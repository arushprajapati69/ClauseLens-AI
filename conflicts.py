"""Cross-document conflict detection and precedence detection for ClauseLens AI.

Enforces:
1. Candidate pairing: cross-document chunks with similarity >= PAIR_SIM_THRESHOLD.
2. Deterministic scoring: numeric mismatches rank first, polarity cues second.
3. LLM judging: up to MAX_CONFLICT_PAIRS.
4. Gate 2 verification: BOTH quotes must be verbatim in their source chunks.
5. Precedence hint extraction: never auto-resolves.
"""

from dataclasses import dataclass, asdict
import re
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import config
from ingest import Chunk
from gates import verify_quote
from tools import extract_numeric_facts
from llm import LLMClient, CONFLICT_JUDGE_SCHEMA

POSITIVE_POLARITY_CUES = [
    "free cancellation", "full refund", "100% refund", "eligible for refund",
    "covered", "fully covered", "reimbursed"
]

NEGATIVE_POLARITY_CUES = [
    "non-refundable", "strictly non-refundable", "no refund", "forfeit",
    "excluded", "disqualified", "not covered"
]

PRECEDENCE_PATTERN = re.compile(
    r"(?:these\s+terms\s+shall\s+prevail|these\s+terms\s+prevail|in\s+case\s+of\s+(?:any\s+)?(?:conflict|difference|inconsistency)[^\.\n]+prevail|take\s+precedence)",
    re.IGNORECASE
)


@dataclass
class VerifiedConflict:
    topic: str
    doc_a: str
    chunk_id_a: str
    clause_label_a: str
    quote_a: str
    doc_b: str
    chunk_id_b: str
    clause_label_b: str
    quote_b: str
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def find_conflict_candidates(
    chunks: List[Chunk],
    embeddings: np.ndarray,
    sim_threshold: float = config.PAIR_SIM_THRESHOLD
) -> List[Tuple[Chunk, Chunk, float, float]]:
    """Identifies and deterministically scores cross-document candidate conflict pairs.
    
    Returns list of (chunk_a, chunk_b, sim, priority_score) sorted descending by priority.
    """
    candidates = []
    n = len(chunks)
    if n < 2 or embeddings is None:
        return []

    # Ensure normalized embeddings
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norm_embeddings = embeddings / np.maximum(norms, 1e-9)

    for i in range(n):
        for j in range(i + 1, n):
            c_a = chunks[i]
            c_b = chunks[j]
            # Must be from different documents
            if c_a.doc_name == c_b.doc_name:
                continue

            sim = float(np.dot(norm_embeddings[i], norm_embeddings[j]))
            if sim < sim_threshold:
                continue

            priority = sim

            # 1. Deterministic Numeric Mismatch Check
            facts_a = extract_numeric_facts(c_a.text)
            facts_b = extract_numeric_facts(c_b.text)
            has_numeric_mismatch = False

            for fa in facts_a:
                for fb in facts_b:
                    if fa["type"] == fb["type"] and fa["type"] in ("duration", "percentage", "money"):
                        # Compare normalized values
                        if fa["type"] == "duration":
                            if fa.get("norm_unit") == fb.get("norm_unit") and fa.get("norm_value") != fb.get("norm_value"):
                                has_numeric_mismatch = True
                                break
                        elif fa.get("unit") == fb.get("unit") and fa.get("value") != fb.get("value"):
                            has_numeric_mismatch = True
                            break
                if has_numeric_mismatch:
                    break

            if has_numeric_mismatch:
                priority += 10.0

            # 2. Opposite-polarity cues
            text_a_lower = c_a.text.lower()
            text_b_lower = c_b.text.lower()
            a_pos = any(cue in text_a_lower for cue in POSITIVE_POLARITY_CUES)
            a_neg = any(cue in text_a_lower for cue in NEGATIVE_POLARITY_CUES)
            b_pos = any(cue in text_b_lower for cue in POSITIVE_POLARITY_CUES)
            b_neg = any(cue in text_b_lower for cue in NEGATIVE_POLARITY_CUES)

            if (a_pos and b_neg) or (a_neg and b_pos):
                priority += 5.0

            candidates.append((c_a, c_b, sim, priority))

    # Sort descending by priority score
    candidates.sort(key=lambda x: x[3], reverse=True)
    return candidates


def evaluate_conflicts(
    candidates: List[Tuple[Chunk, Chunk, float, float]],
    llm_client: LLMClient,
    max_pairs: int = config.MAX_CONFLICT_PAIRS
) -> List[VerifiedConflict]:
    """Judges candidate pairs with LLM and rigorously verifies quotes with Gate 2."""
    verified_conflicts: List[VerifiedConflict] = []

    # Prioritize candidate pairs that exhibit clear numeric or polarity cues (priority >= 5.0)
    prioritized = [c for c in candidates if c[3] >= 5.0]
    eval_list = (prioritized if prioritized else candidates)[:min(max_pairs, 2)]

    judge_system = (
        "You are a strict policy conflict judge for consumer agreements. Compare the two excerpts from different "
        "documents on the same topic. Determine whether they contradict each other ('conflict'), are consistent ('consistent'), "
        "or unrelated ('unrelated'). When there is a conflict, provide exact, verbatim quotes from both excerpts."
    )

    for c_a, c_b, sim, prio in eval_list:
        user_prompt = (
            f"Excerpt A from {c_a.doc_name} ({c_a.clause_label}):\n"
            f"<excerpt_a>{c_a.text}</excerpt_a>\n\n"
            f"Excerpt B from {c_b.doc_name} ({c_b.clause_label}):\n"
            f"<excerpt_b>{c_b.text}</excerpt_b>\n\n"
            "Compare both excerpts. Respond strictly matching the schema."
        )

        res = llm_client.chat_structured(judge_system, user_prompt, CONFLICT_JUDGE_SCHEMA)
        if not res.get("ok"):
            continue

        data = res.get("data", {})
        relation = data.get("relation", "").lower()
        if relation != "conflict":
            continue

        quote_a = data.get("quote_a", "").strip()
        quote_b = data.get("quote_b", "").strip()

        # Gate 2: Both quotes must be verbatim in their respective chunks
        qa_ok = verify_quote(quote_a, c_a.text)
        qb_ok = verify_quote(quote_b, c_b.text)

        if qa_ok and qb_ok:
            conflict = VerifiedConflict(
                topic=data.get("topic", "Policy Discrepancy"),
                doc_a=c_a.doc_name,
                chunk_id_a=c_a.chunk_id,
                clause_label_a=c_a.clause_label,
                quote_a=quote_a,
                doc_b=c_b.doc_name,
                chunk_id_b=c_b.chunk_id,
                clause_label_b=c_b.clause_label,
                quote_b=quote_b,
                explanation=data.get("explanation", "Discrepancy detected between policy documents.")
            )
            verified_conflicts.append(conflict)

    return verified_conflicts


def detect_precedence(chunks: List[Chunk]) -> Optional[Dict[str, str]]:
    """Detects whether any retrieved chunk contains an explicit precedence clause.
    
    Never auto-resolves; surfaces as a hint.
    """
    for c in chunks:
        match = PRECEDENCE_PATTERN.search(c.text)
        if match:
            # Extract sentence or clause around match
            quote = c.text.strip()
            # If chunk is long, extract the relevant sentence containing the match
            sentences = re.split(r"(?<=[.!?])\s+", c.text)
            for s in sentences:
                if PRECEDENCE_PATTERN.search(s):
                    quote = s.strip()
                    break
            return {
                "doc_name": c.doc_name,
                "clause_label": c.clause_label,
                "chunk_id": c.chunk_id,
                "quote": quote,
                "hint": f"{c.doc_name} contains an explicit clause stating it takes legal precedence over marketing materials or FAQs."
            }
    return None

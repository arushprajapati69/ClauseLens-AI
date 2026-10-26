"""Deterministic verification gates for ClauseLens AI.

Three-gate architecture:
- Gate 1: Allowlist / Schema conformance.
- Gate 2: Character-level verbatim evidence & numeric grounding.
- Gate 3: Safe execution & fault-tolerant degradation.
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple
import config
from tools import extract_numeric_facts

ALLOWED_CLAIM_TYPES = {
    "condition", "deadline", "fee", "exclusion", "eligibility", "other"
}

UNICODE_QUOTE_MAP = {
    "‘": "'", "’": "'", "‚": "'", "‛": "'", "`": "'",
    "“": '"', "”": '"', "„": '"', "‟": '"',
    "—": "-", "–": "-", "−": "-", "‐": "-"
}


def normalize_text(s: str) -> str:
    """Normalizes whitespace, unicode quotes, dashes, and casing for comparison."""
    if not s:
        return ""
    for k, v in UNICODE_QUOTE_MAP.items():
        s = s.replace(k, v)
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()


def verify_quote(quote: str, chunk_text: str) -> bool:
    """Verifies that a quote appears character-for-character (verbatim) in chunk_text.
    
    Tolerates normalized whitespace, curly quotes, dashes, and case.
    Supports ellipsis '...' or '…' splitting: every fragment >= 8 chars must appear in sequence.
    Rejects quotes outside [MIN_QUOTE_CHARS, MAX_QUOTE_CHARS].
    """
    if not quote or not chunk_text:
        return False

    trimmed_raw = quote.strip()
    if len(trimmed_raw) < config.MIN_QUOTE_CHARS or len(trimmed_raw) > config.MAX_QUOTE_CHARS:
        return False

    norm_chunk = normalize_text(chunk_text)
    norm_quote = normalize_text(trimmed_raw)

    # Check for ellipsis: ... or …
    ellipsis_pattern = re.compile(r"\s*(?:\.\.\.|…)\s*")
    if ellipsis_pattern.search(norm_quote):
        parts = [p.strip() for p in ellipsis_pattern.split(norm_quote) if p.strip()]
        if not parts:
            return False
        
        last_idx = 0
        for part in parts:
            # If fragment is short, still check if it exists in order
            found_idx = norm_chunk.find(part, last_idx)
            if found_idx == -1:
                return False
            last_idx = found_idx + len(part)
        return True
    else:
        return norm_quote in norm_chunk


def check_schema(obj: Any, retrieved_ids: Set[str]) -> Tuple[bool, List[str]]:
    """Gate 1: Verifies JSON structure and ensures all chunk_ids belong to retrieved set."""
    errors: List[str] = []
    if not isinstance(obj, dict):
        return False, ["Root output must be a JSON object"]

    if "bottom_line" not in obj or not isinstance(obj["bottom_line"], str):
        errors.append("Missing or invalid 'bottom_line' (must be string)")
    
    if "claims" not in obj or not isinstance(obj["claims"], list):
        errors.append("Missing or invalid 'claims' (must be a list)")
    else:
        for idx, claim in enumerate(obj["claims"]):
            if not isinstance(claim, dict):
                errors.append(f"Claim #{idx} is not an object")
                continue
            for k in ("text", "type", "chunk_id", "quote"):
                if k not in claim or not isinstance(claim[k], str):
                    errors.append(f"Claim #{idx} missing or invalid string key '{k}'")
            
            ctype = claim.get("type", "").lower()
            if ctype not in ALLOWED_CLAIM_TYPES:
                errors.append(f"Claim #{idx} has unallowed type '{ctype}'. Allowed: {sorted(ALLOWED_CLAIM_TYPES)}")
            
            cid = claim.get("chunk_id", "")
            if cid not in retrieved_ids:
                errors.append(f"Claim #{idx} cited unretrieved chunk_id '{cid}'")

    if "missing_info" not in obj or not isinstance(obj["missing_info"], list):
        errors.append("Missing or invalid 'missing_info' (must be a list of strings)")

    return len(errors) == 0, errors


def numeric_grounding(text: str, allowed_sources: List[str]) -> List[Dict[str, Any]]:
    """Gate 2b: Checks that every number, currency amount, percentage, and duration in text
    is grounded in the allowed sources (verified quotes, user scenario, or tool outputs).
    
    Returns a list of ungrounded fact dicts.
    """
    if not text:
        return []

    text_facts = extract_numeric_facts(text)
    if not text_facts:
        return []

    # Aggregate all facts present across allowed sources
    combined_source_text = " ".join(allowed_sources)
    source_facts = extract_numeric_facts(combined_source_text)

    # Collect known values for direct lookup
    source_money = {f["value"] for f in source_facts if f["type"] == "money"}
    source_pct = {f["value"] for f in source_facts if f["type"] == "percentage"}
    source_dur_norm = {(f.get("norm_value"), f.get("norm_unit")) for f in source_facts if f["type"] == "duration"}
    source_dur_raw = {f["value"] for f in source_facts if f["type"] == "duration"}
    source_numbers = {f["value"] for f in source_facts}

    ungrounded = []
    for fact in text_facts:
        ftype = fact["type"]
        fval = fact["value"]

        # Check grounding
        is_grounded = False
        if ftype == "money":
            is_grounded = fval in source_money or fval in source_numbers
        elif ftype == "percentage":
            is_grounded = fval in source_pct or fval in source_numbers
        elif ftype == "duration":
            norm_pair = (fact.get("norm_value"), fact.get("norm_unit"))
            is_grounded = norm_pair in source_dur_norm or fval in source_dur_raw or fval in source_numbers
        elif ftype == "number":
            # Numbers that are part of standard prose (e.g. 1 or 2 sentences) or section references
            is_grounded = fval in source_numbers or fval in {1, 2}

        if not is_grounded:
            ungrounded.append(fact)

    return ungrounded


def derive_verdict(
    has_conflict: bool,
    best_retrieval_score: float,
    verified_claims_count: int,
    dropped_claims_count: int,
    numeric_grounding_errors: int,
    had_execution_error: bool = False
) -> str:
    """Deterministically derives the final verdict label.
    
    Verdicts:
    - ERROR: if a system or parsing failure occurred.
    - CONFLICT: if a verified contradiction between documents was detected.
    - INSUFFICIENT_EVIDENCE: if retrieval score is below threshold or 0 claims survived.
    - PARTIAL: if some claims were dropped by verification or numeric grounding failed.
    - SUPPORTED: all claims verified, grounded, and no conflicts.
    """
    if had_execution_error:
        return "ERROR"
    if has_conflict:
        return "CONFLICT"
    if best_retrieval_score < config.MIN_RETRIEVAL_SCORE or verified_claims_count == 0:
        return "INSUFFICIENT_EVIDENCE"
    if dropped_claims_count > 0 or numeric_grounding_errors > 0:
        return "PARTIAL"
    return "SUPPORTED"

import numpy as np
import pytest
from ingest import Chunk
from conflicts import find_conflict_candidates, evaluate_conflicts, detect_precedence, VerifiedConflict

def test_find_conflict_candidates_scoring():
    chunk_a = Chunk(
        chunk_id="terms_c1",
        doc_name="terms.md",
        page=None,
        clause_label="Section 4.2",
        text="Cancellations between 3 and 6 days get 50% refund. Cancellations under 3 days are strictly non-refundable."
    )
    chunk_b = Chunk(
        chunk_id="faq_c1",
        doc_name="faq.md",
        page=None,
        clause_label="FAQ 3",
        text="Free cancellation up to 24 hours before check-in with 100% full refund."
    )
    chunk_same_doc = Chunk(
        chunk_id="terms_c2",
        doc_name="terms.md",
        page=None,
        clause_label="Section 2.1",
        text="Payment must be secured at booking."
    )

    chunks = [chunk_a, chunk_b, chunk_same_doc]
    # Unit vectors where chunk_a and chunk_b have high cosine similarity (e.g. 0.9)
    # and chunk_same_doc has lower similarity
    emb = np.array([
        [1.0, 0.1, 0.0],
        [0.9, 0.2, 0.0],
        [0.1, 0.9, 0.0]
    ], dtype=np.float32)

    candidates = find_conflict_candidates(chunks, emb, sim_threshold=0.5)
    # Chunks from same doc (terms_c1 and terms_c2) must NOT be paired
    pair_docs = [(c1.doc_name, c2.doc_name) for c1, c2, _, _ in candidates]
    for d1, d2 in pair_docs:
        assert d1 != d2

    # The top candidate should be terms.md and faq.md with high priority due to numeric and polarity mismatches
    assert len(candidates) >= 1
    top_a, top_b, sim, priority = candidates[0]
    assert {top_a.doc_name, top_b.doc_name} == {"terms.md", "faq.md"}
    # Priority should include numeric mismatch bonus (+10) and polarity bonus (+5)
    assert priority > 15.0


def test_evaluate_conflicts_gate2_verification():
    chunk_a = Chunk(
        chunk_id="terms_c1",
        doc_name="terms.md",
        page=None,
        clause_label="Section 4.2",
        text="Cancellations made between 3 and 6 days prior to check-in receive a 50% refund."
    )
    chunk_b = Chunk(
        chunk_id="faq_c1",
        doc_name="faq.md",
        page=None,
        clause_label="FAQ 3",
        text="Free cancellation up to 24 hours before check-in on standard rates."
    )
    candidate = (chunk_a, chunk_b, 0.85, 16.0)

    # 1. Mock LLM returning verbatim quotes -> should succeed
    class ValidMockLLM:
        def chat_structured(self, system, user, schema, model=None):
            return {
                "ok": True,
                "data": {
                    "relation": "conflict",
                    "topic": "Cancellation Deadline",
                    "explanation": "Terms require 3-6 days for partial refund while FAQ promises 24 hours for free cancellation.",
                    "quote_a": "Cancellations made between 3 and 6 days prior to check-in receive a 50% refund.",
                    "quote_b": "Free cancellation up to 24 hours before check-in on standard rates."
                }
            }

    conflicts = evaluate_conflicts([candidate], ValidMockLLM())
    assert len(conflicts) == 1
    c = conflicts[0]
    assert c.doc_a == "terms.md"
    assert c.doc_b == "faq.md"
    assert "50% refund" in c.quote_a
    assert "24 hours" in c.quote_b

    # 2. Mock LLM returning hallucinated quotes -> must be rejected by Gate 2
    class HallucinatedMockLLM:
        def chat_structured(self, system, user, schema, model=None):
            return {
                "ok": True,
                "data": {
                    "relation": "conflict",
                    "topic": "Cancellation Deadline",
                    "explanation": "Contradiction found.",
                    "quote_a": "You only get half back if you cancel late.", # Not in chunk_a!
                    "quote_b": "Free cancellation up to 24 hours before check-in on standard rates."
                }
            }

    conflicts_rejected = evaluate_conflicts([candidate], HallucinatedMockLLM())
    assert len(conflicts_rejected) == 0


def test_detect_precedence():
    chunk_with_precedence = Chunk(
        chunk_id="c1",
        doc_name="terms.md",
        page=None,
        clause_label="Section 9.1",
        text="In case of any conflict or difference between these Terms and any FAQ, these Terms shall prevail in all respects."
    )
    chunk_normal = Chunk(
        chunk_id="c2",
        doc_name="faq.md",
        page=None,
        clause_label="FAQ 1",
        text="Check-in is at 2 PM."
    )

    prec = detect_precedence([chunk_with_precedence, chunk_normal])
    assert prec is not None
    assert prec["doc_name"] == "terms.md"
    assert "prevail" in prec["quote"].lower()

    prec_none = detect_precedence([chunk_normal])
    assert prec_none is None

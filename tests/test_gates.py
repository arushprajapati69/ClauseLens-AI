import pytest
import config
from gates import verify_quote, check_schema, numeric_grounding, derive_verdict, normalize_text

SAMPLE_CHUNK = """
Section 4.2: Cancellations made between 3 and 6 days prior to scheduled check-in
shall be eligible for a 50% refund of the total booking value.
Any cancellation made less than 72 hours (3 days) prior to arrival is strictly non-refundable.
"""

def test_verify_quote_exact():
    quote = "Cancellations made between 3 and 6 days prior to scheduled check-in"
    assert verify_quote(quote, SAMPLE_CHUNK) is True

def test_verify_quote_whitespace_and_case():
    quote = "cancellations   made between 3 and 6 DAYS\nprior to scheduled check-in"
    assert verify_quote(quote, SAMPLE_CHUNK) is True

def test_verify_quote_curly_quotes_and_dashes():
    chunk = "“Special terms”—cancellations incur a ‘nominal’ fee of ₹100."
    quote = '"Special terms"-cancellations incur a \'nominal\' fee of ₹100.'
    assert verify_quote(quote, chunk) is True

def test_verify_quote_ellipsis_fragments():
    # In order fragments
    quote = "Cancellations made between 3 and 6 days ... eligible for a 50% refund"
    assert verify_quote(quote, SAMPLE_CHUNK) is True

    # With unicode ellipsis
    quote_unicode = "Cancellations made between 3 and 6 days … eligible for a 50% refund"
    assert verify_quote(quote_unicode, SAMPLE_CHUNK) is True

def test_verify_quote_ellipsis_out_of_order():
    # Out of order fragments must return False
    quote = "eligible for a 50% refund ... Cancellations made between 3 and 6 days"
    assert verify_quote(quote, SAMPLE_CHUNK) is False

def test_verify_quote_fabricated_and_wrong_chunk():
    # Fabricated / paraphrased text
    quote = "You can cancel between 3 and 6 days to get half your money back"
    assert verify_quote(quote, SAMPLE_CHUNK) is False

    # Wrong chunk text
    quote_wrong = "Free cancellation up to 24 hours before check-in on standard rates."
    assert verify_quote(quote_wrong, SAMPLE_CHUNK) is False

def test_verify_quote_length_bounds():
    # Too short (< 15 chars)
    quote_short = "50% refund"
    assert verify_quote(quote_short, SAMPLE_CHUNK) is False

    # Too long (> 400 chars)
    quote_long = "Cancellations " + ("made between " * 40)
    assert verify_quote(quote_long, SAMPLE_CHUNK) is False


def test_check_schema_valid():
    retrieved_ids = {"chunk_1", "chunk_2"}
    obj = {
        "bottom_line": "You are eligible for a 50% refund.",
        "claims": [
            {
                "text": "50% refund for 3-6 days notice",
                "type": "fee",
                "chunk_id": "chunk_1",
                "quote": "shall be eligible for a 50% refund of the total booking value."
            }
        ],
        "missing_info": []
    }
    ok, errors = check_schema(obj, retrieved_ids)
    assert ok is True
    assert errors == []


def test_check_schema_invalid():
    retrieved_ids = {"chunk_1"}
    # Cited unretrieved chunk
    obj_bad_cid = {
        "bottom_line": "Some statement.",
        "claims": [
            {
                "text": "Claim",
                "type": "deadline",
                "chunk_id": "chunk_99",
                "quote": "A valid length quote text here."
            }
        ],
        "missing_info": []
    }
    ok, errors = check_schema(obj_bad_cid, retrieved_ids)
    assert ok is False
    assert any("unretrieved chunk_id" in e for e in errors)

    # Invalid claim type
    obj_bad_type = {
        "bottom_line": "Some statement.",
        "claims": [
            {
                "text": "Claim",
                "type": "unsupported_type",
                "chunk_id": "chunk_1",
                "quote": "A valid length quote text here."
            }
        ],
        "missing_info": []
    }
    ok, errors = check_schema(obj_bad_type, retrieved_ids)
    assert ok is False
    assert any("unallowed type" in e for e in errors)


def test_numeric_grounding():
    allowed_sources = [
        "Cancellations between 3 and 6 days notice get 50% refund minus ₹250 fee.",
        "Check-in on 2026-11-10 with total payment ₹12,000."
    ]

    # Grounded text
    grounded_text = "Under the policy, ₹250 fee is deducted and you receive a 50% refund for 3 days notice."
    ungrounded = numeric_grounding(grounded_text, allowed_sources)
    assert ungrounded == []

    # Ungrounded text (hallucinated ₹900 fee and 14 days)
    ungrounded_text = "You will be charged a ₹900 fee and must notify within 14 days."
    ungrounded = numeric_grounding(ungrounded_text, allowed_sources)
    assert len(ungrounded) >= 2
    types_and_vals = [(u["type"], u["value"]) for u in ungrounded]
    assert ("money", 900) in types_and_vals
    assert ("duration", 14) in types_and_vals


def test_derive_verdict():
    # CONFLICT
    assert derive_verdict(has_conflict=True, best_retrieval_score=0.8, verified_claims_count=2, dropped_claims_count=0, numeric_grounding_errors=0) == "CONFLICT"

    # INSUFFICIENT_EVIDENCE: low score
    assert derive_verdict(has_conflict=False, best_retrieval_score=0.2, verified_claims_count=1, dropped_claims_count=0, numeric_grounding_errors=0) == "INSUFFICIENT_EVIDENCE"

    # INSUFFICIENT_EVIDENCE: zero claims
    assert derive_verdict(has_conflict=False, best_retrieval_score=0.7, verified_claims_count=0, dropped_claims_count=1, numeric_grounding_errors=0) == "INSUFFICIENT_EVIDENCE"

    # PARTIAL: dropped claim
    assert derive_verdict(has_conflict=False, best_retrieval_score=0.7, verified_claims_count=1, dropped_claims_count=1, numeric_grounding_errors=0) == "PARTIAL"

    # PARTIAL: numeric grounding error
    assert derive_verdict(has_conflict=False, best_retrieval_score=0.7, verified_claims_count=1, dropped_claims_count=0, numeric_grounding_errors=1) == "PARTIAL"

    # SUPPORTED
    assert derive_verdict(has_conflict=False, best_retrieval_score=0.7, verified_claims_count=2, dropped_claims_count=0, numeric_grounding_errors=0) == "SUPPORTED"

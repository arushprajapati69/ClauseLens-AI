import pytest
from ingest import Chunk
from pipeline import answer_question, Result, build_system_prompt
from conflicts import VerifiedConflict

class MockIndex:
    def __init__(self, chunks_with_scores):
        self.chunks_with_scores = chunks_with_scores

    def query(self, question, top_k=6):
        return self.chunks_with_scores[:top_k]

class MockLLM:
    def __init__(self, response_data, ok=True, error=None):
        self.response_data = response_data
        self.ok = ok
        self.error = error
        self.client = self

    def embed(self, model, input):
        class FakeRes:
            pass
        res = FakeRes()
        n = len(input) if isinstance(input, list) else 1
        res.embeddings = [[0.1] * 768 for _ in range(n)]
        return res

    def chat_structured(self, system, user, schema, model=None):
        if not self.ok:
            return {"ok": False, "error": self.error or "LLM failed"}
        return {"ok": True, "data": self.response_data}


def test_build_system_prompt():
    prompt = build_system_prompt()
    assert "ClauseLens" in prompt
    assert "<excerpt>" in prompt
    assert "untrusted data" in prompt


def test_gate_0_rejections():
    idx = MockIndex([])
    # Empty question
    res_empty = answer_question("", idx)
    assert res_empty.verdict == "INSUFFICIENT_EVIDENCE"
    assert res_empty.error == "Empty question"

    # Too long
    long_q = "Can I get a refund? " * 100
    res_long = answer_question(long_q, idx)
    assert res_long.verdict == "ERROR"
    assert "too long" in res_long.bottom_line.lower()


def test_retrieval_below_min_score_abstains():
    chunk = Chunk(chunk_id="c1", doc_name="doc.md", page=None, clause_label="Sec 1", text="General text.")
    # Score 0.25 is well below MIN_RETRIEVAL_SCORE (0.38)
    idx = MockIndex([(chunk, 0.25)])
    
    mock_llm = MockLLM(response_data={})
    res = answer_question("Random off topic query?", idx, client=mock_llm)
    assert res.verdict == "INSUFFICIENT_EVIDENCE"
    assert "sufficient evidence" in res.bottom_line.lower()


def test_pipeline_supported_verdict():
    chunk_text = "Cancellations made between 3 and 6 days prior to check-in receive a 50% refund."
    chunk = Chunk(chunk_id="c1", doc_name="terms.md", page=None, clause_label="Section 4.2", text=chunk_text)
    idx = MockIndex([(chunk, 0.75)])

    llm_output = {
        "bottom_line": "You will receive a 50% refund if you cancel between 3 and 6 days before arrival.",
        "claims": [
            {
                "text": "50% refund for 3-6 days notice",
                "type": "fee",
                "chunk_id": "c1",
                "quote": "Cancellations made between 3 and 6 days prior to check-in receive a 50% refund."
            }
        ],
        "missing_info": []
    }
    mock_llm = MockLLM(response_data=llm_output)
    res = answer_question("Can I get a refund?", idx, client=mock_llm)

    assert res.verdict == "SUPPORTED"
    assert len(res.verified_claims) == 1
    assert len(res.dropped_claims) == 0
    assert "50% refund" in res.bottom_line


def test_pipeline_partial_verdict_on_dropped_claim():
    chunk_text = "Cancellations made between 3 and 6 days prior to check-in receive a 50% refund."
    chunk = Chunk(chunk_id="c1", doc_name="terms.md", page=None, clause_label="Section 4.2", text=chunk_text)
    idx = MockIndex([(chunk, 0.75)])

    llm_output = {
        "bottom_line": "You will receive a 50% refund.",
        "claims": [
            {
                "text": "Hallucinated claim",
                "type": "condition",
                "chunk_id": "c1",
                "quote": "This quote is completely fabricated."
            }
        ],
        "missing_info": []
    }
    mock_llm = MockLLM(response_data=llm_output)
    res = answer_question("Can I get a refund?", idx, client=mock_llm)

    # Claim dropped by Gate 2 -> 0 claims survived -> INSUFFICIENT_EVIDENCE
    assert res.verdict == "INSUFFICIENT_EVIDENCE"
    assert len(res.dropped_claims) == 1


def test_pipeline_safe_fallback_on_llm_error():
    chunk = Chunk(chunk_id="c1", doc_name="terms.md", page=None, clause_label="Section 1", text="Excerpts directly shown.")
    idx = MockIndex([(chunk, 0.8)])
    failing_llm = MockLLM(response_data={}, ok=False, error="Connection timeout to Ollama")

    res = answer_question("Any question", idx, client=failing_llm)
    assert res.verdict == "PARTIAL"
    assert "retrieved policy excerpts" in res.bottom_line
    assert len(res.retrieved_chunks) == 1

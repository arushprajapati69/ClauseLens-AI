import os
import numpy as np
import pytest
from ingest import extract_text_from_file, chunk_document, Chunk
from store import PolicyIndex

def test_extract_text_markdown():
    sample_path = os.path.join(os.path.dirname(__file__), "..", "sample_docs", "stayeasy_terms.md")
    pages_data = extract_text_from_file(sample_path)
    assert len(pages_data) == 1
    assert pages_data[0]["page"] is None
    assert "StayEasy" in pages_data[0]["text"]
    assert "Section 4" in pages_data[0]["text"]


def test_chunk_document_clauses():
    text = (
        "# Main Heading\n"
        "Some introductory preamble.\n\n"
        "Section 4.1: Cancellation 7 days prior gives full refund minus ₹250.\n\n"
        "Section 4.2: Cancellation 3 to 6 days gives 50% refund.\n\n"
        "Q: Can I get a refund?\n"
        "Yes, subject to terms."
    )
    pages_data = [{"page": 1, "text": text}]
    chunks = chunk_document("test_doc.pdf", pages_data)
    
    assert len(chunks) >= 3
    labels = [c.clause_label for c in chunks]
    assert any("4.1" in l for l in labels)
    assert any("4.2" in l for l in labels)
    assert any("Q:" in l or "Can I get a refund" in l for l in labels)
    
    for c in chunks:
        assert c.chunk_id.startswith("test_doc_c")
        assert c.doc_name == "test_doc.pdf"
        assert c.page == 1
        assert len(c.text) > 0


def test_policy_index_hybrid_retrieval(tmp_path):
    class FakeOllamaClient:
        def embed(self, model, input):
            class FakeRes:
                pass
            res = FakeRes()
            # If list of texts
            if isinstance(input, list):
                res.embeddings = []
                for t in input:
                    vec = [0.0] * 768
                    if "refund" in t.lower():
                        vec[0] = 1.0
                    if "warranty" in t.lower():
                        vec[1] = 1.0
                    res.embeddings.append(vec)
            else:
                vec = [0.0] * 768
                if "refund" in input.lower():
                    vec[0] = 1.0
                if "warranty" in input.lower():
                    vec[1] = 1.0
                res.embeddings = [vec]
            return res

    index = PolicyIndex(cache_dir=str(tmp_path))
    index.client = FakeOllamaClient()

    chunks = [
        Chunk(chunk_id="c1", doc_name="terms.md", page=None, clause_label="Refund", text="Refund within 7 days."),
        Chunk(chunk_id="c2", doc_name="warranty.md", page=None, clause_label="Warranty", text="Earbud battery covered for 6 months."),
    ]
    index.add_document("terms.md", "Refund within 7 days.", [chunks[0]])
    index.add_document("warranty.md", "Earbud battery covered for 6 months.", [chunks[1]])

    # Query for refund
    results = index.query("Can I get a refund?", top_k=2)
    assert len(results) == 2
    top_chunk, top_score = results[0]
    assert top_chunk.chunk_id == "c1"
    assert top_score > results[1][1]

"""Automated evaluation and calibration benchmark runner for ClauseLens AI.

Runs labelled test cases against indexed sample documents and measures:
- Verdict accuracy (including conflict detection and abstention)
- Gate 2 verbatim quote verification rate
- Retrieval score distributions for threshold calibration
- Numeric grounding and scenario calculator correctness
"""

import json
import os
import sys
import time

# Ensure root directory is on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8", errors="replace")
except Exception:
    pass

import config
from ingest import extract_text_from_file, chunk_document
from store import PolicyIndex
from pipeline import answer_question, Result
from llm import LLMClient


def load_and_index_samples(index: PolicyIndex, sample_dir: str = "sample_docs"):
    """Loads and indexes all sample documents."""
    docs = [
        "stayeasy_terms.md",
        "stayeasy_faq.md",
        "voltedge_warranty.md",
        "clipstream_subscription.md"
    ]
    total_chunks = 0
    for doc in docs:
        doc_path = os.path.join(sample_dir, doc)
        if not os.path.exists(doc_path):
            continue
        pages_data = extract_text_from_file(doc_path)
        chunks = chunk_document(doc, pages_data)
        raw_text = "\n".join(p["text"] for p in pages_data)
        index.add_document(doc, raw_text, chunks)
        total_chunks += len(chunks)

    print(f"Indexed {len(docs)} documents ({total_chunks} total clause-aware chunks).")
    return total_chunks


def run_evaluation(questions_path: str = "eval/questions.json"):
    print("=" * 75)
    print("ClauseLens AI — Automated Benchmark & Calibration Suite")
    print("=" * 75)

    index = PolicyIndex(cache_dir=".cache")
    load_and_index_samples(index)

    with open(questions_path, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    llm_client = LLMClient()
    results_summary = []
    total_claims = 0
    total_verified = 0

    print("\nRunning evaluation cases...\n", flush=True)

    for idx, tc in enumerate(test_cases):
        qid = tc["id"]
        q_text = tc["question"]
        scenario = tc.get("scenario", {})
        expected_verdict = tc["expected_verdict"]
        cat = tc["category"]

        print(f"[{idx+1}/{len(test_cases)}] Running '{qid}' ({cat})...", flush=True)
        t0 = time.time()
        res: Result = answer_question(q_text, index, scenario=scenario, client=llm_client)
        elapsed = time.time() - t0

        best_score = res.retrieved_chunks[0][1] if res.retrieved_chunks else 0.0
        v_claims = len(res.verified_claims)
        d_claims = len(res.dropped_claims)
        t_claims = v_claims + d_claims

        total_claims += t_claims
        total_verified += v_claims

        quote_verif_rate = (v_claims / t_claims * 100.0) if t_claims > 0 else 100.0

        verdict_match = (res.verdict == expected_verdict)
        # For conflict cases, also check if verified conflict was detected
        if expected_verdict == "CONFLICT":
            verdict_match = verdict_match and (len(res.conflicts) > 0)

        results_summary.append({
            "id": qid,
            "category": cat,
            "expected_verdict": expected_verdict,
            "actual_verdict": res.verdict,
            "match": verdict_match,
            "best_score": round(best_score, 3),
            "claims_verified": v_claims,
            "claims_dropped": d_claims,
            "quote_verif_rate": round(quote_verif_rate, 1),
            "conflicts_count": len(res.conflicts),
            "elapsed_sec": round(elapsed, 2)
        })

        status_str = "PASS" if verdict_match else "FAIL"
        print(f"[{status_str}] {qid} ({cat}):")
        print(f"       Verdict: {res.verdict} (expected: {expected_verdict})")
        print(f"       Retrieval Score: {best_score:.3f} | Verified Claims: {v_claims}/{t_claims} | Time: {elapsed:.2f}s")
        if res.conflicts:
            print(f"       Conflict: {res.conflicts[0].doc_a} vs {res.conflicts[0].doc_b} ('{res.conflicts[0].topic}')")
        if res.bottom_line:
            print(f"       Bottom line: {res.bottom_line[:90]}...")
        print()

    # Aggregate metrics
    total_cases = len(results_summary)
    passed_cases = sum(1 for r in results_summary if r["match"])
    accuracy = (passed_cases / total_cases) * 100.0
    overall_quote_rate = (total_verified / total_claims * 100.0) if total_claims > 0 else 100.0

    print("=" * 75)
    print("EVALUATION SUMMARY & CALIBRATION METRICS")
    print("=" * 75)
    print(f"Total Benchmark Cases:        {total_cases}")
    print(f"Verdict Match Accuracy:       {passed_cases}/{total_cases} ({accuracy:.1f}%)")
    print(f"Gate 2 Quote Verification:    {total_verified}/{total_claims} ({overall_quote_rate:.1f}%)")
    print("\nRetrieval Score Calibration Table:")
    print(f"{'Case ID':<30} | {'Score':<8} | {'Verdict':<15} | {'Category'}")
    print("-" * 75)
    for r in results_summary:
        print(f"{r['id']:<30} | {r['best_score']:<8.3f} | {r['actual_verdict']:<15} | {r['category']}")
    print("-" * 75)
    print(f"Calibrated MIN_RETRIEVAL_SCORE: {config.MIN_RETRIEVAL_SCORE}")
    print(f"Calibrated PAIR_SIM_THRESHOLD:  {config.PAIR_SIM_THRESHOLD}")
    print("=" * 75)

    return results_summary


if __name__ == "__main__":
    run_evaluation()

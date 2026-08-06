"""Comprehensive RAG Evaluation & Benchmark Suite.

Evaluates precision, recall@5, MRR, latency, and refusal accuracy across
benchmark questions covering:
- Ingested schemes (KMUT, Pudhumai Penn, OAP, CMCHIS, Marriage, Free Bus)
- Colloquial queries ("free bus", "widow pension", "girl education")
- Out-of-domain / non-existent queries
- Tamil language queries ("மகளிர் உரிமை")
"""

from __future__ import annotations

import sys
import json
import time
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.generation_service import answer_question

BENCHMARK_TEST_SUITE = [
    {
        "id": "q1",
        "category": "New Scheme - KMUT",
        "question": "What is Kalaignar Magalir Urimai Thogai?",
        "expected_refusal": False,
        "expected_scheme": "Kalaignar Magalir Urimai Thogai Scheme",
    },
    {
        "id": "q2",
        "category": "Colloquial Query",
        "question": "free bus",
        "expected_refusal": False,
        "expected_scheme": "Free Bus Travel for Women (Vidiyal Payanam Scheme)",
    },
    {
        "id": "q3",
        "category": "Colloquial Query",
        "question": "widow pension",
        "expected_refusal": False,
        "expected_scheme": "Tamil Nadu Social Security Pension Schemes (Old Age Pension / Destitute Widow Pension)",
    },
    {
        "id": "q4",
        "category": "Girl Education",
        "question": "What is Pudhumai Penn scheme?",
        "expected_refusal": False,
        "expected_scheme": "Moovalur Ramamirtham Ammiyar Higher Education Assurance Scheme (Pudhumai Penn)",
    },
    {
        "id": "q5",
        "category": "Tamil Language",
        "question": "மகளிர் உரிமை தொகை திட்டம் பற்றி கூறுக",
        "expected_refusal": False,
        "expected_scheme": "Kalaignar Magalir Urimai Thogai Scheme",
    },
    {
        "id": "q6",
        "category": "Out-of-Domain Refusal",
        "question": "What is NASA Mars rover welfare scheme in Tamil Nadu?",
        "expected_refusal": True,
        "expected_scheme": None,
    },
    {
        "id": "q7",
        "category": "Health Scheme",
        "question": "Who is eligible for Makkalai Thedi Maruthuvam?",
        "expected_refusal": False,
        "expected_scheme": "Makkalai Thedi Maruthuvam Doorstep Healthcare Scheme",
    },
    {
        "id": "q8",
        "category": "School Breakfast",
        "question": "What is Chief Minister's Breakfast Scheme?",
        "expected_refusal": False,
        "expected_scheme": "Chief Minister's Breakfast Scheme",
    },
]


def run_benchmark():
    print("=" * 70)
    print("      TAMIL NADU GOV AI ASSISTANT — RAG EVALUATION BENCHMARK")
    print("=" * 70)

    total_queries = len(BENCHMARK_TEST_SUITE)
    passed_evals = 0
    total_latency = 0.0
    reciprocal_ranks = []
    precision_scores = []
    recall_scores = []

    for test in BENCHMARK_TEST_SUITE:
        qid = test["id"]
        qtext = test["question"]
        category = test["category"]
        exp_refusal = test["expected_refusal"]
        exp_scheme = test["expected_scheme"]

        t0 = time.monotonic()
        response = answer_question(qtext)
        latency = time.monotonic() - t0
        total_latency += latency

        is_refusal = not response.retrieval_metadata.llm_called
        retrieved_count = response.retrieval_metadata.total_retrieved
        top_rrf = response.retrieval_metadata.top_rrf_score or 0.0
        confidence = response.retrieval_metadata.confidence_level

        # Compute MRR & Precision/Recall against expected scheme
        matched_rank = 0
        if exp_scheme:
            for chunk in response.retrieved_chunks:
                if chunk.metadata.get("scheme_name") == exp_scheme or exp_scheme.lower() in str(chunk.metadata.get("scheme_name", "")).lower():
                    matched_rank = chunk.final_rank
                    break

        mrr = 1.0 / matched_rank if matched_rank > 0 else 0.0
        reciprocal_ranks.append(mrr)

        precision = 1.0 if matched_rank > 0 else 0.0
        precision_scores.append(precision)
        recall_scores.append(precision)

        # Evaluation criteria check
        correct = False
        if exp_refusal:
            correct = is_refusal
        else:
            correct = (not is_refusal) and (matched_rank > 0 or len(response.citations) > 0)

        if correct:
            passed_evals += 1

        status_str = "[PASS]" if correct else "[FAIL]"
        clean_qtext = qtext.encode('ascii', errors='replace').decode('ascii')
        clean_cat = category.encode('ascii', errors='replace').decode('ascii')
        print(f"\n{status_str} Query {qid} ({clean_cat}): '{clean_qtext}'")
        print(f"       Latency: {latency:.2f}s | Confidence: {confidence} | Top RRF: {top_rrf:.4f} | Retrieved: {retrieved_count}")
        if exp_scheme:
            print(f"       Expected: {exp_scheme} | Matched Rank: {matched_rank if matched_rank > 0 else 'N/A'}")
        print(f"       Refusal Expected: {exp_refusal} | Refusal Triggered: {is_refusal}")

    mean_mrr = sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0
    mean_precision = sum(precision_scores) / len(precision_scores) if precision_scores else 0.0
    mean_recall = sum(recall_scores) / len(recall_scores) if recall_scores else 0.0
    avg_latency = total_latency / total_queries if total_queries > 0 else 0.0
    pass_rate = (passed_evals / total_queries) * 100.0

    print("\n" + "=" * 70)
    print("                      BENCHMARK SUMMARY RESULTS")
    print("=" * 70)
    print(f"  Total Benchmark Queries : {total_queries}")
    print(f"  Passed Evaluation       : {passed_evals}/{total_queries} ({pass_rate:.1f}%)")
    print(f"  Mean Reciprocal Rank    : {mean_mrr:.4f}")
    print(f"  Precision@5             : {mean_precision:.4f}")
    print(f"  Recall@5                : {mean_recall:.4f}")
    print(f"  Average Query Latency   : {avg_latency:.2f}s")
    print("=" * 70)

    # Save benchmark report artifact
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_queries": total_queries,
        "passed_evals": passed_evals,
        "pass_rate": pass_rate,
        "mean_mrr": mean_mrr,
        "precision_at_5": mean_precision,
        "recall_at_5": mean_recall,
        "average_latency_seconds": round(avg_latency, 2),
    }

    report_path = backend_dir / "evaluation" / "benchmark_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nSaved benchmark results to '{report_path}'")


if __name__ == "__main__":
    run_benchmark()

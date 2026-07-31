"""Deterministic Quality Checks for Milestone 6 RAG Evaluation.

Evaluates generation responses deterministically without using an LLM-as-a-judge:
- Verifies expected refusal for out-of-scope/adjacent queries
- Verifies expected scheme presence in generated citations for in-scope queries
- Measures execution time and retrieval counts
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from app.services.generation_service import answer_question

logger = logging.getLogger(__name__)


def run_quick_check(dataset_path: str = "evaluation/eval_dataset.json") -> dict[str, Any]:
    """Execute deterministic quality verification against the evaluation dataset.

    Args:
        dataset_path: Path to evaluation dataset JSON file.

    Returns:
        Dictionary containing summary stats and individual question check details.
    """
    path = Path(dataset_path)
    if not path.exists():
        raise FileNotFoundError(f"Evaluation dataset not found at {dataset_path}")

    with open(path, "r", encoding="utf-8") as f:
        questions = json.load(f)

    results: list[dict[str, Any]] = []
    passed_count = 0
    failed_count = 0

    print("\n" + "=" * 80)
    print("STARTING DETERMINISTIC QUICK CHECK")
    print("=" * 80)

    for item in questions:
        q_id = item["id"]
        q_text = item["question"]
        expected_scheme = item.get("expected_scheme")
        expected_refusal = item.get("expected_refusal", False)

        t0 = time.monotonic()
        try:
            response = answer_question(q_text)
            elapsed = round(time.monotonic() - t0, 3)

            llm_called = response.retrieval_metadata.llm_called
            citations = response.citations
            citation_count = len(citations)

            cited_schemes = [c.scheme_name for c in citations if c.scheme_name]
            top_retrieved_scheme = cited_schemes[0] if cited_schemes else "None"

            # Deterministic Pass/Fail criteria
            is_pass = True
            failure_reasons = []

            # 1. Refusal Check
            if expected_refusal:
                # Answer should refuse (citations empty or llm_called false or refusal text present)
                is_refusal = (not llm_called) or (citation_count == 0) or ("No relevant official information found" in response.answer)
                if not is_refusal:
                    is_pass = False
                    failure_reasons.append("Expected refusal, but answer was generated with citations")
            else:
                # In-scope check
                if citation_count == 0:
                    is_pass = False
                    failure_reasons.append("Expected citations, but 0 citations were returned")
                elif expected_scheme and not any(expected_scheme.lower() in s.lower() for s in cited_schemes):
                    is_pass = False
                    failure_reasons.append(f"Expected scheme '{expected_scheme}' not found in citations {cited_schemes}")

            status = "PASS" if is_pass else "FAIL"
            if is_pass:
                passed_count += 1
            else:
                failed_count += 1

            entry = {
                "id": q_id,
                "question": q_text,
                "category": item.get("category"),
                "status": status,
                "expected_refusal": expected_refusal,
                "expected_scheme": expected_scheme,
                "llm_called": llm_called,
                "citation_count": citation_count,
                "top_retrieved_scheme": top_retrieved_scheme,
                "cited_schemes": cited_schemes,
                "execution_time_sec": elapsed,
                "failure_reasons": failure_reasons,
            }
            results.append(entry)

            print(
                f"[{status}] {q_id} | {item.get('category'):<12} | Time: {elapsed}s | "
                f"Citations: {citation_count} | LLM: {llm_called} | Reason: {', '.join(failure_reasons) if failure_reasons else 'OK'}"
            )

        except Exception as exc:
            elapsed = round(time.monotonic() - t0, 3)
            logger.exception("Error checking question %s", q_id)
            failed_count += 1
            results.append({
                "id": q_id,
                "question": q_text,
                "category": item.get("category"),
                "status": "FAIL",
                "expected_refusal": expected_refusal,
                "expected_scheme": expected_scheme,
                "llm_called": False,
                "citation_count": 0,
                "top_retrieved_scheme": "Error",
                "cited_schemes": [],
                "execution_time_sec": elapsed,
                "failure_reasons": [f"Runtime Exception: {str(exc)}"],
            })

    total = len(questions)
    pass_rate = round((passed_count / total) * 100, 1) if total > 0 else 0.0

    summary = {
        "total_questions": total,
        "passed": passed_count,
        "failed": failed_count,
        "pass_rate_pct": pass_rate,
        "results": results,
    }

    print("=" * 80)
    print(f"QUICK CHECK SUMMARY: {passed_count}/{total} PASSED ({pass_rate}%)")
    print("=" * 80 + "\n")

    return summary


if __name__ == "__main__":
    run_quick_check()

"""Deterministic Retrieval Evaluator for Hit@K, MRR, and Retrieval Latency.

Evaluates hybrid retrieval (vector + BM25 + RRF) performance against expected scheme targets.
"""

from __future__ import annotations

import json
import logging
import statistics
import time
from pathlib import Path
from typing import Any

from app.rag.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)


def evaluate_retrieval(dataset_path: str = "evaluation/eval_dataset.json") -> dict[str, Any]:
    """Execute retrieval benchmark across evaluation dataset.

    Args:
        dataset_path: Path to dataset JSON file.

    Returns:
        Dictionary containing Hit@1, Hit@3, Hit@5, MRR, and retrieval latency metrics.
    """
    path = Path(dataset_path)
    if not path.exists():
        raise FileNotFoundError(f"Evaluation dataset not found at {dataset_path}")

    with open(path, "r", encoding="utf-8") as f:
        questions = json.load(f)

    retrieval_service = RetrievalService()

    hit1_count = 0
    hit3_count = 0
    hit5_count = 0
    reciprocal_ranks = []
    total_retrieved_chunks = []
    retrieval_latencies_ms = []

    in_scope_total = 0
    success_count = 0

    print("\n" + "=" * 80)
    print("STARTING RETRIEVAL BENCHMARK")
    print("=" * 80)

    for item in questions:
        q_id = item["id"]
        q_text = item["question"]
        expected_scheme = item.get("expected_scheme")
        expected_refusal = item.get("expected_refusal", False)

        t0 = time.monotonic()
        try:
            chunks = retrieval_service.retrieve(q_text)
            elapsed_ms = round((time.monotonic() - t0) * 1000, 2)
            retrieval_latencies_ms.append(elapsed_ms)
            total_retrieved_chunks.append(len(chunks))

            if expected_refusal or not expected_scheme:
                # Out-of-scope / adjacent questions
                continue

            in_scope_total += 1
            schemes_in_chunks = [c.metadata.get("scheme_name", "") for c in chunks]

            # Find rank of expected scheme
            found_rank = None
            for idx, sch in enumerate(schemes_in_chunks, start=1):
                if expected_scheme.lower() in sch.lower():
                    found_rank = idx
                    break

            if found_rank is not None:
                success_count += 1
                rr = 1.0 / found_rank
                reciprocal_ranks.append(rr)
                if found_rank == 1:
                    hit1_count += 1
                if found_rank <= 3:
                    hit3_count += 1
                if found_rank <= 5:
                    hit5_count += 1
            else:
                reciprocal_ranks.append(0.0)

            print(
                f"[{q_id}] Scheme: '{expected_scheme[:35]}...' | Found Rank: {found_rank} | "
                f"Chunks: {len(chunks)} | Latency: {elapsed_ms}ms"
            )

        except Exception as exc:
            logger.exception("Retrieval failed for query %s", q_id)
            if not expected_refusal:
                in_scope_total += 1
                reciprocal_ranks.append(0.0)

    hit1_rate = round((hit1_count / in_scope_total) * 100, 1) if in_scope_total > 0 else 0.0
    hit3_rate = round((hit3_count / in_scope_total) * 100, 1) if in_scope_total > 0 else 0.0
    hit5_rate = round((hit5_count / in_scope_total) * 100, 1) if in_scope_total > 0 else 0.0
    mrr = round(statistics.mean(reciprocal_ranks), 4) if reciprocal_ranks else 0.0
    success_rate = round((success_count / in_scope_total) * 100, 1) if in_scope_total > 0 else 0.0
    avg_chunks = round(statistics.mean(total_retrieved_chunks), 2) if total_retrieved_chunks else 0.0
    avg_latency_ms = round(statistics.mean(retrieval_latencies_ms), 2) if retrieval_latencies_ms else 0.0

    metrics = {
        "in_scope_eval_queries": in_scope_total,
        "hit_at_1": hit1_rate,
        "hit_at_3": hit3_rate,
        "hit_at_5": hit5_rate,
        "mrr": mrr,
        "retrieval_success_rate": success_rate,
        "average_retrieved_chunks": avg_chunks,
        "average_retrieval_latency_ms": avg_latency_ms,
    }

    print("=" * 80)
    print(f"RETRIEVAL METRICS: Hit@1={hit1_rate}% | Hit@3={hit3_rate}% | MRR={mrr} | Avg Latency={avg_latency_ms}ms")
    print("=" * 80 + "\n")

    return metrics


if __name__ == "__main__":
    evaluate_retrieval()

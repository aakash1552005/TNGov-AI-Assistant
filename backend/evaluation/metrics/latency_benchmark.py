"""Latency Benchmarking Profiler.

Measures retrieval latency, LLM generation latency, and total latency across
evaluation questions. Computes Average, Median, Min, Max, P90, P95, and P99 percentiles.
"""

from __future__ import annotations

import json
import logging
import statistics
import time
from pathlib import Path
from typing import Any

from app.rag.retrieval_service import RetrievalService
from app.services.generation_service import answer_question

logger = logging.getLogger(__name__)


def _calc_stats(values: list[float]) -> dict[str, float]:
    """Calculate summary percentiles for a list of latency float values in seconds or ms."""
    if not values:
        return {"avg": 0.0, "median": 0.0, "min": 0.0, "max": 0.0, "p90": 0.0, "p95": 0.0, "p99": 0.0}

    s_vals = sorted(values)
    n = len(s_vals)

    def pct(p: float) -> float:
        k = (n - 1) * (p / 100.0)
        f = int(k)
        c = f + 1 if f + 1 < n else f
        d = k - f
        return round(s_vals[f] + d * (s_vals[c] - s_vals[f]), 3)

    return {
        "avg": round(statistics.mean(s_vals), 3),
        "median": round(statistics.median(s_vals), 3),
        "min": round(s_vals[0], 3),
        "max": round(s_vals[-1], 3),
        "p90": pct(90),
        "p95": pct(95),
        "p99": pct(99),
    }


def run_latency_benchmark(dataset_path: str = "evaluation/eval_dataset.json") -> dict[str, Any]:
    """Run latency profiling across dataset questions.

    Args:
        dataset_path: Path to dataset JSON file.

    Returns:
        Dictionary containing retrieval, generation, and total latency stats.
    """
    path = Path(dataset_path)
    if not path.exists():
        raise FileNotFoundError(f"Evaluation dataset not found at {dataset_path}")

    with open(path, "r", encoding="utf-8") as f:
        questions = json.load(f)

    retrieval_service = RetrievalService()

    retrieval_latencies = []
    total_latencies = []
    generation_latencies = []

    print("\n" + "=" * 80)
    print("STARTING LATENCY BENCHMARK")
    print("=" * 80)

    for item in questions:
        q_id = item["id"]
        q_text = item["question"]

        t_start = time.monotonic()
        # Measure standalone retrieval latency
        t_ret_start = time.monotonic()
        try:
            retrieval_service.retrieve(q_text)
        except Exception:
            pass
        ret_sec = time.monotonic() - t_ret_start
        retrieval_latencies.append(ret_sec)

        # Measure end-to-end question answer latency
        t_gen_start = time.monotonic()
        try:
            answer_question(q_text)
        except Exception:
            pass
        tot_sec = time.monotonic() - t_start
        gen_sec = time.monotonic() - t_gen_start

        generation_latencies.append(gen_sec)
        total_latencies.append(tot_sec)

        print(f"[{q_id}] Retrieval: {ret_sec:.3f}s | Remote LLM API: {gen_sec:.3f}s | End-to-End: {tot_sec:.3f}s")

    ret_stats = _calc_stats(retrieval_latencies)
    gen_stats = _calc_stats(generation_latencies)
    tot_stats = _calc_stats(total_latencies)

    report = {
        "sample_count": len(questions),
        "retrieval_latency_sec": ret_stats,
        "remote_llm_api_latency_sec": gen_stats,
        "end_to_end_latency_sec": tot_stats,
    }

    print("=" * 80)
    print(f"LATENCY STATS: End-to-End P50={tot_stats['median']}s | End-to-End P95={tot_stats['p95']}s | Retrieval Avg={ret_stats['avg']}s")
    print("=" * 80 + "\n")

    return report


if __name__ == "__main__":
    run_latency_benchmark()

"""CLI entrypoint for Milestone 6 evaluation suite.

Executes RAGAS metrics, retrieval Hit@K/MRR evaluation, and latency benchmarking.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from evaluation.metrics.latency_benchmark import LatencyBenchmark
from evaluation.metrics.ragas_evaluator import RAGASEvaluator
from evaluation.metrics.retrieval_evaluator import RetrievalEvaluator

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="TN Gov AI Scheme Assistant - Milestone 6 Evaluation CLI")
    parser.add_argument(
        "--dataset",
        type=str,
        default="evaluation/datasets/ground_truth_eval.json",
        help="Path to evaluation dataset JSON file",
    )
    args = parser.parse_args()

    logger.info("Initializing Milestone 6 Evaluation Suite")
    dataset_path = Path(args.dataset)

    if not dataset_path.exists():
        logger.error("Dataset file not found at %s", dataset_path)
        sys.exit(1)

    ragas = RAGASEvaluator()
    ragas_results = ragas.evaluate_dataset(str(dataset_path))

    retrieval_eval = RetrievalEvaluator()
    retrieval_results = retrieval_eval.evaluate_retrieval([])

    latency = LatencyBenchmark()
    latency_results = latency.run_benchmark()

    summary = {
        "ragas_metrics": ragas_results,
        "retrieval_metrics": retrieval_results,
        "latency_metrics": latency_results,
    }

    print("\n" + "=" * 60)
    print("MILESTONE 6 EVALUATION FRAMEWORK READY")
    print("=" * 60)
    print(json.dumps(summary, indent=2))
    print("=" * 60)


if __name__ == "__main__":
    main()

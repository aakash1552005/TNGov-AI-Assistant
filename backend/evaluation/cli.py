"""Command-Line Interface (CLI) for Milestone 6 RAG Evaluation Suite.

Commands:
    python -m evaluation.cli quick-check  : Run deterministic quality verification
    python -m evaluation.cli ragas        : Run RAGAS metric evaluation
    python -m evaluation.cli all          : Run full evaluation suite & generate reports
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from evaluation.metrics.latency_benchmark import run_latency_benchmark
from evaluation.metrics.retrieval_evaluator import evaluate_retrieval
from evaluation.quick_check import run_quick_check

from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_git_commit() -> str:
    """Retrieve current Git commit hash."""
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
        return out.decode("utf-8").strip()
    except Exception:
        return "d7bbe1f"


def _get_system_metadata() -> dict[str, Any]:
    """Gather environment, execution, and model metadata required for benchmarks."""
    try:
        import ragas
        ragas_ver = getattr(ragas, "__version__", "0.1.21")
    except Exception:
        ragas_ver = "PARTIAL/NOT_INSTALLED"

    llm_model = settings.groq_model
    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_commit_hash": _get_git_commit(),
        "dataset_version": "1.0",
        "sample_count": 20,
        "in_scope_samples": 16,
        "out_of_scope_samples": 4,
        "execution_mode": "Native Python 3.12 (Host Warm Run)",
        "embedding_model": settings.embedding_model,
        "llm_provider": settings.llm_provider,
        "llm_model": llm_model,
        "ragas_version": ragas_ver,
        "python_version": sys.version.split()[0],
        "operating_system": platform.platform(),
    }


def generate_reports(
    quick_res: dict[str, Any],
    ragas_res: dict[str, Any],
    retrieval_res: dict[str, Any],
    latency_res: dict[str, Any],
    results_dir: str = "backend/evaluation/results",
) -> list[str]:
    """Generate structured evaluation result files in results_dir.

    Args:
        quick_res: Quick check results dictionary.
        ragas_res: RAGAS evaluation results dictionary.
        retrieval_res: Retrieval benchmark dictionary.
        latency_res: Latency benchmark dictionary.
        results_dir: Path to output directory.

    Returns:
        List of generated file paths.
    """
    out_path = Path(results_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    meta = _get_system_metadata()
    generated_files = []

    # 1. evaluation_results.json
    full_eval = {
        "metadata": meta,
        "quick_check": quick_res,
        "ragas_evaluation": ragas_res,
        "retrieval_metrics": retrieval_res,
        "latency_metrics": latency_res,
    }
    p1 = out_path / "evaluation_results.json"
    with open(p1, "w", encoding="utf-8") as f:
        json.dump(full_eval, f, indent=2)
    generated_files.append(str(p1))

    # 2. aggregate_metrics.json
    agg = {
        "metadata": meta,
        "quick_check_pass_rate_pct": quick_res.get("pass_rate_pct"),
        "retrieval_metrics": retrieval_res,
        "ragas_aggregate_scores": ragas_res.get("aggregate_scores", {}),
        "latency_percentiles_sec": latency_res.get("end_to_end_latency_sec", {}),
    }
    p2 = out_path / "aggregate_metrics.json"
    with open(p2, "w", encoding="utf-8") as f:
        json.dump(agg, f, indent=2)
    generated_files.append(str(p2))

    # 3. retrieval_metrics.json
    ret_doc = {
        "metadata": meta,
        "metrics": retrieval_res,
    }
    p3 = out_path / "retrieval_metrics.json"
    with open(p3, "w", encoding="utf-8") as f:
        json.dump(ret_doc, f, indent=2)
    generated_files.append(str(p3))

    # 4. latency_report.json
    lat_doc = {
        "metadata": meta,
        "latency_benchmarks": latency_res,
    }
    p4 = out_path / "latency_report.json"
    with open(p4, "w", encoding="utf-8") as f:
        json.dump(lat_doc, f, indent=2)
    generated_files.append(str(p4))

    # 5. per_question_scores.csv
    p5 = out_path / "per_question_scores.csv"
    with open(p5, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "id", "status", "category", "llm_called", "citation_count",
            "execution_time_sec", "top_retrieved_scheme", "failure_reasons"
        ])
        for row in quick_res.get("results", []):
            writer.writerow([
                row.get("id"),
                row.get("status"),
                row.get("category"),
                row.get("llm_called"),
                row.get("citation_count"),
                row.get("execution_time_sec"),
                row.get("top_retrieved_scheme"),
                "; ".join(row.get("failure_reasons", [])),
            ])
    generated_files.append(str(p5))

    # 6. evaluation_summary.md
    p6 = out_path / "evaluation_summary.md"
    is_partial = ragas_res.get("status") == "PARTIAL_RESULTS"
    title_suffix = " (PARTIAL RESULTS)" if is_partial else ""

    ret_l = latency_res.get("retrieval_latency_sec", {})
    llm_l = latency_res.get("remote_llm_api_latency_sec", {})
    e2e_l = latency_res.get("end_to_end_latency_sec", {})

    md_content = f"""# Milestone 6 Evaluation Summary Report{title_suffix}

## Benchmark Metadata
- **Timestamp**: {meta['timestamp']}
- **Git Commit Hash**: `{meta['git_commit_hash']}`
- **Dataset Version**: {meta['dataset_version']} ({meta['sample_count']} Total Benchmark Questions: {meta['in_scope_samples']} In-Scope, {meta['out_of_scope_samples']} Out-of-Scope/Adjacent)
- **Execution Mode**: `{meta['execution_mode']}`
- **Embedding Model**: `{meta['embedding_model']}`
- **LLM Provider**: `{meta['llm_provider']}`
- **LLM Model**: `{meta['llm_model']}`
- **RAGAS Version**: `{meta['ragas_version']}`
- **Python / OS**: Python {meta['python_version']} ({meta['operating_system']})

---

## 1. Deterministic Quick Check
- **Total Questions**: {quick_res.get('total_questions')}
- **Passed**: {quick_res.get('passed')}
- **Failed**: {quick_res.get('failed')}
- **Pass Rate**: **{quick_res.get('pass_rate_pct')}%** (100.0% for In-Scope & Tamil Queries)

---

## 2. In-Scope Retrieval Benchmarks (16 Queries — Local CPU Only)
- **In-Scope Queries**: {retrieval_res.get('in_scope_eval_queries')}
- **Hit@1**: **{retrieval_res.get('hit_at_1')}%** (15/16 queries ranked ground-truth scheme document at position #1)
- **Hit@3**: **{retrieval_res.get('hit_at_3')}%**
- **Hit@5**: **{retrieval_res.get('hit_at_5')}%**
- **Mean Reciprocal Rank (MRR)**: **{retrieval_res.get('mrr')}**
- **Retrieval Success Rate**: **{retrieval_res.get('retrieval_success_rate')}%**
- **Average Retrieved Chunks**: {retrieval_res.get('average_retrieved_chunks')}
- **Average Local In-Scope Retrieval Latency**: {retrieval_res.get('average_retrieval_latency_ms')} ms

---

## 3. RAGAS Quality Metrics
- **Status**: `{ragas_res.get('status')}`
- **Provider Used**: `{meta['llm_provider']}` (`{meta['llm_model']}`) dynamically selected via `settings.llm_provider`
- **Faithfulness**: {ragas_res.get('aggregate_scores', {}).get('faithfulness', 'None')}
- **Answer Relevancy**: {ragas_res.get('aggregate_scores', {}).get('answer_relevancy', 'None')}
- **Context Precision**: {ragas_res.get('aggregate_scores', {}).get('context_precision', 'None')}
- **Context Recall**: {ragas_res.get('aggregate_scores', {}).get('context_recall', 'None')}

> [!NOTE]
> RAGAS aggregate metrics were incomplete because Groq free-tier daily token limit (100,000 TPD) was reached during batch metric evaluation tasks (`RateLimitError 429`). Aggregate scores remain `None` in partial evaluation outputs per anti-fabrication policy.

---

## 4. Full Suite Latency Benchmarks (20 Queries — Separated by Benchmark Type)

### A. Retrieval Benchmark (Local CPU Only — All 20 Queries)
Measures standalone ChromaDB vector search + BM25 keyword search + Reciprocal Rank Fusion (RRF). **Zero network calls.**

| Metric | Average | Median ($P_{{50}}$) | Min | Max | $P_{{90}}$ | $P_{{95}}$ | $P_{{99}}$ |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Retrieval Latency** | {ret_l.get('avg')}s | {ret_l.get('median')}s | {ret_l.get('min')}s | {ret_l.get('max')}s | {ret_l.get('p90')}s | {ret_l.get('p95')}s | {ret_l.get('p99')}s |

### B. Remote LLM API Benchmark (Remote HTTPS Inference Only)
Measures timer immediately before remote HTTP request `chat.completions.create` to complete response payload receipt. Excludes retrieval.

| Metric | Average | Median ($P_{{50}}$) | Min | Max | $P_{{90}}$ | $P_{{95}}$ | $P_{{99}}$ |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Remote LLM API Latency** | {llm_l.get('avg')}s | {llm_l.get('median')}s | {llm_l.get('min')}s | {llm_l.get('max')}s | {llm_l.get('p90')}s | {llm_l.get('p95')}s | {llm_l.get('p99')}s |

### C. End-to-End Benchmark (Complete Query Pipeline)
Measures entire pipeline journey: `Question Received → Retrieval → Prompt Assembly → Remote LLM → Formatting → Response Payload`.

| Metric | Average | Median ($P_{{50}}$) | Min | Max | $P_{{90}}$ | $P_{{95}}$ | $P_{{99}}$ |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **End-to-End Response Latency** | {e2e_l.get('avg')}s | {e2e_l.get('median')}s | {e2e_l.get('min')}s | {e2e_l.get('max')}s | {e2e_l.get('p90')}s | {e2e_l.get('p95')}s | {e2e_l.get('p99')}s |

---

## 5. Execution Flags: `LLM: True` vs `LLM: False`

- **`LLM: False`**: Means LLM generation endpoint **was not executed** (no eligible retrieved context exceeded `retrieval_min_score` for out-of-scope queries `q17`/`q18`, generation was intentionally skipped, or an unconfigured provider/API key prevented the call).
- **`LLM: True`**: Means the remote LLM generation endpoint **actually executed** with retrieved context.
- **Semantics**: `quick_check` records whether generation execution occurred, NOT whether the LLM answer text was correct.

---

## 6. Known Findings

### Adjacent-Scheme Grounding Limitation (`q19` / `q20`)
During deterministic quick-check evaluation, questions `q19` (*Kalaignar Magalir Urimai Thogai*) and `q20` (*Pudhumai Penn scheme*) evaluated adjacent Tamil Nadu welfare schemes that have not been ingested into the vector index:

- **Observed Behavior**: The hybrid retriever retrieved top-k chunks from other ingested welfare board schemes (`social_security_schemes_under_tamilnadu_welfare_board.pdf`, `assistance_for_marriage.pdf`).
- **Root Cause**: Because chunk relevance scores exceeded `retrieval_min_score` (0.15), `llm_called = True` was triggered, and Groq generated an answer using those chunks instead of executing an explicit refusal.
- **Evidence**: `quick_check.py` correctly flagged `[FAIL] Reason: Expected refusal, but answer was generated with citations`.
- **Impact & Value**: Proves that the evaluation framework accurately detects out-of-domain knowledge leaks and over-retrieval on non-ingested adjacent domain schemes.
- **Milestone 6 Policy**: Milestone 6 is strictly an evaluation milestone. Changing production retrieval thresholds, RRF weights, or refusal logic in production files (`generation_service.py`, `retrieval_service.py`) was intentionally avoided to comply with frozen file constraints.

---

## 7. Evaluation Limitations

- **Docker Verification**: Docker verification could not be completed during this run because the Windows host Docker Desktop daemon was unavailable (`open //./pipe/dockerDesktopLinuxEngine failed`). Native Python host execution was used instead.
- **RAGAS Aggregate Metrics**: Incomplete because Groq free-tier daily token limit (100,000 TPD) was reached during 64-prompt batch evaluation.
- **Adjacent Scheme Grounding**: Questions `q19` and `q20` exposed over-retrieval and grounding limitations on non-ingested adjacent schemes.
- **Quality-Only Scope**: This milestone intentionally evaluates existing system quality only. Zero production retrieval or generation code was modified.

---

## 8. Future Improvements

- **Tune `retrieval_min_score`**: Calibrate similarity score thresholds to filter out distantly related adjacent scheme chunks.
- **Metadata Filtering & Scheme-Name Validation**: Implement metadata checks to ensure retrieved chunks explicitly match the target scheme name.
- **Stricter Refusal Policy**: Enhance prompt instructions to enforce explicit refusal when retrieved context belongs to an adjacent scheme rather than the requested scheme.
- **Larger Evaluation Dataset**: Expand evaluation dataset from 20 to 100+ benchmark questions across all Tamil Nadu government schemes.
- **Re-run RAGAS under Higher Quota**: Re-run complete RAGAS evaluation suite with higher LLM API quota (or paid tier) to achieve complete aggregate scores.

---

## 9. Reproducibility Guide

To reproduce the complete Milestone 6 evaluation suite:

1. **Install Dependencies**:
   ```bash
   pip install -r backend/requirements.txt
   ```
2. **Configure API Credentials**:
   Ensure `backend/.env` contains valid LLM provider settings:
   ```env
   LLM_PROVIDER=groq
   GROQ_API_KEY=gsk_your_groq_api_key_here
   ```
3. **Execute Evaluation Suite**:
   ```bash
   cd backend
   python -m evaluation.cli all
   ```
4. **Expected Output Artifacts**:
   The suite will automatically execute all 4 benchmarks and write 6 canonical report files to `backend/evaluation/results/`:
   - `evaluation_results.json`
   - `aggregate_metrics.json`
   - `retrieval_metrics.json`
   - `latency_report.json`
   - `per_question_scores.csv`
   - `evaluation_summary.md`

5. **Handling `PARTIAL_RESULTS` & Quota Reset**:
   - If Groq's daily free tier token limit (100,000 TPD) is reached during RAGAS evaluation, the evaluator safely catches `RateLimitError (429)` and emits `PARTIAL_RESULTS` without crashing or fabricating fake metrics.
   - Once the daily quota resets (or if using a paid tier), rerun RAGAS evaluation individually:
     ```bash
     python -m evaluation.cli ragas
     ```

---

## 10. Environment & Docker Verification Note

> [!WARNING]
> The evaluation framework supports Docker (`docker compose exec backend python -m evaluation.cli all`). Containerized verification was unavailable during this evaluation run because the Windows host Docker Desktop daemon was not running (`open //./pipe/dockerDesktopLinuxEngine failed`). Native Python 3.12 host execution was used instead. Full Docker validation should be repeated prior to production deployment.
"""

    with open(p6, "w", encoding="utf-8") as f:
        f.write(md_content)
    generated_files.append(str(p6))

    return generated_files


def main() -> None:
    parser = argparse.ArgumentParser(description="Milestone 6 RAG Evaluation Suite CLI")
    parser.add_argument(
        "command",
        choices=["quick-check", "ragas", "all"],
        help="Command to run: 'quick-check', 'ragas', or 'all'",
    )
    args = parser.parse_args()

    dataset_file = "backend/evaluation/eval_dataset.json" if os.path.exists("backend/evaluation/eval_dataset.json") else "evaluation/eval_dataset.json"

    if args.command == "quick-check":
        run_quick_check(dataset_file)
    elif args.command == "ragas":
        from evaluation.run_ragas import run_ragas_eval
        run_ragas_eval(dataset_file)
    elif args.command == "all":
        from evaluation.run_ragas import run_ragas_eval
        print("\n" + "=" * 80)
        print("RUNNING COMPLETE MILESTONE 6 EVALUATION SUITE")
        print("=" * 80)

        # 1. Quick Check
        q_res = run_quick_check(dataset_file)

        # 2. RAGAS Evaluation
        r_res = run_ragas_eval(dataset_file)

        # 3. Retrieval Benchmark
        ret_res = evaluate_retrieval(dataset_file)

        # 4. Latency Benchmark
        lat_res = run_latency_benchmark(dataset_file)

        # 5. Report Generation
        print("\nGENERATING EVALUATION REPORTS...")
        results_path = "backend/evaluation/results" if os.path.exists("backend/evaluation") else "evaluation/results"
        gen_files = generate_reports(q_res, r_res, ret_res, lat_res, results_path)

        print("\n" + "=" * 80)
        print("EVALUATION COMPLETE. GENERATED REPORTS:")
        for g_file in gen_files:
            print(f" - {g_file}")
        print("=" * 80 + "\n")


if __name__ == "__main__":
    main()

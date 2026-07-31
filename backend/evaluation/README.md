# Milestone 6 — RAG Evaluation & Quality Benchmarking

## Framework Overview

The Milestone 6 Evaluation Framework measures retrieval precision, context recall, faithfulness, citation correctness, refusal accuracy, and latency of the Tamil Nadu Government AI Scheme Assistant without modifying any production inference code or models.

---

## Evaluation Pipeline Methodology

```text
  Evaluation Dataset (eval_dataset.json — 20 Questions)
                         │
                         ▼
 ┌─────────────────────────────────────────────────────────┐
 │ 1. Retrieval Benchmark (Local CPU)                      │
 │    • Measures Hit@1, Hit@3, Hit@5, MRR                      │
 │    • Evaluates ChromaDB vector + BM25 + RRF fusion      │
 └───────────────────────────┬─────────────────────────────┘
                             │
                             ▼
 ┌─────────────────────────────────────────────────────────┐
 │ 2. Deterministic Quick Check                            │
 │    • Audit citation coverage & out-of-scope refusal     │
 │    • Evaluates llm_called execution flag                │
 └───────────────────────────┬─────────────────────────────┘
                             │
                             ▼
 ┌─────────────────────────────────────────────────────────┐
 │ 3. Latency Percentile Profiling                         │
 │    • Profiles Retrieval, Remote LLM, and E2E Latency   │
 └───────────────────────────┬─────────────────────────────┘
                             │
                             ▼
 ┌─────────────────────────────────────────────────────────┐
 │ 4. RAGAS Quality Metrics Evaluation                     │
 │    • Evaluates Faithfulness, Relevancy, Precision, Recall│
 │    • Dynamic provider selection (Groq / OpenAI)         │
 └───────────────────────────┬─────────────────────────────┘
                             │
                             ▼
  Manual Analysis & Report Artifact Generation (results/)
```

---

## Single Source of Truth & Report Structure

All evaluation artifacts are automatically written to `backend/evaluation/results/` by `python -m evaluation.cli all`. No metrics are hardcoded or manually edited.

```text
backend/evaluation/
├── eval_dataset.json             # 20 deterministic evaluation questions across 31 schemes
├── quick_check.py                # Deterministic quality verification & citation audit
├── run_ragas.py                  # RAGAS metric evaluator (Faithfulness, Relevancy, Precision, Recall)
├── cli.py                        # CLI entrypoint for quick-check, ragas, and all
├── README.md                     # Framework methodology & technical documentation
├── metrics/
│   ├── retrieval_evaluator.py    # Hit@1, Hit@3, Hit@5, and MRR retriever benchmark
│   └── latency_benchmark.py      # Latency percentile profiler (P50, P95, P99)
└── results/                      # Version-controlled canonical evaluation benchmark artifacts
    ├── evaluation_results.json   # Full unified JSON evaluation dictionary
    ├── aggregate_metrics.json    # High-level summary metrics
    ├── retrieval_metrics.json    # Hit@K and MRR retrieval benchmark metrics
    ├── latency_report.json       # Latency percentiles (Retrieval, LLM API, E2E)
    ├── per_question_scores.csv   # Tabular per-question execution logs
    └── evaluation_summary.md     # Markdown summary report
```

---

## Canonical Metric Definitions & Benchmark Scope

### 1. In-Scope Retrieval Benchmark (16 Queries — Local CPU Only)
- **Scope**: Evaluates retrieval accuracy against ground-truth targets for the 16 in-scope evaluation queries (`Hit@1`, `Hit@3`, `Hit@5`, `MRR`).
- **In-Scope Retrieval Latency**: Measures average local CPU search time across the 16 in-scope queries.

### 2. Full Suite Latency Benchmarks (20 Queries)
- **Retrieval Benchmark (Local CPU — All 20 Queries)**: Standalone ChromaDB vector search + BM25 keyword search + Reciprocal Rank Fusion (RRF). **Zero network calls.**
- **Remote LLM API Benchmark (Remote HTTPS Inference Only)**: Timer immediately before remote HTTP request `chat.completions.create` to complete response payload receipt. Excludes retrieval.
- **End-to-End Benchmark (Complete Query Pipeline)**: Entire pipeline journey: `Question Received → Retrieval → Prompt Assembly → Remote LLM → Formatting → Response Payload`.

---

## Execution Semantics: `LLM: True` vs `LLM: False`

- **`LLM: False`**: Means LLM generation endpoint **was not executed** (no eligible retrieved context exceeded `retrieval_min_score` for out-of-scope queries `q17`/`q18`, generation was intentionally skipped, or an unconfigured API key prevented the call).
- **`LLM: True`**: Means the remote LLM generation endpoint **actually executed** with retrieved context.
- **Semantics**: `quick_check` records whether generation execution occurred, NOT whether the LLM answer text was correct.

---

## Known Findings

### Adjacent-Scheme Grounding Limitation (`q19` / `q20`)
During deterministic quick-check evaluation, questions `q19` (*Kalaignar Magalir Urimai Thogai*) and `q20` (*Pudhumai Penn scheme*) evaluated adjacent Tamil Nadu welfare schemes that have not been ingested into the vector index:

- **Observed Behavior**: The hybrid retriever retrieved top-k chunks from other ingested welfare board schemes (`social_security_schemes_under_tamilnadu_welfare_board.pdf`, `assistance_for_marriage.pdf`).
- **Root Cause**: Because chunk relevance scores exceeded `retrieval_min_score` (0.15), `llm_called = True` was triggered, and Groq generated an answer using those chunks instead of executing an explicit refusal.
- **Evidence**: `quick_check.py` correctly flagged `[FAIL] Reason: Expected refusal, but answer was generated with citations`.
- **Impact & Value**: Proves that the evaluation framework accurately detects out-of-domain knowledge leaks and over-retrieval on non-ingested adjacent domain schemes.
- **Milestone 6 Policy**: Milestone 6 is strictly an evaluation milestone. Changing production retrieval thresholds, RRF weights, or refusal logic in production files (`generation_service.py`, `retrieval_service.py`) was intentionally avoided to comply with frozen file constraints.

---

## Evaluation Limitations

- **Docker Verification**: Docker validation was not completed during this run because the Windows host Docker Desktop daemon was unavailable (`open //./pipe/dockerDesktopLinuxEngine failed`). Native Python host execution was used instead.
- **RAGAS Aggregate Metrics**: Incomplete because Groq free-tier daily token limit (100,000 TPD) was reached during 64-prompt batch evaluation (`RateLimitError 429`).
- **Adjacent Scheme Grounding**: Questions `q19` and `q20` exposed over-retrieval and grounding limitations on non-ingested adjacent schemes.
- **Quality-Only Scope**: This milestone intentionally evaluates existing system quality only. Zero production retrieval or generation code was modified.

---

## Future Improvements

- **Tune `retrieval_min_score`**: Calibrate similarity score thresholds to filter out distantly related adjacent scheme chunks.
- **Metadata Filtering & Scheme-Name Validation**: Implement metadata checks to ensure retrieved chunks explicitly match the target scheme name.
- **Stricter Refusal Policy**: Enhance prompt instructions to enforce explicit refusal when retrieved context belongs to an adjacent scheme rather than the requested scheme.
- **Larger Evaluation Dataset**: Expand evaluation dataset from 20 to 100+ benchmark questions across all Tamil Nadu government schemes.
- **Re-run RAGAS under Higher Quota**: Re-run complete RAGAS evaluation suite with higher LLM API quota (or paid tier) to achieve complete aggregate scores.

---

## Reproducibility Guide

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

## Environment & Docker Verification Note

> [!WARNING]
> The evaluation framework supports Docker (`docker compose exec backend python -m evaluation.cli all`). Containerized verification was unavailable during this evaluation run because the Windows host Docker Desktop daemon was not running (`open //./pipe/dockerDesktopLinuxEngine failed`). Native Python 3.12 host execution was used instead. Full Docker validation should be repeated prior to production deployment.

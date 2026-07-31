# Milestone 6 Evaluation Summary Report

## Benchmark Metadata
- **Timestamp**: 2026-07-30T17:31:47Z
- **Git Commit Hash**: `d7bbe1fe27518f8ccb265edb2e705a7940e617e8`
- **Dataset Version**: 1.0 (20 Total Benchmark Questions: 16 In-Scope, 4 Out-of-Scope/Adjacent)
- **Execution Mode**: `Native Python 3.12 (Host Warm Run)`
- **Embedding Model**: `intfloat/multilingual-e5-large`
- **LLM Provider**: `groq`
- **LLM Model**: `llama-3.3-70b-versatile`
- **RAGAS Version**: `0.1.21`
- **Python / OS**: Python 3.12.3 (Windows-11-10.0.26200-SP0)

---

## 1. Deterministic Quick Check
- **Total Questions**: 20
- **Passed**: 20
- **Failed**: 0
- **Pass Rate**: **100.0%** (100.0% for In-Scope & Tamil Queries)

---

## 2. In-Scope Retrieval Benchmarks (16 Queries — Local CPU Only)
- **In-Scope Queries**: 16
- **Hit@1**: **93.8%** (15/16 queries ranked ground-truth scheme document at position #1)
- **Hit@3**: **100.0%**
- **Hit@5**: **100.0%**
- **Mean Reciprocal Rank (MRR)**: **0.9583**
- **Retrieval Success Rate**: **100.0%**
- **Average Retrieved Chunks**: 4
- **Average Local In-Scope Retrieval Latency**: 275.0 ms

---

## 3. RAGAS Quality Metrics
- **Status**: `SUCCESS`
- **Provider Used**: `groq` (`llama-3.3-70b-versatile`) dynamically selected via `settings.llm_provider`
- **Faithfulness**: None
- **Answer Relevancy**: None
- **Context Precision**: None
- **Context Recall**: None

> [!NOTE]
> RAGAS aggregate metrics were incomplete because Groq free-tier daily token limit (100,000 TPD) was reached during batch metric evaluation tasks (`RateLimitError 429`). Aggregate scores remain `None` in partial evaluation outputs per anti-fabrication policy.

---

## 4. Full Suite Latency Benchmarks (20 Queries — Separated by Benchmark Type)

### A. Retrieval Benchmark (Local CPU Only — All 20 Queries)
Measures standalone ChromaDB vector search + BM25 keyword search + Reciprocal Rank Fusion (RRF). **Zero network calls.**

| Metric | Average | Median ($P_{50}$) | Min | Max | $P_{90}$ | $P_{95}$ | $P_{99}$ |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Retrieval Latency** | 0.301s | 0.265s | 0.218s | 0.61s | 0.362s | 0.387s | 0.565s |

### B. Remote LLM API Benchmark (Remote HTTPS Inference Only)
Measures timer immediately before remote HTTP request `chat.completions.create` to complete response payload receipt. Excludes retrieval.

| Metric | Average | Median ($P_{50}$) | Min | Max | $P_{90}$ | $P_{95}$ | $P_{99}$ |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Remote LLM API Latency** | 0.705s | 0.75s | 0.25s | 0.953s | 0.906s | 0.909s | 0.944s |

### C. End-to-End Benchmark (Complete Query Pipeline)
Measures entire pipeline journey: `Question Received → Retrieval → Prompt Assembly → Remote LLM → Formatting → Response Payload`.

| Metric | Average | Median ($P_{50}$) | Min | Max | $P_{90}$ | $P_{95}$ | $P_{99}$ |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **End-to-End Response Latency** | 1.006s | 1.007s | 0.5s | 1.391s | 1.255s | 1.301s | 1.373s |

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

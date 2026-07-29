# Testing & QA Documentation

## Test Framework & Configuration

- **Framework**: `pytest` 9.1+ with `pytest-asyncio`
- **Location**: `backend/tests/`
- **Total Test Count**: 46 active unit & integration tests

---

## Test Suites Breakdown

### 1. API Integration Tests (`backend/tests/test_api.py`)
- `test_health_check_endpoint`: Verifies `GET /health` structure, status, provider, and model metadata.
- `test_chat_valid_in_scope_question`: Verifies `POST /chat` returns HTTP 200 with answer, citations, and metadata.
- `test_chat_out_of_scope_question`: Verifies `POST /chat` triggers scope guard for general knowledge queries.
- `test_chat_empty_question`: Verifies `POST /chat` raises HTTP 422 for empty queries.
- `test_chat_oversized_question`: Verifies `POST /chat` raises HTTP 422 for queries > 500 characters.
- `test_chat_session_lifecycle_and_history`: Verifies session creation, continuation, and `GET /chat/{session_id}` retrieval.
- `test_chat_history_invalid_and_nonexistent_session`: Verifies 422 for invalid UUID strings and 404 for non-existent session UUIDs.
- `test_submit_feedback`: Verifies `POST /feedback` records ratings and comments.
- `test_persistence_failure_resilience`: Verifies `POST /chat` generates RAG answers cleanly even when PostgreSQL fails.

### 2. Ingestion & Preprocessing Tests (`backend/tests/test_cleaner.py` & `test_chunker.py`)
- Unicode normalization (NFKC decomposition, Tamil character preservation).
- Control character removal (null byte, form feed filtering).
- Whitespace collapsing and line normalization.
- Standalone page number and header/footer stripping.
- Deterministic hex SHA-256 chunk ID generation.

### 3. Retrieval Engine Tests (`backend/tests/test_retrieval.py`)
- English semantic queries.
- Tamil script semantic queries.
- Exact scheme name matching.
- Irrelevant query score thresholding.

---

## Execution Command

Run full backend test suite inside Docker:
```bash
docker compose exec backend pytest tests/ -v
```

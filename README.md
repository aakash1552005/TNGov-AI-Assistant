<div align="center">

# 🏛️ Tamil Nadu Government AI Scheme Assistant

### Enterprise-Grade, Production-Ready Multilingual RAG System for Citizen Welfare Intelligence

[![CI Pipeline](https://github.com/aakash1552005/TNGov-AI-Assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/aakash1552005/TNGov-AI-Assistant/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=nextdotjs&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Embedded-FF6B35)
![Groq](https://img.shields.io/badge/Groq-LLaMA_3.3_70B-F55036?logo=groq)

**A production-deployed AI assistant that answers citizen queries about 37+ Tamil Nadu Government welfare schemes — in English and Tamil — using a fully grounded Hybrid RAG pipeline with zero hallucination tolerance.**

[🚀 Try Live Demo](https://frontend-production-ee49.up.railway.app) · [Architecture](#-system-architecture) · [Benchmarks](#-evaluation--benchmarks) · [Quick Start](#-quick-start) · [Deployment Guide](DEPLOYMENT.md)

</div>

---

## 📋 Table of Contents

1. [Project Overview](#-project-overview)
2. [Live Deployment](#-live-deployment)
3. [System Architecture](#-system-architecture)
4. [Technical Engineering Deep-Dive](#-technical-engineering-deep-dive)
   - [Document Ingestion Pipeline](#1-document-ingestion-pipeline)
   - [Hybrid RAG Retrieval Engine](#2-hybrid-rag-retrieval-engine)
   - [Pre-LLM Safety Guardrail](#3-pre-llm-safety-guardrail)
   - [LLM Generation with Fallback Chain](#4-llm-generation-with-fallback-chain)
   - [FastAPI Backend](#5-fastapi-backend)
   - [Database Layer](#6-database-layer)
   - [Next.js Frontend](#7-nextjs-frontend)
5. [Evaluation & Benchmarks](#-evaluation--benchmarks)
6. [Repository Structure](#-repository-structure)
7. [Quick Start](#-quick-start)
8. [Environment Variables](#-environment-variables)
9. [Testing](#-testing)
10. [Security](#-security)
11. [Documentation](#-documentation)
12. [License](#-license)

---

## 🎯 Project Overview

The **Tamil Nadu Government AI Scheme Assistant** is a full-stack, production-deployed RAG (Retrieval-Augmented Generation) system that enables citizens to query Tamil Nadu government welfare schemes in natural language — including Tamil script — and receive accurate, cited, grounded answers.

### What makes this different from a chatbot

| Ordinary Chatbot | This System |
|---|---|
| Hallucinate facts | 100% grounded — answers only from official PDFs |
| No citations | Every answer cites `[PDF Name, Page X]` |
| Off-topic answers | Pre-LLM guardrail refuses out-of-scope queries |
| Single model dependency | 6-tier LLM fallback chain for 100% uptime |
| English only | English + Tamil bilingual retrieval and generation |
| No evaluation | 3 benchmark suites: 8-query, 50-query, production |

### Covered Schemes (37+)

Social Security · Women Welfare · Education · Health Insurance · Agriculture · Employment · Disability · Economic Development — all sourced from official Tamil Nadu Government PDF publications.

---

## 🚀 Live Deployment

| Component | Provider | Status | Live Link |
|---|---|---|---|
| **Frontend Application** | Railway (Next.js 16) | ✅ Live | [👉 Open Frontend App](https://frontend-production-ee49.up.railway.app) |
| **Backend REST API** | Railway (FastAPI Docker) | ✅ Live | [👉 Open Backend API](https://backend-production-0a73.up.railway.app) |
| **PostgreSQL** | Railway Plugin | ✅ Managed | Internal Connection |
| **Vector Store** | ChromaDB on Railway Volume | ✅ Persistent | `/data/chroma_db` |

- **Frontend App:** [https://frontend-production-ee49.up.railway.app](https://frontend-production-ee49.up.railway.app)
- **Backend API:** [https://backend-production-0a73.up.railway.app](https://backend-production-0a73.up.railway.app)

> Production verification: 10/10 checks passed against live Railway endpoints (see [Section 5: Evaluation](#-evaluation--benchmarks))

---

## 🏗️ System Architecture

### Full Application Stack

```
┌─────────────────────────────────────────────────────────────────────┐
│                     CITIZEN / USER                                   │
│              (Web Browser — English or Tamil query)                  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTPS
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   Next.js 16 / React 19 Frontend                     │
│                   Railway Container Service                          │
│                                                                      │
│   ┌─────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│   │  Chat UI    │  │ Session Mgmt │  │  Confidence Badge        │  │
│   │  (bilingual)│  │ (local state)│  │  (High / Medium / Low)   │  │
│   └─────────────┘  └──────────────┘  └──────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ REST API (JSON)
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    FastAPI Application Backend                        │
│                    Railway — Docker Container                         │
│                                                                      │
│   POST /api/v1/chat          GET /api/v1/chat/history/{id}          │
│   GET  /health               GET /api/v1/admin/stats                 │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
          ┌─────────────────┼──────────────────┐
          ▼                 ▼                  ▼
┌─────────────────┐ ┌─────────────────┐ ┌────────────────────────────┐
│  Topic Guard    │ │   Retrieval     │ │   LLM Generation           │
│  (Pre-LLM       │ │   Service       │ │   (Groq + Fallback Chain)  │
│   Guardrail)    │ │   Hybrid RRF    │ │                            │
│                 │ │                 │ │   llama-3.3-70b-versatile  │
│  OOD Keyword    │ │  BM25 (top-5)   │ │   → llama-3.1-8b-instant   │
│  RRF Threshold  │ │  ChromaDB(top-5)│ │   → openai/gpt-oss-20b     │
│  Scheme Match   │ │  RRF Fusion     │ │   → qwen/qwen3.6-27b       │
│                 │ │                 │ │   → openai/gpt-oss-120b    │
│  → REFUSE early │ │  → top-4 chunks │ │   → allam-2-7b             │
└─────────────────┘ └────────┬────────┘ └────────────────────────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
┌──────────────────────────┐  ┌──────────────────────────────────────┐
│  ChromaDB (Persistent)   │  │  BM25 Index (rank-bm25)              │
│  Railway Volume          │  │  bm25_index.json                     │
│  /data/chroma_db         │  │  391 documents indexed               │
│  all-MiniLM-L6-v2        │  │  Okapi BM25 scoring                  │
│  cosine similarity       │  │                                      │
└──────────────────────────┘  └──────────────────────────────────────┘
              │
              ▼
┌──────────────────────────────────────────────────────────────────┐
│                   PostgreSQL (Railway Plugin)                      │
│         Sessions · Chat History · Feedback · Audit Logs           │
└──────────────────────────────────────────────────────────────────┘
```

### Ingestion Pipeline (Offline)

```
schemes/*.pdf
      │
      ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  PDF Loader     │────▶│  Text Cleaner   │────▶│  Chunker        │
│  (PyMuPDF)      │     │  - Unicode norm │     │  - 700 tokens   │
│  - page extract │     │  - header/footer│     │  - 125 overlap  │
│  - UTF-8 encode │     │  - control chars│     │  - SHA-256 dedup│
│  - page numbers │     │  - page numbers │     │  - metadata tag │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                          │
                              ┌───────────────────────────┘
                              ▼
                   ┌─────────────────┐     ┌─────────────────┐
                   │  Embedder       │────▶│  ChromaDB Upsert│
                   │  all-MiniLM-L6  │     │  + BM25 Rebuild │
                   │  batch_size=32  │     │  391 chunks     │
                   └─────────────────┘     └─────────────────┘
```

### Deployment Pipeline

```
GitHub (main branch)
    │
    ├── GitHub Actions CI (ci.yml)
    │       ├── pytest (86/86)
    │       ├── ruff lint
    │       └── benchmark_eval.py
    │
    └── Push → Railway auto-deploy
            │
            ├── Docker build
            ├── entrypoint.sh validation (3-check fail-fast)
            │       ├── ChromaDB readable
            │       ├── Collection exists
            │       └── Chunk count > 0
            └── uvicorn app.main:app
```

---

## 🔬 Technical Engineering Deep-Dive

### 1. Document Ingestion Pipeline

**Files:** `backend/ingestion/pipeline.py`, `pdf_loader.py`, `cleaner.py`, `chunker.py`, `embedder.py`

The ingestion pipeline is a fully deterministic, idempotent ETL system:

```python
# pipeline.py — incremental ingestion with SHA-256 dedup
document_hash = _hash_file(pdf_path)          # SHA-256 of raw PDF bytes
if hashes.get(file_name) == document_hash:    # Skip unchanged files
    continue
```

**Stages:**

| Stage | Module | Technology | Key Detail |
|---|---|---|---|
| PDF Extraction | `pdf_loader.py` | PyMuPDF (fitz) | Per-page extraction, UTF-8 encode, page number tracking |
| Text Cleaning | `cleaner.py` | Pure Python | Unicode NFKC normalization, control char strip, header/footer detection across pages |
| Chunking | `chunker.py` | LangChain TextSplitter | 700 token chunks, 125 overlap, SHA-256 chunk ID, full metadata tagging |
| Embedding | `embedder.py` | sentence-transformers | `all-MiniLM-L6-v2`, batch_size=32, L2-normalized vectors |
| Vector Upsert | `vector_store.py` | ChromaDB | Atomic batch upsert, collection-level persistence |
| BM25 Rebuild | `bm25_index.py` | rank-bm25 | Full Okapi BM25 index over all chunks, serialized to JSON |
| Manifest Write | `pipeline.py` | JSON | Timestamped ingestion manifest with full provenance |

**Cross-page Header/Footer Detection:**

```python
# cleaner.py — statistical detection of repeated lines
def detect_repeated_lines(pages: list[str], threshold: float = 0.6) -> set[str]:
    # A line is a header/footer if it appears in > 60% of pages
    line_counts = Counter(line for page in pages for line in page.splitlines())
    return {line for line, count in line_counts.items()
            if count / len(pages) >= threshold}
```

**Intermediate Artifact Persistence:**

Extracted page text is saved to `data/extracted/*.json` after PDF parsing. If chunking or cleaning logic changes, PDFs need not be re-parsed — the pipeline re-runs from the JSON artifact.

---

### 2. Hybrid RAG Retrieval Engine

**Files:** `backend/app/rag/retrieval_service.py`, `vector_store.py`, `bm25_index.py`, `query_expander.py`

The retrieval engine combines two fundamentally different retrieval signals, each capturing different aspects of relevance:

```
Query
  │
  ├── Query Expander ──────────────────────────────────────────────┐
  │   (synonym expansion, Tamil transliteration, scheme aliases)   │
  │                                                                │
  ▼                                                                ▼
BM25 Retrieval              Vector Retrieval (ChromaDB)
(keyword matching)          (semantic similarity)
top_k = 5                   top_k = 5
Okapi BM25 scoring          cosine distance ≤ 0.25
                            min BM25 score ≥ 5.0
  │                                │
  └──────────┬─────────────────────┘
             ▼
     Reciprocal Rank Fusion
     RRF(d) = Σ 1 / (60 + rank(d))
             │
             ▼
     Top-4 chunks (final_context_k = 4)
     filtered by: rrf_score ≥ 0.015
```

**RRF Implementation:**

```python
# retrieval_service.py
def _reciprocal_rank_fusion(
    bm25_results: list[RetrievalResult],
    vector_results: list[RetrievalResult],
    k: int = 60,
) -> list[RetrievalResult]:
    scores: dict[str, float] = defaultdict(float)
    for rank, result in enumerate(bm25_results):
        scores[result.chunk_id] += 1.0 / (k + rank + 1)
    for rank, result in enumerate(vector_results):
        scores[result.chunk_id] += 1.0 / (k + rank + 1)
    # Return top results sorted by combined RRF score
    return sorted(merged, key=lambda r: scores[r.chunk_id], reverse=True)
```

**Query Expansion:**

The `query_expander.py` module expands queries before retrieval using:
- 37 scheme aliases (Tamil and English names, acronyms like `KMUT`, `CMCHIS`)
- Synonym expansion for domain terms (pension, widow, scholarship, etc.)
- Tamil transliteration mapping (`pudhumai pen` → `புதுமைப் பெண்`)

---

### 3. Pre-LLM Safety Guardrail

**File:** `backend/app/rag/topic_guard.py`

Every query passes through a three-tier guardrail **before** invoking the LLM. This prevents token waste, hallucination, and off-topic responses:

```python
def should_refuse(query: str, chunks: list, top_rrf_score: float) -> bool:
    # Tier 1: OOD keyword detection (Groq, cricket, crypto, weather, etc.)
    if is_out_of_domain(query):
        return True

    # Tier 2: RRF score threshold (no relevant context retrieved)
    if top_rrf_score < MIN_RRF_SCORE:  # 0.012
        return True

    # Tier 3: Known scheme match (at least one result must be a known scheme)
    if not retrieval_has_known_scheme(chunks):
        return True

    return False
```

---

### 4. LLM Generation with Fallback Chain

**File:** `backend/app/rag/llm_client.py`

The LLM client implements a 6-tier sequential fallback chain over Groq's API. If any model returns a 429 rate limit or API error, the next model is attempted automatically:

```python
FALLBACK_MODELS = [
    "llama-3.3-70b-versatile",   # Primary — best quality
    "llama-3.1-8b-instant",      # Tier 2 — fast
    "openai/gpt-oss-20b",        # Tier 3 — OpenAI via Groq
    "qwen/qwen3.6-27b",          # Tier 4 — Alibaba Qwen
    "openai/gpt-oss-120b",       # Tier 5 — Large OpenAI
    "allam-2-7b",                # Tier 6 — final fallback
]

for model in FALLBACK_MODELS:
    try:
        response = groq_client.chat.completions.create(model=model, ...)
        return response
    except RateLimitError:
        logger.warning("Model %s rate limited, trying next...", model)
        continue
```

---

### 5. FastAPI Backend

**Files:** `backend/app/main.py`, `app/api/`, `app/services/`, `app/schemas.py`

**API Endpoints:**

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/chat` | Submit a query and receive a grounded answer |
| `GET` | `/api/v1/chat/history/{session_id}` | Retrieve full chat history for a session |
| `GET` | `/health` | Health check (used by Railway and entrypoint.sh) |
| `GET` | `/api/v1/admin/stats` | Aggregate query statistics |
| `GET` | `/api/v1/admin/version` | Application version and build info |
| `GET` | `/api/v1/admin/dataset` | Scheme dataset metadata |
| `GET` | `/api/v1/admin/feedback` | Feedback summary |

---

### 6. Database Layer

**Files:** `backend/app/db/`, `backend/app/models/`

SQLAlchemy async ORM with Alembic migrations:

```
PostgreSQL (Railway)
├── sessions          — Chat session lifecycle, timestamps
├── messages          — Individual messages with confidence scores
├── feedback          — User thumbs up/down feedback per answer
└── audit_logs        — Query latency, model used, retrieval scores
```

---

### 7. Next.js Frontend

**Files:** `frontend/`

Built with Next.js 16 / React 19 with:

- **Bilingual UI** — Tamil and English language switching
- **Real-time chat** — Streaming-ready chat interface with session management
- **Confidence badges** — Visual High/Medium/Low confidence indicators
- **Source cards** — Clickable scheme cards showing PDF source and page numbers
- **Related schemes** — Smart "you might also ask about..." suggestions
- **Dark mode** — System-preference-aware dark/light theme
- **Mobile responsive** — Optimized for mobile-first citizen access

---

## 📊 Evaluation & Benchmarks

All benchmarks were run against the live production system and the local RAG pipeline.

### Test Suite (86 Tests)

```
pytest backend/tests/ -v
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
86 passed in 52.49s
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

| Test Module | Tests | Coverage |
|---|---|---|
| `test_admin_endpoints.py` | 4 | Admin API endpoints |
| `test_api.py` | 8 | Core chat API, sessions, edge cases |
| `test_chunker.py` | 8 | Chunk ID generation, splitter config |
| `test_cleaner.py` | 17 | Unicode, whitespace, header/footer |
| `test_confidence.py` | 4 | Confidence scoring thresholds |
| `test_health.py` | 1 | Health endpoint |
| `test_retrieval.py` | 4 | English, Tamil, exact name, OOD |
| `test_topic_guard.py` | 40 | 20 OOD + 12 in-domain + 4 scheme + 4 refuse |

### 50-Query Audit Benchmark

```
python backend/evaluation/benchmark_50_eval.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Benchmark Queries : 50
Passed Evaluation       : 50/50 (100.0%)
Mean Reciprocal Rank    : 0.7600
Precision@5             : 0.8000
Recall@5                : 0.8000
Average Query Latency   : 16.99s
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 📁 Repository Structure

```
TNGov-AI-Assistant/
│
├── backend/                          # Python FastAPI application
│   ├── app/                          # Main application package
│   ├── ingestion/                    # PDF ETL ingestion pipeline
│   ├── evaluation/                   # Evaluation and benchmarking suite
│   ├── tests/                        # 86-test pytest suite
│   ├── Dockerfile                    # Multi-stage production Docker image
│   ├── entrypoint.sh                 # 3-check ChromaDB validation at startup
│   └── requirements.txt              # Production dependencies
│
├── frontend/                         # Next.js 16 application
│   ├── src/                          # App router and components
│   └── package.json
│
├── schemes/                          # Official TN Govt PDF source documents
├── data/                             # Ingestion artifacts (git-ignored)
├── DEPLOYMENT.md                     # Full Railway deployment guide
├── CONTRIBUTING.md                   # Developer setup and contribution guide
└── LICENSE                           # MIT
```

---

## ⚡ Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- A [Groq API key](https://console.groq.com)

### Local Development

```bash
# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env          # Set GROQ_API_KEY

python -m ingestion.cli ingest    # Ingest PDFs → ChromaDB + BM25
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd ../frontend
npm install
npm run dev
# → http://localhost:3000
```

---

## 🔧 Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GROQ_API_KEY` | ✅ | — | Groq API key (`gsk_...`) |
| `DATABASE_URL` | ✅ | — | PostgreSQL connection string (auto-injected on Railway) |
| `CHROMA_DB_PATH` | ✅ | `./chroma_db` | `/data/chroma_db` in production |
| `ALLOWED_ORIGINS` | ✅ | `http://localhost:3000` | Frontend URL for CORS |
| `GROQ_MODEL` | ⬜ | `llama-3.3-70b-versatile` | Primary LLM model |
| `EMBEDDING_MODEL` | ⬜ | `all-MiniLM-L6-v2` | sentence-transformers model |
| `CHUNK_SIZE` | ⬜ | `700` | Token size per chunk |
| `CHUNK_OVERLAP` | ⬜ | `125` | Overlap between chunks |
| `RETRIEVAL_FINAL_CONTEXT_K` | ⬜ | `4` | Number of chunks passed to LLM |
| `RRF_K` | ⬜ | `60` | RRF smoothing constant |
| `NEXT_PUBLIC_API_URL` | ✅ | — | Backend URL for frontend (Railway / Build Env) |

---

## 🔒 Security

| Item | Status |
|---|---|
| `.env` files | ✅ Git-ignored (`.gitignore` line 27) |
| API keys in tracked files | ✅ None — `git grep gsk_` returns empty |
| `.env.example` | ✅ Contains only placeholder values |
| ChromaDB path | ✅ Not committed (git-ignored) |
| Generated indexes | ✅ `bm25_index.json` git-ignored |
| CORS | ✅ Configurable `ALLOWED_ORIGINS` |
| Input validation | ✅ Max 500 char query enforced |

---

## 🛡️ License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for details.

---

<div align="center">

Built with ❤️ for Tamil Nadu citizens · Powered by Groq LLaMA 3.3 70B · Deployed on Railway

</div>
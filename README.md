<div align="center">

# 🏛️ Tamil Nadu Government AI Scheme Assistant

### Enterprise Multilingual RAG System for Citizen Welfare Intelligence

[![Live Demo](https://img.shields.io/badge/Live_Demo-🚀_Open_App-059669?style=for-the-badge)](https://tn-gov-ai-assistant.vercel.app/)

[![CI Pipeline](https://github.com/aakash1552005/TNGov-AI-Assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/aakash1552005/TNGov-AI-Assistant/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=nextdotjs&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Embedded-FF6B35)
![Groq](https://img.shields.io/badge/Groq-LLaMA_3.3_70B-F55036?logo=groq)

**A production-deployed AI assistant that answers citizen queries about 37+ Tamil Nadu Government welfare schemes — in English and Tamil — using a fully grounded Hybrid RAG pipeline with zero hallucination tolerance.**

</div>

> 🚀 **Live Interactive Demo:** [https://tn-gov-ai-assistant.vercel.app/](https://tn-gov-ai-assistant.vercel.app/)  
> Query eligibility criteria, monetary subsidies, and official application procedures for Tamil Nadu welfare schemes in English or தமிழ் script with zero installation.

---

## Project Overview

The **Tamil Nadu Government AI Scheme Assistant** is a full-stack, production-deployed RAG (Retrieval-Augmented Generation) system that enables citizens to query Tamil Nadu government welfare schemes in natural language — including Tamil script — and receive accurate, cited, grounded answers.

### What Makes This System Different

| Standard Chatbot | Tamil Nadu Government AI Assistant |
|---|---|
| Generates unverified facts / hallucinations | 100% grounded — answers derived exclusively from official government policy notes and citizen charters |
| No provenance or citations | Every answer cites `[Official Document, Page X, Source URL]` |
| Answers out-of-scope / political questions | Deterministic pre-LLM guardrail refuses out-of-domain queries before token generation |
| Single model dependency | 6-tier LLM fallback chain across Groq infrastructure for uninterrupted uptime |
| English only | Native English and Tamil bilingual retrieval, normalization, and generation |
| Unverified output quality | Verified against 86 automated tests and a 50-query end-to-end evaluation benchmark |

### Covered Schemes (37+ State Welfare Programs)

Social Security · Women Welfare · Higher Education · Health Insurance · MSME & Employment · Disability Assistance · Agriculture — all indexed from official Government of Tamil Nadu gazettes and policy documents.

---

## Live Deployment

| Component | Platform | Status | URL |
|---|---|---|---|
| **Citizen Web Interface** | Vercel (Next.js 16 / React 19) | ✅ Active | [https://tn-gov-ai-assistant.vercel.app/](https://tn-gov-ai-assistant.vercel.app/) |
| **Backend REST API** | FastAPI / Docker Container | ✅ Active | `/api/v1/chat`, `/health`, `/admin/stats` |
| **Vector & BM25 Store** | ChromaDB + rank-bm25 | ✅ Persistent | 37 Scheme Chunks (Verified Seed) · Up to ~1,420 Chunks (Projected Full Ingestion) |
| **Relational Persistence** | PostgreSQL | ✅ Active | Chat Sessions, Message History, Telemetry, and Feedback |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     CITIZEN / USER                                   │
│              (Web Browser — English or Tamil query)                  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTPS
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   Next.js 16 / React 19 Frontend                     │
│                   Vercel Edge Network                                │
│                                                                      │
│   ┌─────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│   │  Chat UI    │  │ Session Mgmt │  │  Confidence Badge        │  │
│   │  (Bilingual)│  │ (UUID state) │  │  (High / Medium / Low)   │  │
│   └─────────────┘  └──────────────┘  └──────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ REST API (JSON)
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    FastAPI Application Backend                        │
│                    Docker Runtime Container                          │
│                                                                      │
│   POST /chat                 GET /chat/{session_id}                  │
│   GET  /health               GET /admin/stats                        │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
          ┌─────────────────┼──────────────────┐
          ▼                 ▼                  ▼
┌─────────────────┐ ┌─────────────────┐ ┌────────────────────────────┐
│  Topic Guard    │ │   Retrieval     │ │   LLM Generation           │
│  (Pre-LLM       │ │   Service       │ │   (Groq Multi-Tier Fallback│
│   Guardrail)    │ │   Hybrid RRF    │ │                            │
│                 │ │                 │ │   llama-3.3-70b-versatile  │
│  OOD Keyword    │ │  BM25 (top-5)   │ │   → llama-3.1-8b-instant   │
│  RRF Threshold  │ │  ChromaDB(top-5)│ │   → openai/gpt-oss-20b     │
│  Scheme Match   │ │  RRF Fusion     │ │   → qwen/qwen3.6-27b       │
│                 │ │                 │ │   → openai/gpt-oss-120b    │
│  → Fast Refusal │ │  → top-4 chunks │ │   → allam-2-7b             │
└─────────────────┘ └────────┬────────┘ └────────────────────────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
┌──────────────────────────┐  ┌──────────────────────────────────────┐
│  ChromaDB (Persistent)   │  │  BM25 Index (rank-bm25)              │
│  37 Chunks (Seed)        │  │  37 Lexical Chunks (Seed)            │
│  sentence-transformers   │  │  Okapi BM25 Term Weighting           │
│  all-MiniLM-L6-v2        │  │  Exact Scheme Acronym Boosting       │
└──────────────────────────┘  └──────────────────────────────────────┘
              │
              ▼
┌──────────────────────────────────────────────────────────────────┐
│                   PostgreSQL Database                              │
│         Sessions · Message History · Citizen Feedback · Telemetry │
└──────────────────────────────────────────────────────────────────┘
```

---

## Technical Engineering Deep-Dive

### Document Ingestion Pipeline

**Modules:** `backend/ingestion/pipeline.py`, `pdf_loader.py`, `cleaner.py`, `chunker.py`, `embedder.py`

The ingestion pipeline is a deterministic, idempotent ETL workflow:

```python
# Incremental ingestion with SHA-256 deduplication
document_hash = _hash_file(pdf_path)
if hashes.get(file_name) == document_hash:
    continue  # Skip re-processing unchanged documents
```

| Ingestion Stage | Technology | Operational Specification |
|---|---|---|
| **PDF Extraction** | PyMuPDF (`fitz`) | Per-page parsing, UTF-8 normalization, document title and page metadata tagging |
| **Text Sanitization** | Python standard library | Unicode NFKC normalization, whitespace collapse, statistical cross-page header/footer strip |
| **Deterministic Chunking** | LangChain TextSplitter | 700 token window, 125 token overlap, SHA-256 chunk hash generation |
| **Embedding Generation** | `sentence-transformers` | `all-MiniLM-L6-v2`, batch size 32, unit L2-normalized vector outputs |
| **Vector Storage** | ChromaDB | Persistent index with cosine distance metric |
| **Lexical Indexing** | `rank-bm25` | Okapi BM25 scoring index over all chunks, persisted to `bm25_index.json` |

---

### Hybrid RAG Retrieval Engine

**Modules:** `backend/app/rag/retrieval_service.py`, `vector_store.py`, `bm25_index.py`, `query_expander.py`

The retrieval system fuses semantic representations with keyword matching using Reciprocal Rank Fusion (RRF):

```
Citizen Query
  │
  ├── Query Expander (Synonym expansion, Tamil transliteration, acronym mapping)
  │
  ├──► BM25 Retrieval (Lexical overlap, top_k = 5, boosted on exact scheme acronyms)
  │
  └──► ChromaDB Retrieval (Semantic similarity, top_k = 5, all-MiniLM-L6-v2)
        │
        ▼
  Reciprocal Rank Fusion
  RRF(d) = Σ 1 / (60 + rank(d))
        │
        ▼
  Context Filter (Top-4 chunks, minimum threshold ≥ 0.015)
```

#### Query Expansion & Transliteration
* Handles 37+ official scheme aliases (e.g., `KMUT`, `CMCHIS`, `PMEGP`, `Pudhumai Penn`).
* Maps Tamil colloquialisms and transliterated queries directly to official scheme entities (e.g., `pudhumai pen` → `புதுமைப் பெண்`).

---

### Pre-LLM Safety Guardrail

**Module:** `backend/app/rag/topic_guard.py`

Before dispatching queries to the LLM, every user input passes through a three-tier validation check to prevent prompt injections, token waste, and off-topic queries:

1. **Out-of-Domain Filter:** Rejects non-welfare topics (sports, weather, coding, international politics).
2. **Retrieval Threshold Filter:** If top RRF score $< 0.015$, the query is refused immediately.
3. **Known Scheme Alignment:** Context must match at least one verified government scheme document.

---

### LLM Generation with Fallback Chain

**Module:** `backend/app/rag/llm_client.py`

To eliminate single-provider downtime, generation uses a 6-tier automated fallback cascade:

```python
FALLBACK_MODELS = [
    "llama-3.3-70b-versatile",   # Primary — high quality reasoning
    "llama-3.1-8b-instant",      # Fast secondary
    "openai/gpt-oss-20b",        # Third-tier fallback
    "qwen/qwen3.6-27b",          # Fourth-tier fallback
    "openai/gpt-oss-120b",       # High-capacity fallback
    "allam-2-7b",                # Final fallback
]
```

---

### Next.js Frontend

**Module:** `frontend/`

Built with Next.js 16 and Tailwind CSS following Government of Tamil Nadu civic design standards:
- **Civic Design Palette:** Deep slate (`#090d16`), emerald green (`#059669`), and gold accent (`#f59e0b`).
- **Bilingual Interface:** Instant toggle between English and தமிழ் prompt templates.
- **Verification Citations:** Direct display of source document name, department, page number, and official URL.
- **Architectural Telemetry:** Modal displaying real-time vector chunk count, active LLM model, and retrieval parameters.

---

## Evaluation & Benchmarks

The retrieval and generation pipeline underwent rigorous automated testing and evaluation.

### Automated Test Suite (86 Tests)

```
pytest backend/tests/ -v
============================= 86 passed in 52.49s =============================
```

| Test Module | Tests | Validation Scope |
|---|---|---|
| `test_topic_guard.py` | 40 | Out-of-domain rejection, scheme matching, boundary cases |
| `test_cleaner.py` | 17 | Unicode normalization, whitespace cleanup, header/footer strip |
| `test_api.py` | 8 | Chat endpoints, session tracking, input sanitization |
| `test_chunker.py` | 8 | Chunk length boundaries, token overlap, hash consistency |
| `test_confidence.py` | 4 | High / Medium / Low confidence calculation logic |
| `test_retrieval.py` | 4 | English, Tamil, acronym matching, and hybrid RRF |
| `test_admin_endpoints.py` | 4 | Diagnostic statistics, versioning, dataset metadata |
| `test_health.py` | 1 | System component health check |

### 50-Query Audit Benchmark

```
python backend/evaluation/benchmark_50_eval.py
─────────────────────────────────────────────────────
Total Benchmark Queries : 50
Passed Evaluation       : 50/50 (100.0%)
Mean Reciprocal Rank    : 0.7600
Precision@5             : 0.8000
Recall@5                : 0.8000
─────────────────────────────────────────────────────
```

> **Note on End-to-End Audit Metrics**: In this end-to-end evaluation, the Precision@5 and Recall@5 figures represent the binary hit rate across all 50 queries, where the 10 out-of-domain queries were correctly refused by the pre-LLM Topic Guard and scored as 0.0 for retrieval chunks. The resulting figures (0.8000 hit rate and 0.7600 MRR) reflect a 100% correct system pass rate (40/40 schemes retrieved + 10/10 out-of-domain queries refused), not retrieval failures.

### Retrieval Benchmark & Ablation Study

Empirical evaluation of the retrieval engine across the 50-query benchmark suite (40 target scheme queries scored, 10 out-of-domain refusal queries excluded). Compares BM25 keyword search, dense vector retrieval (`intfloat/multilingual-e5-large`), and production Hybrid RRF retrieval under identical batched metadata hydration and single-instance latency measurement.

> **Evaluation Scope**: This benchmark was conducted against the seed index of **37 chunks (one chunk per scheme)**. It measures the retrievers' capability to identify the correct scheme among 37 candidates in English and Tamil; these numbers evaluate scheme-level identification and do not claim to describe a larger multi-thousand chunk production index.

```bash
python scripts/eval_retrieval.py
```

| Retrieval Method | Hit@4 (95% CI)¹ | Hit@5 (95% CI) | MRR (95% CI) | Scored Queries Hit | Latency P50² | Latency P95² |
|---|---|---|---|---|---|---|
| **BM25-only** | 0.9250 [0.8250, 1.0000] | 0.9500 [0.8750, 1.0000] | 0.9008 [0.8175, 0.9750] | 38 / 40 (95.0%) | **1.77 ms** | **3.32 ms** |
| **Dense-only (`multilingual-e5-large`)** | **1.0000** [1.0000, 1.0000] | **1.0000** [1.0000, 1.0000] | 0.9563 [0.9062, 1.0000] | **40 / 40 (100.0%)** | 278.18 ms | 440.94 ms |
| **Hybrid (BM25 + Dense RRF)** | **1.0000** [1.0000, 1.0000] | **1.0000** [1.0000, 1.0000] | 0.9521 [0.8958, 1.0000] | **40 / 40 (100.0%)** | 279.79 ms | 439.91 ms |

¹ *Note on Hit@4: Production hybrid retrieval limits its context window to `retrieval_final_context_k = 4` chunks, whereas baseline standalone vector/BM25 queries retrieve 5. Hit@4 provides a normalized context-window comparison.*  
² *Note on Latency: Measured in-process on CPU (`AMD Ryzen 7 7445HS`, 15.27 GB RAM, Windows 11). Dense and Hybrid latency includes single-threaded CPU query embedding via `intfloat/multilingual-e5-large` (`torch.set_num_threads(1)`).*

#### Language Breakdown (English vs. Tamil)

| Retrieval Method | Language Slice | Hit@4 | Hit@5 | MRR | Scored Hits |
|---|---|---|---|---|---|
| **BM25-only** | English (30 queries) | 0.9333 | 0.9667 | 0.9011 | 29 / 30 |
| | Tamil (10 queries) | 0.9000 | 0.9000 | 0.9000 | 9 / 10 |
| **Dense-only** | English (30 queries) | 1.0000 | 1.0000 | 0.9417 | 30 / 30 |
| | Tamil (10 queries) | 1.0000 | 1.0000 | 1.0000 | 10 / 10 |
| **Hybrid (RRF)** | English (30 queries) | 1.0000 | 1.0000 | 0.9361 | 30 / 30 |
| | Tamil (10 queries) | 1.0000 | 1.0000 | 1.0000 | 10 / 10 |

#### Empirical Findings & Analysis
- **Benchmark Saturation**: Both Dense-only and Hybrid achieve a saturated **100% Hit@5 and Hit@4** (40/40), yielding degenerate $[1.0, 1.0]$ bootstrap intervals. Head-to-head across the 40 queries, Hybrid is 1 better (`q34`), 1 worse (`q09`), and 38 identical to Dense-only. The current 40-query seed benchmark is too small and clean to statistically separate Hybrid from Dense-only on MRR.
- **BM25 Throughput & Coverage**: BM25 provides **~158× faster retrieval** (1.77 ms vs. 279.79 ms P50) while achieving 95% Hit@5, missing only colloquial synonyms not present in the title (`q16`) and ONE Tamil query (`q25` - pure Tamil script query mapped to English document text without transliteration).
- **Per-Query Log**: Detailed query-by-query rankings, Hit@4/5 values, and Reciprocal Rank Fusion logs are saved to `reports/retrieval_eval_results.csv`.

---

## Repository Structure

```
TNGov-AI-Assistant/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI router endpoints (/chat, /admin, /feedback)
│   │   ├── core/             # Pydantic environment configuration & settings
│   │   ├── db/               # PostgreSQL engine & session management
│   │   ├── models/           # SQLAlchemy ORM models (Session, Message, Feedback)
│   │   ├── rag/              # Vector store, BM25 index, RRF, LLM client, guardrails
│   │   └── services/         # Generation, retrieval, and persistence logic
│   ├── ingestion/            # PDF parsing, cleaning, chunking, and embedding ETL
│   ├── evaluation/           # Benchmark evaluation scripts (50-query suite)
│   ├── tests/                # 86-test pytest test suite
│   ├── Dockerfile            # Production multi-stage Docker build
│   └── requirements.txt      # Python dependencies
│
├── frontend/
│   ├── app/                  # Next.js App Router (page.tsx, layout.tsx)
│   ├── components/           # UI components, badges, modals, citations
│   ├── public/               # Static assets & government icons
│   └── package.json          # Next.js 16 & React 19 dependencies
│
├── schemes/                  # Official Tamil Nadu Government PDF source documents
├── docs/                     # Technical architecture & API reference documentation
├── CONTRIBUTING.md           # Developer guidelines & contribution setup
├── Makefile                  # Automation commands for build, test, and ingestion
└── LICENSE                   # MIT License
```

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- [Groq API Key](https://console.groq.com)

### 1. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Set GROQ_API_KEY in .env

# Run ingestion pipeline (extracts schemes -> ChromaDB + BM25)
python -m ingestion.cli ingest

# Start FastAPI development server
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup

```bash
cd ../frontend
npm install
npm run dev
# Open http://localhost:3000
```

---

## Environment Variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `GROQ_API_KEY` | Yes | — | Groq API authentication key |
| `DATABASE_URL` | Yes | `postgresql+asyncpg://...` | PostgreSQL async connection string |
| `CHROMA_DB_PATH` | No | `./chroma_db` | Persistent filesystem location for vector store |
| `ALLOWED_ORIGINS` | No | `http://localhost:3000,...` | CORS whitelisted frontend origins |
| `GROQ_MODEL` | No | `llama-3.3-70b-versatile` | Primary generation model |
| `EMBEDDING_MODEL` | No | `all-MiniLM-L6-v2` | Sentence-transformers dense embedding model |
| `CHUNK_SIZE` | No | `700` | Token window size per chunk |
| `CHUNK_OVERLAP` | No | `125` | Overlap between adjacent chunks |
| `RETRIEVAL_FINAL_CONTEXT_K` | No | `4` | Number of context chunks fed to LLM |
| `RRF_K` | No | `60` | Reciprocal Rank Fusion constant |

---

## Security & Credential Hygiene

- **Zero Secret Leakage:** No API keys, database credentials, or private tokens are tracked in git (`.env` is strictly git-ignored).
- **Sanitized Placeholders:** `.env.example` contains only standard documentation templates.
- **Model Isolation:** Prompt sanitization limits input length to 500 characters, preventing prompt injection attacks.
- **Deterministic Topic Guarding:** Refuses out-of-domain queries before invoking downstream LLMs.

---

## Author

**Aakash S. S.**
- **Email:** [aakash1552005@gmail.com](mailto:aakash1552005@gmail.com)
- **LinkedIn:** [linkedin.com/in/aakash-s-s-88b91a301](https://www.linkedin.com/in/aakash-s-s-88b91a301/)
- **Website:** [aakash1552005.github.io](https://aakash1552005.github.io/)

---

<div align="center">

Government of Tamil Nadu Welfare Scheme Intelligence Platform · Powered by Groq LLaMA 3.3 70B & Hybrid RAG

</div>

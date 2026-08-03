# Tamil Nadu Government AI Scheme Assistant
### Multilingual RAG-Powered Welfare Scheme Intelligence Assistant — v1.0.0

[![CI Pipeline](https://github.com/aakash1552005/TNGov-AI-Assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/aakash1552005/TNGov-AI-Assistant/actions/workflows/ci.yml)
![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Embedded-orange.svg)
![Next.js](https://img.shields.io/badge/Next.js-16-black.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

An enterprise-grade, production-ready Retrieval-Augmented Generation (RAG) assistant designed to answer citizen queries regarding **31 Tamil Nadu Government welfare schemes** in English and Tamil with 100% grounded context and explicit PDF page citations.

---

## 🚀 Production Deployment

| Component | Provider | URL |
|-----------|----------|-----|
| **Backend API** | Railway | _(set after deployment)_ |
| **Frontend** | Vercel | _(set after deployment)_ |
| **PostgreSQL** | Railway Plugin | Managed, auto-configured |
| **Vector Store** | Embedded ChromaDB | Persistent volume at `/data/chroma_db` |

**Quick Deploy**: See [DEPLOYMENT.md](DEPLOYMENT.md) for the full step-by-step guide.

---

## 🏛️ System Architecture

### Application Architecture

```text
               ┌─────────────────────────────────────────┐
               │     Next.js 16 / React 19 Frontend       │
               │     (Vercel — global CDN)                │
               └────────────────────┬────────────────────┘
                                    │ HTTPS REST
                                    ▼
               ┌─────────────────────────────────────────┐
               │    FastAPI Application (app/main.py)    │
               │    (Railway — Docker container)         │
               └────────────────────┬────────────────────┘
                                    │
           ┌────────────────────────┴────────────────────────┐
           ▼                                                 ▼
┌──────────────────────┐                         ┌──────────────────────┐
│  /chat  /feedback    │                         │  GET /health         │
└──────────┬───────────┘                         └──────────────────────┘
           │
           ▼
┌───────────────────────────────────────────────────────────────────────┐
│ Generation Service (app/services/generation_service.py)               │
└──────────┬────────────────────────────────────────────────────────────┘
           │
 ┌─────────┴──────────────────────────────┐
 ▼                                        ▼
┌───────────────────────────────────┐  ┌────────────────────────────────┐
│ Retrieval Service (Hybrid RRF)    │  │ LLM Client Abstraction         │
│ (app/rag/retrieval_service.py)    │  │ Groq / OpenAI / Gemini         │
└──────────┬────────────────────────┘  └────────────────────────────────┘
           │
 ┌─────────┴──────────────────────────────┐
 ▼                                        ▼
┌───────────────────────────────────┐  ┌────────────────────────────────┐
│ ChromaDB (Embedded Persistent)    │  │ BM25 Index (rank-bm25)         │
│ /data/chroma_db (Railway volume)  │  │ /data/bm25_index.json          │
└───────────────────────────────────┘  └────────────────────────────────┘
```

### Deployment Architecture

```text
GitHub (main branch)
    │
    ├── CI Pipeline (ci.yml) ─── Tests + Linting + Evaluation
    │
    └── CD Pipeline (deploy.yml)
            │
            ├── Railway (Backend Docker Container)
            │       │
            │       ├── entrypoint.sh validates ChromaDB (fail-fast)
            │       ├── uvicorn app.main:app --host 0.0.0.0 --port $PORT
            │       ├── Railway PostgreSQL (managed, auto-URL)
            │       └── Railway Persistent Volume → /data/chroma_db
            │
            └── Vercel (Frontend Next.js)
                    │
                    └── NEXT_PUBLIC_API_URL → Railway backend
```

---

## ✨ Key Features

- **Hybrid RAG Engine**: Combines dense vector similarity (`intfloat/multilingual-e5-large` in ChromaDB) and sparse keyword matching (BM25) fused via Reciprocal Rank Fusion ($RRF(d) = \sum \frac{1}{60 + r(d)}$).
- **100% Grounded & Cited Answers**: Answers cite official source PDF documents in `[PDF Name, Page X]` format.
- **Out-of-Scope Refusal Guardrails**: Automatic refusal (`llm_called = False`) when no retrieved context meets `retrieval_min_score`.
- **Multi-Provider LLM Abstraction**: Dynamic provider switching between Groq (`llama-3.3-70b-versatile`), OpenAI (`gpt-4o-mini`), and Gemini (`gemini-2.0-flash`).
- **Multilingual Query Support**: Seamless retrieval and generation across English and Tamil queries.
- **Production Validation Gate**: `entrypoint.sh` performs 3-check fail-fast validation of ChromaDB before starting the server — prevents silent data loss on misconfigured deployments.
- **Evaluation & Quality Suite**: Full benchmarking pipeline measuring Hit@K, MRR, latency percentiles, and RAGAS quality metrics.

---

## ⚡ Quickstart

### 1. Clone & Configure

```bash
git clone https://github.com/aakash1552005/TNGov-AI-Assistant.git
cd TNGov-AI-Assistant

cp backend/.env.example backend/.env
# Edit backend/.env — set GROQ_API_KEY (or OPENAI_API_KEY / GEMINI_API_KEY)
```

### 2. Local Docker (Recommended)

```bash
# Build and start backend + PostgreSQL
docker compose up -d --build

# One-time ChromaDB initialization (first run only)
docker compose exec backend python -m ingestion.cli ingest

# Verify
curl http://localhost:8000/health
```

### 3. Local Development (Without Docker)

```bash
cd backend
pip install -r requirements.txt
python -m ingestion.cli ingest
uvicorn app.main:app --reload --port 8000
```

### 4. Cloud Deployment

See **[DEPLOYMENT.md](DEPLOYMENT.md)** for the complete Railway + Vercel deployment guide.

---

## 🗄️ ChromaDB Persistence

ChromaDB is used as an **embedded persistent vector store** — not an external service. This is the correct architectural choice for this project:

| Factor | Detail |
|--------|--------|
| Corpus size | 31 chunks — no distributed storage needed |
| Write pattern | Write-once during initialization, read-many at runtime |
| Latency | Sub-millisecond (no network) vs. 10–50ms for external APIs |
| Cost | Zero (embedded) vs. $70–$100+/month for managed vector DBs |
| Operational burden | None — no API keys, SLAs, or external dependencies |

**In production (Railway)**, ChromaDB data is stored on a Railway persistent volume at `/data/chroma_db`. This volume survives all container restarts and redeployments.

**Startup validation**: Every container start runs `entrypoint.sh`, which validates ChromaDB contains exactly 31 chunks before starting the server. If validation fails, the container exits with a detailed diagnostic message — it does **not** silently serve empty results.

---

## 🧪 Testing & Evaluation

### Run Unit Tests

```bash
cd backend
python -m pytest tests/ -v
```

### Run Evaluation Suite

```bash
cd backend
python -m evaluation.cli all
```

---

## 📊 Quality Benchmarks

| Metric | Score | Description |
| :--- | :--- | :--- |
| **Unit Test Pass Rate** | **100.0%** (46/46) | Automated test suite |
| **Hit@1 Precision** | **93.8%** | Ground-truth doc at rank #1 |
| **Hit@3 Recall** | **100.0%** | Ground-truth doc in top-3 |
| **MRR** | **0.9583** | Mean Reciprocal Rank |
| **Retrieval Latency P50** | **275 ms** | Local CPU search latency |
| **E2E Response P50** | **1.007 s** | Complete pipeline duration |

---

## 🔧 Environment Variables

| Variable | Where Set | Description |
|----------|-----------|-------------|
| `GROQ_API_KEY` | Backend `.env` / Railway | LLM API key |
| `DATABASE_URL` | Auto-injected by Railway | PostgreSQL connection |
| `CHROMA_DB_PATH` | Railway variable | `/data/chroma_db` in production |
| `ALLOWED_ORIGINS` | Railway variable | Frontend URL for CORS |
| `NEXT_PUBLIC_API_URL` | Vercel variable | Backend URL |

Full reference: [DEPLOYMENT.md § Environment Variables](DEPLOYMENT.md#3-environment-variables-reference)

---

## 📄 Documentation

- [Deployment Guide](DEPLOYMENT.md) — Railway + Vercel production deployment.
- [Evaluation Framework](backend/evaluation/README.md) — Methodology and benchmark details.
- [Developer Guide](CONTRIBUTING.md) — Code style, testing, and contribution steps.
- [Release Notes](RELEASE_NOTES.md) — v1.0.0 capabilities and deployment.

---

## 🛡️ License

Distributed under the MIT License. See `LICENSE` for more information.
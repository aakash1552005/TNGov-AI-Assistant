# Tamil Nadu Government AI Scheme Assistant
### Multilingual RAG-Powered Welfare Scheme Intelligence Assistant

[![CI Pipeline](https://github.com/aakash1552005/TNGov-AI-Assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/aakash1552005/TNGov-AI-Assistant/actions/workflows/ci.yml)
![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)
![ChromaDB](https://img.shields.io/badge/ChromaDB-0.5-orange.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

An enterprise-grade, production-ready Retrieval-Augmented Generation (RAG) assistant designed to answer citizen queries regarding 31 Tamil Nadu Government welfare schemes in English and Tamil with $100\%$ grounded context and explicit PDF page citations.

---

## 🏛️ System Architecture

```text
               ┌─────────────────────────────────────────┐
               │     Next.js / React Web Frontend        │
               └────────────────────┬────────────────────┘
                                    │ HTTP / REST APIs
                                    ▼
               ┌─────────────────────────────────────────┐
               │    FastAPI Application (app/main.py)    │
               └────────────────────┬────────────────────┘
                                    │
           ┌────────────────────────┴────────────────────────┐
           ▼                                                 ▼
┌──────────────────────┐                         ┌──────────────────────┐
│  API Routers (/chat) │                         │ Health Endpoint      │
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
│ Retrieval Service                 │  │ LLM Client Abstraction         │
│ (app/rag/retrieval_service.py)    │  │ (app/rag/llm_client.py)        │
└──────────┬────────────────────────┘  └────────────────────────────────┘
           │
 ┌─────────┴──────────────────────────────┐
 ▼                                        ▼
┌───────────────────────────────────┐  ┌────────────────────────────────┐
│ Dense Vector Store (ChromaDB)     │  │ Sparse Keyword Search (BM25)   │
└───────────────────────────────────┘  └────────────────────────────────┘
```

---

## ✨ Key Features

- **Hybrid RAG Engine**: Combines dense vector similarity (`intfloat/multilingual-e5-large` in ChromaDB) and sparse keyword matching (BM25) fused via Reciprocal Rank Fusion ($RRF(d) = \sum \frac{1}{60 + r(d)}$).
- **$100\%$ Grounded & Cited Answers**: Answers cite official source PDF documents in `[PDF Name, Page X]` format.
- **Out-of-Scope Refusal Guardrails**: Automatic refusal (`llm_called = False`) when no retrieved context meets `retrieval_min_score` ($0.15$).
- **Multi-Provider LLM Abstraction**: Dynamic provider switching between Groq (`llama-3.3-70b-versatile`), OpenAI (`gpt-4o-mini`), and Gemini (`gemini-2.0-flash`).
- **Multilingual Query Support**: Seamless retrieval and generation across English and Tamil queries.
- **Evaluation & Quality Suite**: Full benchmarking pipeline measuring Hit@K, MRR, latency percentiles, and RAGAS quality metrics.
- **Production DevOps Packaging**: Docker Compose, GitHub Actions CI workflow, health check endpoints, and environment templates.

---

## ⚡ Quickstart & Setup

### 1. Prerequisites
- Python 3.12+
- Docker & Docker Compose (optional for containerized deployment)

### 2. Environment Setup
```bash
cd backend
cp .env.example .env
```
Edit `.env` to supply your `GROQ_API_KEY`, `OPENAI_API_KEY`, or `GEMINI_API_KEY`.

### 3. Local Development Run
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 4. Docker Deployment
```bash
docker compose up -d --build
```

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

## 📊 Key Verification & Quality Benchmarks

| Metric | Benchmark Score | Description |
| :--- | :--- | :--- |
| **Unit Test Pass Rate** | **100.0%** (46/46) | Automated test suite coverage across API, retrieval, chunker, cleaner |
| **Hit@1 Precision** | **93.8%** | In-scope queries ranking ground-truth document at position #1 |
| **Hit@3 Recall** | **100.0%** | In-scope queries retrieving ground-truth document in top-3 ranks |
| **MRR** | **0.9583** | Mean Reciprocal Rank across hybrid retrieval queries |
| **In-Scope Retrieval Latency** | **275.0 ms** | Average local CPU search latency |
| **E2E Response Latency P50** | **1.007 s** | Median complete citizen query response pipeline duration |

---

## 📄 Documentation

- [Deployment Guide](DEPLOYMENT.md) — Production Docker and systemd deployment.
- [Evaluation Framework](backend/evaluation/README.md) — Methodology and benchmark details.
- [Developer Guide](CONTRIBUTING.md) — Code style, testing, and contribution steps.
- [Release Notes](RELEASE_NOTES.md) — Version 1.0.0 capabilities.

---

## 🛡️ License

Distributed under the MIT License. See `LICENSE` for more information.
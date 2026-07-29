# Tamil Nadu Government AI Scheme Assistant

[![Docker Compose](https://img.shields.io/badge/Docker%20Compose-v2-blue?logo=docker)](https://docs.docker.com/compose/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-16.2-black?logo=nextdotjs)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql)](https://www.postgresql.org/)
[![Groq](https://img.shields.io/badge/Groq-Llama--3.3--70b-orange)](https://groq.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A production-grade, grounded multilingual (English + Tamil) Retrieval-Augmented Generation (RAG) system for citizens seeking official Tamil Nadu welfare scheme information. Built with **FastAPI**, **Next.js 16**, **PostgreSQL 16**, **ChromaDB**, **BM25 Inverted Index**, and **Groq Llama-3.3-70b**.

> ⚠️ **Disclaimer**: This is an AI assistant and not an official government source. Please verify all information with the concerned department before taking action.

---

## Key Features

- **Multilingual Scheme Intelligence**: Query official welfare documents in English or Tamil.
- **Hybrid Retrieval Engine**: Combines dense vector search (`multilingual-e5-large`) and sparse keyword search (BM25) fused via **Reciprocal Rank Fusion (RRF)** ($k=60$).
- **Strict Grounding & Scope Guard**: Score thresholds prevent hallucinations. Out-of-scope queries (e.g. general trivia) return an immediate refusal with 0 citations.
- **Document & Page-Level Citations**: Every answer provides verified PDF document names, page numbers, excerpts, and live official portal links.
- **Asynchronous Session Persistence**: PostgreSQL 16 persists conversation history (`chat_sessions`, `chat_messages`) and citizen feedback ratings (`feedback`).
- **Database Outage Resilience**: Non-blocking database fallbacks ensure RAG answer delivery even if PostgreSQL becomes temporarily unavailable.
- **Browser LocalStorage Auto-Restoration**: Reloading the browser restores previous conversation history automatically.

---

## Architecture Overview

```mermaid
graph TD
    Citizen([Citizen / Browser]) <-->|HTTP REST / JSON| Frontend[Next.js 16 UI]
    Frontend <-->|API Requests| FastAPI[FastAPI REST Layer]

    subgraph Backend Core
        FastAPI -->|Generation Request| GenService[GenerationService]
        FastAPI -->|Persistence Request| PersistService[PersistenceService]

        GenService -->|Hybrid Query| RetService[RetrievalService]
        GenService -->|Grounded Prompt| LLM[Groq Llama-3.3-70b]

        RetService -->|Vector Search| Chroma[ChromaDB / E5-Large Embeddings]
        RetService -->|Keyword Search| BM25[BM25 Index]
        RetService -->|Rank Fusion| RRF[Reciprocal Rank Fusion - RRF]

        PersistService <-->|Async Engine| Postgres[(PostgreSQL 16)]
    end
```

Detailed technical documentation is available in [`docs/`](./docs/):
- [Architecture & Sequence Diagrams](./docs/architecture.md)
- [REST API Reference](./docs/api.md)
- [Database Schema & ER Diagram](./docs/database.md)
- [Hybrid Retrieval & RRF Pipeline](./docs/retrieval.md)
- [Deployment Guide](./docs/deployment.md)
- [Test Suite Guide](./docs/testing.md)
- [Codebase Structure](./docs/project_structure.md)

---

## Technology Stack

| Layer | Technology | Description |
| :--- | :--- | :--- |
| **Frontend** | Next.js 16 (App Router), TypeScript, Vanilla CSS | Dark mode glassmorphism UI with responsive animations |
| **Backend** | FastAPI, Python 3.12, Pydantic v2 | Async REST API service |
| **Relational Database** | PostgreSQL 16, SQLAlchemy 2.0, asyncpg | Session persistence, message history, feedback |
| **Vector Store** | ChromaDB (`hnsw:space: cosine`) | Persistent vector database (`./chroma_db`) |
| **Embeddings** | `intfloat/multilingual-e5-large` | 1024-dimensional dense semantic vectors |
| **Sparse Keyword Search**| BM25 Inverted Index | Custom tokenization over raw PDF chunks |
| **Rank Fusion** | Reciprocal Rank Fusion (RRF) | Merges vector & BM25 candidate ranks ($k=60$) |
| **LLM Provider** | Groq (`llama-3.3-70b-versatile`) | Fast, grounded LLM generation at `temperature=0` |
| **Orchestration** | Docker & Docker Compose v2 | Multi-container production deployment |

---

## Quick Start

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) & Docker Compose v2
- [Git](https://git-scm.com/)

### 1. Clone & Configure Environment
```bash
git clone https://github.com/aakash1552005/TNGov-AI-Assistant.git
cd TNGov-AI-Assistant

cp .env.example .env
# Edit .env and set your GROQ_API_KEY
```

### 2. Launch Stack via Docker Compose
```bash
docker compose up -d --build
```

### 3. Verify Container Health
```bash
# Check service health
docker compose ps

# Access health endpoint
curl http://localhost:8000/health
```

### 4. Access Web Interface
Open `http://localhost:3000` in your web browser.

---

## Environment Variables Configuration

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `APP_NAME` | `"TN Gov AI Scheme Assistant"` | Application identifier |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@postgres:5432/tngov_db` | PostgreSQL connection string |
| `LLM_PROVIDER` | `groq` | Active LLM provider (`groq`, `gemini`, `openai`) |
| `GROQ_API_KEY` | `""` | API key for Groq Cloud |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Active Groq model |
| `EMBEDDING_MODEL` | `intfloat/multilingual-e5-large` | Dense embedding model |
| `MAX_QUERY_LENGTH` | `500` | Maximum character length for user questions |

---

## Running Automated Tests

Run the full backend unit & integration test suite (46 tests):

```bash
docker compose exec backend pytest tests/ -v
```

---

## API Summary

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Component health check, active provider & model metadata |
| `POST` | `/chat` | Submit question, execute RAG retrieval & LLM generation |
| `GET` | `/chat/{session_id}` | Retrieve historical messages for a session |
| `POST` | `/feedback` | Submit thumbs up/down rating & comment |

Detailed API payloads and JSON response contracts can be found in [`docs/api.md`](./docs/api.md).

---

## Future Roadmap

- **Milestone 6**: RAGAS evaluation pipeline, retrieval benchmarking, latency profiling, and quality metrics tracking.
- **Milestone 7**: Streaming response delivery via Server-Sent Events (SSE).
- **Milestone 8**: Advanced reranking model integration (Cohere / BGE-Reranker).

---

## License

Distributed under the MIT License. See [`LICENSE`](./LICENSE) for details.
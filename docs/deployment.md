# Deployment & Production Setup Documentation

## Overview

The application is containerized using Docker and orchestrated via Docker Compose.

---

## Service Architecture

| Container Name | Service | Base Image / Build | Port Mapping | Healthcheck |
| :--- | :--- | :--- | :--- | :--- |
| `tngov-backend` | FastAPI Backend | Python 3.12 Slim (`backend/Dockerfile`) | `8000:8000` | HTTP `GET /health` |
| `tngov-frontend` | Next.js Chat UI | Node.js 20 Alpine (`frontend/Dockerfile`) | `3000:3000` | HTTP `GET /` |
| `tngov-postgres` | Relational DB | `postgres:16-alpine` | `5432:5432` | `pg_isready` |

---

## Environment Variables

### Backend Configuration (`backend/.env` or root `.env`)

```ini
# Application Configuration
APP_NAME="TN Gov AI Scheme Assistant"
DEBUG=false
MAX_QUERY_LENGTH=500

# Database Settings
DATABASE_URL="postgresql+asyncpg://postgres:postgres@postgres:5432/tngov_db"

# LLM Settings
LLM_PROVIDER="groq"
GROQ_API_KEY="gsk_..."
GROQ_MODEL="llama-3.3-70b-versatile"

# Embedding Settings
EMBEDDING_MODEL="intfloat/multilingual-e5-large"
CHROMA_PERSIST_DIRECTORY="./chroma_db"
BM25_INDEX_PATH="./chroma_db/bm25_index.json"

# Retrieval Settings
RETRIEVAL_TOP_K=4
RETRIEVAL_MIN_SCORE=0.015
RETRIEVAL_MAX_VECTOR_DISTANCE=0.85
RETRIEVAL_MIN_BM25_SCORE=1.0
```

---

## Deployment Commands

### 1. Build and Launch Production Stack
```bash
docker compose up -d --build
```

### 2. Verify Container Health
```bash
docker compose ps
```

### 3. Check Backend Logs
```bash
docker compose logs backend -f
```

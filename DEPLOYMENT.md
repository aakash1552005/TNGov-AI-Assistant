# Production Deployment Guide
## Tamil Nadu Government AI Scheme Assistant — v1.0.0

This guide covers both **cloud deployment** (Railway + Vercel) and **local Docker deployment**. Read the relevant section for your use case.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Prerequisites](#2-prerequisites)
3. [Environment Variables Reference](#3-environment-variables-reference)
4. [Local Docker Deployment (Development)](#4-local-docker-deployment)
5. [Cloud Deployment — Backend (Railway)](#5-cloud-deployment--backend-railway)
6. [Cloud Deployment — Frontend (Vercel)](#6-cloud-deployment--frontend-vercel)
7. [ChromaDB Persistence Architecture](#7-chromadb-persistence-architecture)
8. [Database Configuration (PostgreSQL)](#8-database-configuration-postgresql)
9. [GitHub Actions CD Pipeline](#9-github-actions-cd-pipeline)
10. [Health Verification & Smoke Testing](#10-health-verification--smoke-testing)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. Architecture Overview

```text
Internet
    │
    ├── HTTPS ──→ Vercel (Next.js Frontend)
    │                    │
    │              NEXT_PUBLIC_API_URL
    │                    │
    └── HTTPS ──→ Railway (FastAPI Backend)
                         │
               ┌─────────┴──────────┐
               │                    │
        Railway PostgreSQL    Railway Persistent
          (conversations,       Volume /data/
           feedback)             chroma_db/
                                 bm25_index.json
```

### Deployment Stack

| Component | Provider | Notes |
|-----------|----------|-------|
| Backend API | Railway (Docker) | FastAPI + Uvicorn |
| PostgreSQL | Railway Plugin | Managed, auto-SSL |
| Vector Store | Embedded ChromaDB | Persistent volume at `/data/chroma_db` |
| BM25 Index | File-based | Persistent volume at `/data/bm25_index.json` |
| Frontend | Vercel | Next.js 16, zero-config deploy |

---

## 2. Prerequisites

### Accounts Required
- **Railway** account — [railway.app](https://railway.app) (free trial, $5/month Hobby plan for persistent volumes)
- **Vercel** account — [vercel.com](https://vercel.com) (free tier sufficient)
- **GitHub** repository with this codebase pushed

### Tools Required
- Docker Engine 24.0+
- Docker Compose v2.20+
- Railway CLI: `npm install -g @railway/cli`
- Vercel CLI: `npm install -g vercel`

### API Keys Required
- `GROQ_API_KEY` (recommended) — [console.groq.com](https://console.groq.com)
- OR `OPENAI_API_KEY` / `GEMINI_API_KEY` (alternatives)

---

## 3. Environment Variables Reference

### Backend (Railway Service Variables)

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `DATABASE_URL` | ✅ | PostgreSQL connection string (auto-injected by Railway plugin) | `postgresql+asyncpg://user:pass@host:5432/db` |
| `GROQ_API_KEY` | ✅ | Groq API key for LLM inference | `gsk_...` |
| `LLM_PROVIDER` | ✅ | LLM provider selection | `groq` |
| `ALLOWED_ORIGINS` | ✅ | Comma-separated CORS origins | `https://tngov-ai.vercel.app` |
| `CHROMA_DB_PATH` | ✅ | ChromaDB persistent volume path | `/data/chroma_db` |
| `BM25_INDEX_PATH` | ✅ | BM25 index file path | `/data/bm25_index.json` |
| `DATA_DIR` | ✅ | Data directory path | `/data` |
| `APP_ENV` | ✅ | Deployment environment | `production` |
| `EMBEDDING_MODEL` | ✅ | HuggingFace embedding model name | `intfloat/multilingual-e5-large` |
| `GROQ_MODEL` | ❌ | Groq model name | `llama-3.3-70b-versatile` |

### Frontend (Vercel Environment Variables)

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | ✅ | Deployed backend URL | `https://tngov-backend.up.railway.app` |

> **Security note**: No secrets are committed to git. All variables are set through platform dashboards (Railway, Vercel) or GitHub Secrets.

---

## 4. Local Docker Deployment

The local deployment uses Docker Compose and is unchanged from previous milestones.

### Start Local Stack

```bash
# Clone the repository
git clone https://github.com/aakash1552005/TNGov-AI-Assistant.git
cd TNGov-AI-Assistant

# Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env — set GROQ_API_KEY (or other LLM provider key)

# Build and start all services
docker compose up -d --build

# Run one-time ChromaDB initialization (first time only)
docker compose exec backend python -m ingestion.cli ingest

# Verify health
curl http://localhost:8000/health
```

### Verify Local Stack

```bash
docker compose ps
# Expected output:
# tngov-backend   Up (healthy)   0.0.0.0:8000->8000/tcp
# tngov-db        Up (healthy)   0.0.0.0:5432->5432/tcp

curl http://localhost:8000/health
# Expected: {"status":"healthy","chroma_db_loaded":true,"bm25_index_loaded":true,...}
```

---

## 5. Cloud Deployment — Backend (Railway)

### Step 5.1 — Create Railway Project

```bash
# Login to Railway
railway login

# Initialize project from repository root
railway init
# → Select "Create new project"
# → Name: tngov-ai-backend (or your choice)
```

### Step 5.2 — Add PostgreSQL Plugin

In the Railway dashboard:
1. Open your project
2. Click **+ New** → **Database** → **PostgreSQL**
3. Railway automatically injects `DATABASE_URL` into your service

### Step 5.3 — Attach Persistent Volume

In the Railway dashboard:
1. Open your backend service
2. Go to **Volumes** → **+ Add Volume**
3. Mount path: `/data`
4. Size: 2 GB (sufficient for ChromaDB + BM25 + source PDFs)

> **Why `/data`?** The `entrypoint.sh` and `init_vectorstore.py` both expect ChromaDB at `$CHROMA_DB_PATH` (defaulting to `/data/chroma_db`). The persistent volume at `/data` survives all container restarts and redeployments.

### Step 5.4 — Configure Environment Variables

In Railway → Service → **Variables**, set:

```
APP_ENV=production
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your_actual_key_here
GROQ_MODEL=llama-3.3-70b-versatile
EMBEDDING_MODEL=intfloat/multilingual-e5-large
CHROMA_DB_PATH=/data/chroma_db
CHROMA_COLLECTION_NAME=tn_gov_schemes
BM25_INDEX_PATH=/data/bm25_index.json
DATA_DIR=/data
ALLOWED_ORIGINS=https://your-frontend.vercel.app
FRONTEND_URL=https://your-frontend.vercel.app
```

> **Note**: `DATABASE_URL` is auto-injected by the PostgreSQL plugin. Do not set it manually.

### Step 5.5 — Initial Deployment

```bash
# Deploy from project root
railway up --service tngov-backend
```

Watch build logs in the Railway dashboard. Expected sequence:
1. Docker image builds (5–10 minutes first time, embedding model download)
2. Container starts → `entrypoint.sh` runs
3. **entrypoint.sh will FAIL** on first deploy — ChromaDB is empty. This is expected.

### Step 5.6 — One-Time ChromaDB Initialization

> [!IMPORTANT]
> Run this command **once** after first deploy while the persistent volume is attached:

```bash
# Run ingestion against the live Railway container
railway run python -m ingestion.cli ingest --data-dir /data

# Verify chunk count
railway run python -c "
import chromadb
c = chromadb.PersistentClient('/data/chroma_db')
col = c.get_collection('tn_gov_schemes')
print(f'Chunk count: {col.count()}')
"
# Expected output: Chunk count: 31
```

### Step 5.7 — Redeploy After Initialization

```bash
railway up --service tngov-backend
```

Now `entrypoint.sh` will find 31 chunks, pass all 3 checks, and start uvicorn.

### Step 5.8 — Verify Backend

```bash
# Replace with your Railway service URL
BACKEND_URL="https://tngov-backend.up.railway.app"

curl "${BACKEND_URL}/health"
```

Expected response:
```json
{
  "status": "healthy",
  "app": "TN Gov AI Scheme Assistant",
  "version": "1.0.0",
  "chroma_db_loaded": true,
  "bm25_index_loaded": true,
  "llm_provider": "groq",
  "llm_model": "llama-3.3-70b-versatile",
  "embedding_model": "intfloat/multilingual-e5-large"
}
```

**Do NOT proceed to frontend deployment until this check passes.**

---

## 6. Cloud Deployment — Frontend (Vercel)

> **Prerequisite**: Backend deployment must be verified and `/health` must return `chroma_db_loaded: true` before this step.

### Option A — Vercel Dashboard (Recommended)

1. Go to [vercel.com/new](https://vercel.com/new)
2. Import your GitHub repository
3. Configure:
   - **Framework Preset**: Next.js (auto-detected)
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build` (default)
   - **Output Directory**: `.next` (default)
4. Add environment variable:
   - `NEXT_PUBLIC_API_URL` = `https://tngov-backend.up.railway.app`
5. Click **Deploy**

### Option B — Vercel CLI

```bash
cd frontend
vercel login
vercel --prod \
  -e NEXT_PUBLIC_API_URL=https://tngov-backend.up.railway.app
```

### Step 6.2 — Update Backend CORS

After frontend deployment, update `ALLOWED_ORIGINS` in Railway:

```
ALLOWED_ORIGINS=https://tngov-ai.vercel.app,https://www.tngov-ai.vercel.app
```

Redeploy the backend for CORS to take effect.

---

## 7. ChromaDB Persistence Architecture

### Why Embedded ChromaDB Is the Correct Choice

| Factor | This Project | Justification |
|--------|-------------|---------------|
| Corpus size | 31 chunks | No distributed storage needed |
| Write pattern | Write-once, read-many | Zero concurrent write conflicts |
| Network calls | None | Faster than any external service |
| Operational overhead | Zero | No API keys, billing, or external dependencies |
| Cost | Free | Embedded = no SaaS fees |

Migrating to Pinecone, Qdrant, or Weaviate would introduce cost, complexity, and network latency with no benefit at this scale.

### Startup Validation (Fail-Fast Model)

```
──── ONE-TIME INITIALIZATION (explicit, run once) ────────────────────
$ railway run python -m ingestion.cli ingest
   └→ Seeds /data/chroma_db with exactly 31 chunks

──── EVERY CONTAINER STARTUP (entrypoint.sh) ─────────────────────────
Check 1: /data/chroma_db directory exists and is accessible
Check 2: 'tn_gov_schemes' collection exists in ChromaDB
Check 3: collection.count() == 31

ALL PASS → Start uvicorn (application serves traffic)
ANY FAIL → Exit 1 with diagnostic message (do NOT start uvicorn)
```

**Why fail-fast?** A container that silently starts with an empty ChromaDB would serve incorrect "I cannot find information" responses to every citizen query without any error signal. Failing hard surfaces the issue immediately in deployment logs.

### Volume Survival Across Redeploys

Railway persistent volumes are **decoupled from container lifecycle**. When a new Docker image is deployed:
1. The old container stops
2. The new container starts with the same volume mounted at `/data`
3. `entrypoint.sh` finds 31 chunks → passes validation → starts normally

No re-ingestion is needed on redeploy unless the corpus changes.

---

## 8. Database Configuration (PostgreSQL)

### Railway PostgreSQL Plugin

Railway's managed PostgreSQL:
- Auto-creates `DATABASE_URL` in `postgresql+asyncpg://...` format
- Enables SSL by default
- Persists independently of backend service lifecycle
- No manual configuration required

### SSL Configuration

Railway PostgreSQL requires SSL. The `asyncpg` driver used by SQLAlchemy handles SSL automatically when `DATABASE_URL` contains `sslmode=require` or when connecting to a Railway-provided URL.

If you encounter SSL errors, append `?ssl=require` to the connection string:
```
postgresql+asyncpg://user:pass@host:5432/db?ssl=require
```

### Table Creation

Tables are created automatically on startup via `Base.metadata.create_all()` in `app/main.py`. No manual migration step is needed for initial deployment.

---

## 9. GitHub Actions CD Pipeline

The `.github/workflows/deploy.yml` workflow automates deployment on push to `main`.

### Required GitHub Secrets

Configure these in: **GitHub → Repository → Settings → Secrets and variables → Actions**

| Secret | Description |
|--------|-------------|
| `RAILWAY_TOKEN` | Railway API token (Railway → Account → Tokens) |
| `BACKEND_URL` | Deployed Railway backend URL |
| `VERCEL_TOKEN` | Vercel API token (Vercel → Account → Settings → Tokens) |
| `VERCEL_ORG_ID` | Vercel organization ID |
| `VERCEL_PROJECT_ID` | Vercel project ID |
| `FRONTEND_URL` | Deployed Vercel frontend URL |

### Manual Deploy Trigger

```bash
# Trigger from GitHub Actions tab → "Deploy to Production" → "Run workflow"
# Or via gh CLI:
gh workflow run deploy.yml --field deploy_target=backend
```

---

## 10. Health Verification & Smoke Testing

### Backend Endpoints

```bash
BACKEND_URL="https://your-service.up.railway.app"

# Health check
curl "${BACKEND_URL}/health"

# Chat endpoint — real question
curl -X POST "${BACKEND_URL}/chat" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the Chief Ministers Comprehensive Health Insurance Scheme?"}'

# Conversation history
SESSION_ID="<uuid from /chat response>"
curl "${BACKEND_URL}/chat/${SESSION_ID}"

# Feedback submission
MESSAGE_ID="<message_id from /chat response>"
curl -X POST "${BACKEND_URL}/feedback/${MESSAGE_ID}" \
  -H "Content-Type: application/json" \
  -d '{"rating": "up", "comment": "Very helpful"}'
```

### Expected /health Response

```json
{
  "status": "healthy",
  "app": "TN Gov AI Scheme Assistant",
  "version": "1.0.0",
  "chroma_db_loaded": true,
  "bm25_index_loaded": true,
  "llm_provider": "groq",
  "llm_model": "llama-3.3-70b-versatile",
  "embedding_model": "intfloat/multilingual-e5-large"
}
```

---

## 11. Troubleshooting

### `entrypoint.sh` exits 1 — ChromaDB path not found

**Cause**: Persistent volume not attached or wrong mount path.

**Fix**:
1. Verify Railway volume is attached and mounted at `/data`
2. Check `CHROMA_DB_PATH=/data/chroma_db` is set in Railway variables
3. Run one-time initialization: `railway run python -m ingestion.cli ingest`

---

### `entrypoint.sh` exits 1 — Collection not found

**Cause**: Volume is mounted but ingestion has not been run.

**Fix**:
```bash
railway run python -m ingestion.cli ingest --data-dir /data
```

---

### `entrypoint.sh` exits 1 — Chunk count mismatch

**Cause**: Partial ingestion or corpus change.

**Fix**:
```bash
# Clear and re-ingest
railway run python -m ingestion.cli clear
railway run python -m ingestion.cli ingest --data-dir /data
```

---

### CORS errors in browser

**Cause**: `ALLOWED_ORIGINS` does not include the frontend URL.

**Fix**: Update `ALLOWED_ORIGINS` in Railway variables to include your Vercel URL:
```
ALLOWED_ORIGINS=https://tngov-ai.vercel.app,https://www.tngov-ai.vercel.app
```
Then redeploy.

---

### `DATABASE_URL` not found / PostgreSQL connection error

**Cause**: Railway PostgreSQL plugin not attached, or service not linked.

**Fix**:
1. In Railway dashboard → project → click **+ New** → **Database** → **PostgreSQL**
2. Link it to your backend service
3. `DATABASE_URL` will be auto-injected

---

### Frontend shows "Failed to connect to server"

**Cause**: `NEXT_PUBLIC_API_URL` not set or pointing to wrong URL.

**Fix**:
1. In Vercel → Project → Settings → Environment Variables
2. Set `NEXT_PUBLIC_API_URL` = your Railway backend URL (with `https://`)
3. Redeploy the frontend

---

### Railway build times out (embedding model download)

**Cause**: HuggingFace `intfloat/multilingual-e5-large` (~550MB) downloads on first build.

**Fix**: The model is cached after first build. Subsequent builds reuse the cache. Set a longer build timeout in Railway if needed (default is 10 minutes).

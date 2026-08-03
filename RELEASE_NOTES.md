# Release Notes — v1.0.0
## Tamil Nadu Government AI Scheme Assistant
**Release Date**: August 2026

---

## 🚀 What's New in v1.0.0

### Cloud Deployment (Milestone 8)

This release marks the first production deployment of the TN Gov AI Scheme Assistant to the public internet.

#### Deployment Infrastructure
- **Backend**: Deployed on Railway using Docker container
- **Frontend**: Deployed on Vercel (Next.js native platform)
- **PostgreSQL**: Railway managed PostgreSQL plugin (auto-SSL, auto-`DATABASE_URL`)
- **Vector Store**: Embedded ChromaDB on Railway persistent volume at `/data/chroma_db`

#### Production Startup Validation Gate
Added `backend/entrypoint.sh` — a fail-fast ChromaDB validator that runs before every container startup:
- **Check 1**: Persistent volume path is mounted and accessible
- **Check 2**: `tn_gov_schemes` collection exists in ChromaDB
- **Check 3**: `collection.count() == 31` (exact corpus integrity check)

If any check fails, the container exits with a structured diagnostic message and actionable remediation steps. The server **never starts** with an incomplete vector store.

#### Explicit Initialization Model
ChromaDB initialization is an **explicit one-time operation** — not automatic:
```bash
railway run python -m ingestion.cli ingest
```
This separates deployment (container start) from data initialization, making each step independently observable and debuggable.

#### New Files
- `backend/entrypoint.sh` — Production startup validation script
- `backend/scripts/init_vectorstore.py` — One-time initialization script
- `railway.json` — Railway deployment configuration
- `docker-compose.prod.yml` — Production compose override
- `frontend/.env.example` — Frontend environment variable documentation
- `.github/workflows/deploy.yml` — GitHub Actions CD pipeline

#### Updated Files
- `backend/Dockerfile` — Production-grade, uses `$PORT`, calls `entrypoint.sh`
- `frontend/Dockerfile` — Multi-stage production build with standalone output
- `frontend/next.config.ts` — Added `output: 'standalone'`
- `backend/app/core/config.py` — Added `app_env`, `frontend_url` fields; bumped version to 1.0.0
- `backend/.env.example` — Full production variable reference
- `README.md` — Production deployment architecture and ChromaDB explanation
- `DEPLOYMENT.md` — Complete Railway + Vercel deployment guide

---

## 📋 Verified Capabilities (Milestones 1–7)

| Feature | Status |
|---------|--------|
| Hybrid RAG (ChromaDB + BM25 + RRF) | ✅ Verified |
| Multilingual support (English + Tamil) | ✅ Verified |
| Citation generation (PDF + page number) | ✅ Verified |
| Out-of-scope refusal guardrails | ✅ Verified |
| Multi-provider LLM (Groq / OpenAI / Gemini) | ✅ Verified |
| PostgreSQL conversation persistence | ✅ Verified |
| Feedback submission and storage | ✅ Verified |
| Conversation history retrieval | ✅ Verified |
| Unit test suite (46/46 passing) | ✅ Verified |
| Hit@1 = 93.8%, Hit@3 = 100%, MRR = 0.9583 | ✅ Verified |

---

## ⚠️ Known Deployment Notes

### First Deployment
The container will fail to start on first deploy because ChromaDB is empty. This is **expected and by design**. Run the one-time initialization command to seed the vector store:
```bash
railway run python -m ingestion.cli ingest --data-dir /data
```

### Railway Free Tier Limitations
- Free tier containers **sleep after inactivity** (15 minutes). Upgrade to Hobby ($5/month) for always-on deployment.
- Persistent volumes require the Hobby plan.

### HuggingFace Model Download
First build takes 5–10 minutes due to `intfloat/multilingual-e5-large` (~550MB) download. Subsequent builds use Docker layer cache.

### CORS Configuration
After frontend deployment, update `ALLOWED_ORIGINS` in Railway variables to include the Vercel domain, then redeploy the backend.

---

## 🔗 Links

- Repository: https://github.com/aakash1552005/TNGov-AI-Assistant
- Deployment Guide: [DEPLOYMENT.md](DEPLOYMENT.md)
- Backend API Docs: `https://<railway-url>/docs` (Swagger UI)

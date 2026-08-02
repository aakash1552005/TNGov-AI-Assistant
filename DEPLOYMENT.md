# Production Deployment Guide
## Tamil Nadu Government AI Scheme Assistant

This document provides step-by-step production deployment instructions using Docker, Docker Compose, or native system services.

---

## 1. Prerequisites

- **Docker**: Engine version 24.0+ and Docker Compose v2.20+
- **Python**: 3.12+ (if deploying natively)
- **API Key**: Groq API key (`gsk_...`), OpenAI API key (`sk-...`), or Gemini API key (`AIzaSy...`)

---

## 2. Environment Configuration

1. Copy `.env.example` to `.env` inside the `backend` directory:
   ```bash
   cp backend/.env.example backend/.env
   ```
2. Edit `backend/.env` to configure production secrets and model selection:
   ```env
   LLM_PROVIDER=groq
   GROQ_API_KEY=gsk_your_actual_production_groq_api_key
   GROQ_MODEL=llama-3.3-70b-versatile
   DATABASE_URL=postgresql+asyncpg://postgres:postgres_secure_pass@db:5432/tngov_ai
   ALLOWED_ORIGINS=http://your-frontend-domain.com
   ```

---

## 3. Deployment via Docker Compose (Recommended)

To start the full production stack (FastAPI backend + PostgreSQL database + ChromaDB volume persistence):

```bash
# Build and launch containers in detached mode
docker compose up -d --build

# Verify container status
docker compose ps

# Inspect backend server logs
docker compose logs -f backend
```

---

## 4. Native Production Deployment (Uvicorn / Systemd)

1. **Install System Dependencies & Python Packages**:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Ingest Scheme Documents**:
   ```bash
   python -m app.cli ingest
   ```

3. **Start Production Server with Multiple Workers**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
   ```

---

## 5. Health Verification & Smoke Testing

Verify system health via HTTP requests:

```bash
# System Health Check Endpoint
curl http://localhost:8000/health

# Smoke Test Citizen Query
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the Chief Ministers Comprehensive Health Insurance Scheme?"}'
```

Expected `/health` response:
```json
{
  "status": "healthy",
  "app": "Tamil Nadu Government AI Scheme Assistant",
  "version": "1.0.0",
  "chroma_db_loaded": true,
  "bm25_index_loaded": true,
  "llm_provider": "groq",
  "llm_model": "llama-3.3-70b-versatile",
  "embedding_model": "intfloat/multilingual-e5-large"
}
```

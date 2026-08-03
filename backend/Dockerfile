# =============================================================================
# Dockerfile — TN Gov AI Scheme Assistant Backend (Production)
# =============================================================================
#
# Build context: project root (docker compose context: .)
# Dockerfile path: backend/Dockerfile
#
# On startup, entrypoint.sh validates ChromaDB (fail-fast — see entrypoint.sh).
# Ingestion is NOT automatic. Run once explicitly:
#   railway run python -m ingestion.cli ingest
# =============================================================================

# ─── Stage 1: Base Runtime Environment ─────────────────────────────────────
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies required for build & PDF processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code, ingestion, evaluation, and data modules
COPY backend/app /app/app
COPY backend/ingestion /app/ingestion
COPY backend/evaluation /app/evaluation
COPY backend/scripts /app/scripts
COPY backend/seed_data/chroma_db /app/seed_chroma_db
COPY data /app/data
COPY backend/tests /app/tests
COPY backend/pyproject.toml /app/pyproject.toml

# Copy and configure the production entrypoint
COPY backend/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Ensure persistent data directories exist
# ChromaDB and BM25 data are populated via the one-time initialization
# command (railway run python -m ingestion.cli ingest), NOT automatically.
RUN mkdir -p /data/chroma_db /data/processed/bm25 /data/raw

# Expose FastAPI application port
# Railway injects $PORT at runtime; entrypoint.sh uses it.
EXPOSE 8000

# Healthcheck via /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f "http://localhost:${PORT:-8000}/health" || exit 1

# Use entrypoint.sh — validates ChromaDB before starting uvicorn
ENTRYPOINT ["/app/entrypoint.sh"]

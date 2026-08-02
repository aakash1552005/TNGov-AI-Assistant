# ─── Stage 1: Base Runtime Environment ─────────────────────────
FROM python:3.12-slim as base

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
COPY data /app/data
COPY backend/tests /app/tests
COPY backend/pyproject.toml /app/pyproject.toml

# Ensure data directories exist for persistence
RUN mkdir -p /app/data/chroma_db /app/data/processed/bm25 /app/data/raw

# Expose FastAPI application port
EXPOSE 8000

# Healthcheck endpoint verification
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Launch uvicorn production server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

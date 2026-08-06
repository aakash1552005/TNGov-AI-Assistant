"""FastAPI application entry point.

Provides:
- Health-check endpoint (``GET /health``)
- CORS middleware configured for the frontend origin
- Lifespan handler for startup / shutdown logging and DB table creation
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, chat, feedback
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.rag import bm25_index, vector_store

# ── Logging ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan ─────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle application startup and shutdown events."""
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)

    # Create database tables (dev convenience — use Alembic migrations in production)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created / verified")
    except Exception as exc:
        logger.warning("Database connection unavailable on startup (%s). Persistence fallback active.", exc)

    # Pre-warm vector store embedding model & BM25 index
    try:
        from ingestion.embedder import preload_model
        from ingestion.pipeline import run_pipeline

        preload_model()
        vector_store.get_collection()
        bm25_index._ensure_loaded()

        # Auto-ingest dataset into persistent volume if chunk count is out of date (< 37) or model mismatch
        col = vector_store.get_collection()
        stored_model = (col.metadata or {}).get("embedding_model")
        current_chunks = vector_store.get_chunk_count()
        bm25_chunks = bm25_index.get_chunk_count()

        logger.info(
            "Vector store chunks: %d, BM25 chunks: %d, stored model: %s",
            current_chunks,
            bm25_chunks,
            stored_model,
        )

        if current_chunks < 37 or bm25_chunks < 37 or stored_model != settings.embedding_model:
            logger.info(
                "Rebuilding vector store & BM25 index for current embedding model (%s)...",
                settings.embedding_model,
            )
            run_pipeline(data_dir=Path(settings.data_dir), force=True)
            logger.info("Auto-ingestion complete!")

        logger.info("Vector store embedding model and BM25 index pre-warmed successfully")
    except Exception:
        logger.exception("Failed to pre-warm vector store or BM25 index")

    yield  # ← application runs here

    await engine.dispose()
    logger.info("Shutdown complete")


# ── App Instance ─────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Multilingual RAG assistant for Tamil Nadu Government welfare schemes. "
        "Answers are grounded exclusively in official government documents."
    ),
    lifespan=lifespan,
)

# ── Middleware ───────────────────────────────────────────────
origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────
app.include_router(chat.router)
app.include_router(feedback.router)
app.include_router(admin.router)


# ── Routes ───────────────────────────────────────────────────
@app.get("/health", tags=["system"])
async def health_check() -> dict[str, Any]:
    """Return health-check status and system component metadata."""
    chroma_ok = False
    try:
        col = vector_store.get_collection()
        chroma_ok = col is not None
    except Exception:
        chroma_ok = False

    bm25_ok = False
    try:
        bm25_ok = bm25_index.is_loaded()
    except Exception:
        logger.exception("Health check error while verifying BM25 index status")
        bm25_ok = False

    active_model = settings.groq_model

    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "chroma_db_loaded": chroma_ok,
        "bm25_index_loaded": bm25_ok,
        "llm_provider": settings.llm_provider,
        "llm_model": active_model,
        "embedding_model": settings.embedding_model,
    }

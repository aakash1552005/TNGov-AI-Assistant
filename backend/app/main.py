"""FastAPI application entry point.

Provides:
- Health-check endpoint (``GET /health``)
- CORS middleware configured for the frontend origin
- Lifespan handler for startup / shutdown logging and DB table creation
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, feedback
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
        vector_store.get_collection()
        bm25_index._ensure_loaded()
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

    if settings.llm_provider == "groq":
        active_model = settings.groq_model
    elif settings.llm_provider == "gemini":
        active_model = settings.gemini_model
    else:
        active_model = settings.model_name

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

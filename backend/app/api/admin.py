"""FastAPI router for admin diagnostics and dataset metrics.

Endpoints:
- GET /admin/stats: Return indexed document stats, total chunks, BM25 stats, Chroma DB status, and system info.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.rag import bm25_index, vector_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


class AdminStatsResponse(BaseModel):
    app_name: str
    version: str
    llm_provider: str
    embedding_model: str
    total_chunks: int
    bm25_indexed_chunks: int
    chroma_db_path: str
    status: str


@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats() -> Any:
    """Return diagnostic stats about the RAG pipeline and dataset."""
    total_chunks = vector_store.get_chunk_count()
    bm25_count = bm25_index.get_chunk_count()

    return AdminStatsResponse(
        app_name=settings.app_name,
        version=settings.app_version,
        llm_provider=settings.llm_provider,
        embedding_model=settings.embedding_model,
        total_chunks=total_chunks,
        bm25_indexed_chunks=bm25_count,
        chroma_db_path=settings.chroma_db_path,
        status="healthy",
    )

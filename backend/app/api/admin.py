"""FastAPI router for admin diagnostics and dataset metrics.

Endpoints:
- GET /admin/stats    — Indexed document stats, total chunks, BM25 stats, Chroma DB status.
- GET /admin/version  — Git commit hash, build timestamp, model info (Issue 4).
- GET /admin/dataset  — Full document/chunk manifest from ChromaDB (Issue 5).
- GET /admin/feedback — Aggregated feedback counts from PostgreSQL (Issue 3).
"""

from __future__ import annotations

import logging
import os
import subprocess
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.models.feedback import Feedback
from app.rag import bm25_index, vector_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Response models ───────────────────────────────────────────

class AdminStatsResponse(BaseModel):
    app_name: str
    version: str
    llm_provider: str
    embedding_model: str
    total_chunks: int
    bm25_indexed_chunks: int
    chroma_db_path: str
    status: str


class AdminVersionResponse(BaseModel):
    app_version: str
    git_commit: str
    build_timestamp: str
    embedding_model: str
    llm_provider: str
    llm_model: str
    schema_version: str


class DocumentInfo(BaseModel):
    document_name: str
    scheme_name: str
    department: str
    chunk_count: int


class AdminDatasetResponse(BaseModel):
    total_chunks: int
    embedding_model: str
    documents: list[DocumentInfo]
    chunk_ids_sample: list[str]
    chroma_db_path: str


class FeedbackEntry(BaseModel):
    rating: str
    comment: str | None
    created_at: str


class AdminFeedbackResponse(BaseModel):
    total_feedback: int
    up_count: int
    down_count: int
    latest_feedback: list[FeedbackEntry]


# ── Helpers ───────────────────────────────────────────────────

def _get_git_commit() -> str:
    """Return the current git commit hash (short).

    Checks GIT_COMMIT env var first (set by Railway CI), falls back to
    subprocess git command for local development.
    """
    commit = os.environ.get("GIT_COMMIT", "").strip()
    if commit:
        return commit[:12]
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def _get_llm_model() -> str:
    if settings.llm_provider == "groq":
        return settings.groq_model
    elif settings.llm_provider == "gemini":
        return settings.gemini_model
    return settings.model_name


# ── Endpoints ─────────────────────────────────────────────────

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


@router.get("/version", response_model=AdminVersionResponse)
async def get_admin_version() -> Any:
    """Return version, git commit, and model information.

    Used to verify Railway deployed the latest commit.
    GIT_COMMIT env var is populated by entrypoint.sh or Railway build config.
    """
    return AdminVersionResponse(
        app_version=settings.app_version,
        git_commit=_get_git_commit(),
        build_timestamp=os.environ.get(
            "BUILD_TIMESTAMP",
            datetime.now(timezone.utc).isoformat(),
        ),
        embedding_model=settings.embedding_model,
        llm_provider=settings.llm_provider,
        llm_model=_get_llm_model(),
        schema_version="1.0",
    )


@router.get("/dataset", response_model=AdminDatasetResponse)
async def get_admin_dataset() -> Any:
    """Return full document/chunk manifest from ChromaDB.

    Allows verifying that the correct number of chunks exist and which
    documents they belong to — without requiring direct database access.
    """
    try:
        col = vector_store.get_collection()
        total = col.count()

        # Get all metadata
        results = col.get(include=["metadatas"])
        metadatas = results.get("metadatas") or []
        ids = results.get("ids") or []

        # Aggregate by document
        doc_map: dict[str, DocumentInfo] = {}
        for meta in metadatas:
            doc_name = str(meta.get("document_name", "unknown"))
            if doc_name not in doc_map:
                doc_map[doc_name] = DocumentInfo(
                    document_name=doc_name,
                    scheme_name=str(meta.get("scheme_name", "unknown")),
                    department=str(meta.get("department", "unknown")),
                    chunk_count=0,
                )
            doc_map[doc_name].chunk_count += 1

        # Sample of first 10 chunk IDs
        chunk_ids_sample = ids[:10]

        return AdminDatasetResponse(
            total_chunks=total,
            embedding_model=settings.embedding_model,
            documents=sorted(doc_map.values(), key=lambda d: d.document_name),
            chunk_ids_sample=chunk_ids_sample,
            chroma_db_path=settings.chroma_db_path,
        )
    except Exception as exc:
        logger.exception("Failed to retrieve dataset manifest")
        return AdminDatasetResponse(
            total_chunks=0,
            embedding_model=settings.embedding_model,
            documents=[],
            chunk_ids_sample=[],
            chroma_db_path=settings.chroma_db_path,
        )


@router.get("/feedback", response_model=AdminFeedbackResponse)
async def get_admin_feedback(db: AsyncSession = Depends(get_db)) -> Any:
    """Return aggregated feedback counts from PostgreSQL.

    Returns total counts and the 10 most recent feedback entries.
    No PII is returned — message IDs and session IDs are excluded.
    """
    try:
        # Total count
        total_stmt = select(func.count(Feedback.id))
        total_result = await db.execute(total_stmt)
        total = total_result.scalar_one_or_none() or 0

        # Up count
        up_stmt = select(func.count(Feedback.id)).where(Feedback.rating == "up")
        up_result = await db.execute(up_stmt)
        up_count = up_result.scalar_one_or_none() or 0

        # Down count
        down_count = total - up_count

        # Latest 10 entries (no PII — exclude message_id)
        latest_stmt = (
            select(Feedback.rating, Feedback.comment, Feedback.created_at)
            .order_by(Feedback.created_at.desc())
            .limit(10)
        )
        latest_result = await db.execute(latest_stmt)
        latest_rows = latest_result.all()

        latest_feedback = [
            FeedbackEntry(
                rating=row.rating,
                comment=row.comment,
                created_at=row.created_at.isoformat() if row.created_at else "",
            )
            for row in latest_rows
        ]

        return AdminFeedbackResponse(
            total_feedback=total,
            up_count=up_count,
            down_count=down_count,
            latest_feedback=latest_feedback,
        )
    except Exception as exc:
        logger.exception("Failed to retrieve feedback stats")
        return AdminFeedbackResponse(
            total_feedback=-1,
            up_count=0,
            down_count=0,
            latest_feedback=[],
        )

"""FastAPI router for chat endpoint.

Endpoint: POST /chat
Consumes generation_service.answer_question() directly.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.services import generation_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["chat"])


class ChatRequest(BaseModel):
    question: str


class CitationSchema(BaseModel):
    scheme_name: str
    department: str
    document_name: str
    page_number: int | None = 1
    source_url: str = ""
    excerpt: str


class RetrievalMetadataSchema(BaseModel):
    total_retrieved: int
    top_rrf_score: float | None
    vector_results_count: int
    bm25_results_count: int
    llm_called: bool


class ChatResponseSchema(BaseModel):
    answer: str
    citations: list[CitationSchema]
    retrieval_metadata: RetrievalMetadataSchema


@router.post("/chat", response_model=ChatResponseSchema)
async def chat(request: ChatRequest) -> Any:
    """Execute RAG question-answering pipeline via generation_service."""
    question = request.question.strip() if request.question else ""

    if not question:
        raise HTTPException(status_code=422, detail="Question cannot be empty.")

    if len(question) > settings.max_query_length:
        raise HTTPException(
            status_code=422,
            detail=f"Question exceeds maximum query length of {settings.max_query_length} characters.",
        )

    try:
        response = generation_service.answer_question(question)
        return response
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected error during chat generation for question: %s", question[:80])
        raise HTTPException(status_code=500, detail="Internal server error") from exc

"""FastAPI router for chat and conversation history endpoints.

Endpoints:
- POST /chat: RAG Q&A with optional session continuation & resilient DB persistence.
- GET /chat/{session_id}: Retrieve past conversation message history.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.services import generation_service, persistence_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["chat"])


class ChatRequest(BaseModel):
    question: str
    session_id: uuid.UUID | None = None


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
    confidence_level: str = "Low"


class ChatResponseSchema(BaseModel):
    session_id: uuid.UUID
    message_id: uuid.UUID | None = None
    answer: str
    citations: list[CitationSchema]
    retrieval_metadata: RetrievalMetadataSchema
    related_schemes: list[str] = []
    suggestions: list[str] = []


class MessageItemSchema(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    created_at: str


class ConversationHistorySchema(BaseModel):
    session_id: uuid.UUID
    messages: list[MessageItemSchema]


@router.post("/chat", response_model=ChatResponseSchema)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Execute RAG question-answering pipeline via generation_service.

    Persists chat sessions and messages asynchronously to PostgreSQL.
    Database failures are caught and logged without disrupting answer generation.
    """
    question = request.question.strip() if request.question else ""

    if not question:
        raise HTTPException(status_code=422, detail="Question cannot be empty.")

    if len(question) > settings.max_query_length:
        raise HTTPException(
            status_code=422,
            detail=f"Question exceeds maximum query length of {settings.max_query_length} characters.",
        )

    # 1. Handle or create Session ID & Conversation Memory Context
    active_session_id = request.session_id or uuid.uuid4()
    context_prefix: str | None = None

    # Try session retrieval & conversation history for memory
    try:
        if request.session_id:
            session_obj = await persistence_service.get_session(db, request.session_id)
            if not session_obj:
                try:
                    new_session = persistence_service.ChatSession(id=request.session_id)
                    db.add(new_session)
                    await db.commit()
                except Exception:
                    await db.rollback()
            else:
                # Fetch recent messages to extract conversational context
                past_messages = await persistence_service.get_conversation(db, request.session_id)
                if past_messages:
                    # Look at the last user message or assistant message to extract context
                    for m in reversed(past_messages):
                        if m.role == "user" and m.content != question:
                            context_prefix = m.content[:100]
                            break
        else:
            session_obj = await persistence_service.create_session(db)
            active_session_id = session_obj.id
    except Exception:
        await db.rollback()
        logger.exception("Database error while initializing session — proceeding with session_id %s", active_session_id)

    # 2. Save user message
    try:
        await persistence_service.save_user_message(db, active_session_id, question)
    except Exception:
        await db.rollback()
        logger.exception("Database error while saving user message — proceeding with generation")

    # 3. Call core generation service with optional conversation memory context
    gen_response = generation_service.answer_question(question, context_prefix=context_prefix)

    # 4. Save assistant response message
    assistant_msg_id: uuid.UUID | None = None
    try:
        msg_obj = await persistence_service.save_assistant_message(
            db, active_session_id, gen_response.answer
        )
        assistant_msg_id = msg_obj.id
    except Exception:
        await db.rollback()
        logger.exception("Database error while saving assistant message — proceeding with response")

    # 5. Return typed response
    citations_data = [
        CitationSchema(
            scheme_name=c.scheme_name,
            department=c.department,
            document_name=c.document_name,
            page_number=c.page_number,
            source_url=c.source_url,
            excerpt=c.excerpt,
        )
        for c in gen_response.citations
    ]
    meta_data = RetrievalMetadataSchema(
        total_retrieved=gen_response.retrieval_metadata.total_retrieved,
        top_rrf_score=gen_response.retrieval_metadata.top_rrf_score,
        vector_results_count=gen_response.retrieval_metadata.vector_results_count,
        bm25_results_count=gen_response.retrieval_metadata.bm25_results_count,
        llm_called=gen_response.retrieval_metadata.llm_called,
        confidence_level=getattr(gen_response.retrieval_metadata, "confidence_level", "Medium"),
    )
    return ChatResponseSchema(
        session_id=active_session_id,
        message_id=assistant_msg_id,
        answer=gen_response.answer,
        citations=citations_data,
        retrieval_metadata=meta_data,
        related_schemes=gen_response.related_schemes,
        suggestions=gen_response.suggestions,
    )


@router.get("/chat/{session_id}", response_model=ConversationHistorySchema)
async def get_chat_history(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Retrieve all stored user and assistant messages for a session."""
    try:
        session_obj = await persistence_service.get_session(db, session_id)
        if not session_obj:
            raise HTTPException(status_code=404, detail="Session not found")

        messages = await persistence_service.get_conversation(db, session_id)
        msg_items = [
            MessageItemSchema(
                id=m.id,
                role=m.role,
                content=m.content,
                created_at=m.created_at.isoformat(),
            )
            for m in messages
        ]
        return ConversationHistorySchema(
            session_id=session_id,
            messages=msg_items,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to retrieve conversation history for session %s", session_id)
        raise HTTPException(status_code=500, detail="Internal server error") from exc

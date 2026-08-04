"""Dedicated persistence service for conversation history and user feedback.

Completely decoupled from retrieval and generation services. Contains NO
RAG, vector search, or LLM logic.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage, ChatSession
from app.models.feedback import Feedback

logger = logging.getLogger(__name__)


async def create_session(db: AsyncSession) -> ChatSession:
    """Create a new conversation session in PostgreSQL."""
    session = ChatSession(id=uuid.uuid4())
    db.add(session)
    await db.commit()
    await db.refresh(session)
    logger.info("Created new ChatSession: %s", session.id)
    return session


async def get_session(db: AsyncSession, session_id: uuid.UUID) -> ChatSession | None:
    """Retrieve an existing session by UUID."""
    stmt = select(ChatSession).where(ChatSession.id == session_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_conversation(db: AsyncSession, session_id: uuid.UUID) -> list[ChatMessage]:
    """Retrieve all messages in a conversation ordered by created_at."""
    stmt = select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def save_user_message(
    db: AsyncSession,
    session_id: uuid.UUID,
    content: str,
) -> ChatMessage:
    """Save a user question message to the session."""
    msg = ChatMessage(
        id=uuid.uuid4(),
        session_id=session_id,
        role="user",
        content=content,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def save_assistant_message(
    db: AsyncSession,
    session_id: uuid.UUID,
    content: str,
) -> ChatMessage:
    """Save an assistant response message to the session."""
    msg = ChatMessage(
        id=uuid.uuid4(),
        session_id=session_id,
        role="assistant",
        content=content,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def save_feedback(
    db: AsyncSession,
    message_id: uuid.UUID,
    rating: str,
    comment: str | None = None,
) -> Feedback:
    """Save user feedback rating ("up" | "down") for a specific assistant message."""
    fb = Feedback(
        id=uuid.uuid4(),
        message_id=message_id,
        rating=rating,
        comment=comment,
    )
    db.add(fb)
    await db.commit()
    await db.refresh(fb)
    logger.info("Saved feedback %s for message %s", rating, message_id)
    return fb


async def get_conversation(
    db: AsyncSession,
    session_id: uuid.UUID,
) -> Sequence[ChatMessage]:
    """Get all messages in a session ordered by creation timestamp."""
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()

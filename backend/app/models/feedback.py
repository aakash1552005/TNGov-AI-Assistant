"""Feedback ORM model — user ratings on assistant responses.

Table:
- ``feedback``: Stores thumbs up/down ratings and optional comments.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Feedback(Base):
    """User feedback rating for a specific assistant chat message."""

    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rating: Mapped[str] = mapped_column(
        String(10),
        nullable=False,  # "up" | "down"
    )
    comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationship back to chat message
    message: Mapped[ChatMessage] = relationship(
        "ChatMessage",
        back_populates="feedback",
    )

    def __repr__(self) -> str:
        return f"<Feedback(id={self.id!r}, rating={self.rating!r})>"

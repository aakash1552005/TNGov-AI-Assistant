"""User model — optional user profile for personalization.

Matches the ``users`` table defined in the project specification.
Users are optional — anonymous usage is supported.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    """An optional user profile."""

    __tablename__ = "users"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    language_pref: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="en",
    )
    district: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<User(id={self.user_id!r}, lang={self.language_pref!r})>"

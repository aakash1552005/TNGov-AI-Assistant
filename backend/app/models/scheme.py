"""Scheme model — government welfare scheme metadata.

Matches the ``schemes`` table defined in the project specification.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Scheme(Base):
    """A Tamil Nadu government welfare scheme."""

    __tablename__ = "schemes"

    scheme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    scheme_name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    department: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    eligibility_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    benefits: Mapped[str | None] = mapped_column(Text, nullable=True)
    income_limit: Mapped[str | None] = mapped_column(String(200), nullable=True)
    age_limit: Mapped[str | None] = mapped_column(String(200), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(50), nullable=True)
    required_documents: Mapped[str | None] = mapped_column(Text, nullable=True)
    application_link: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    district: Mapped[str | None] = mapped_column(String(200), nullable=True)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    def __repr__(self) -> str:
        return f"<Scheme(name={self.scheme_name!r}, dept={self.department!r})>"

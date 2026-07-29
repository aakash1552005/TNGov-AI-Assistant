"""FastAPI router for user feedback endpoint.

Endpoint:
- POST /feedback: Record thumbs up/down rating and optional comment for an assistant message.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services import persistence_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["feedback"])


class FeedbackRequest(BaseModel):
    message_id: uuid.UUID
    rating: str = Field(..., description="'up' or 'down'")
    comment: str | None = None


class FeedbackResponseSchema(BaseModel):
    status: str
    message: str


@router.post("/feedback", response_model=FeedbackResponseSchema)
async def submit_feedback(
    request: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Submit user rating (thumbs up/down) for an assistant response."""
    rating_lower = request.rating.strip().lower() if request.rating else ""

    if rating_lower not in ("up", "down"):
        raise HTTPException(
            status_code=422,
            detail="Rating must be either 'up' or 'down'.",
        )

    try:
        await persistence_service.save_feedback(
            db,
            message_id=request.message_id,
            rating=rating_lower,
            comment=request.comment,
        )
        return FeedbackResponseSchema(
            status="success",
            message="Feedback submitted successfully.",
        )
    except Exception as exc:
        logger.exception("Failed to save feedback for message %s", request.message_id)
        # Check if error was due to missing message_id
        if "foreignkey" in str(exc).lower() or "violates foreign key constraint" in str(exc).lower():
            raise HTTPException(status_code=404, detail="Message not found") from exc
        raise HTTPException(status_code=500, detail="Internal server error") from exc

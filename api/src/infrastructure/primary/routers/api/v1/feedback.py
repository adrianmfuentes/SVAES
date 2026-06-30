import logging
import uuid
from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.future import select

from core.email import email_service
from core.config import settings
from infrastructure.secondary.database.get_async_session import AsyncSessionLocal
from infrastructure.secondary.database.models.feedback_model import FeedbackModel
from . import ERROR_INTERNO

_log = logging.getLogger(__name__)

router = APIRouter(tags=["Feedback"])

_PUBLIC_FEEDBACK_LIMIT = 50


class FeedbackPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(default="", max_length=255)
    rating: int = Field(..., ge=0, le=5)
    comments: str = Field(..., min_length=1, max_length=2000)


@router.post("/api/v1/feedback", status_code=status.HTTP_201_CREATED)
async def submit_feedback(payload: FeedbackPayload):
    try:
        async with AsyncSessionLocal() as session:
            session.add(FeedbackModel(
                id=uuid.uuid4(),
                name=payload.name,
                email=payload.email or None,
                rating=payload.rating,
                comments=payload.comments,
            ))
            await session.commit()
    except Exception:
        _log.exception("Failed to persist feedback")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)

    try:
        await email_service.send_feedback_email({
            "name": payload.name,
            "email": payload.email,
            "rating": payload.rating,
            "comments": payload.comments,
        })
        _log.info("Feedback received and email sent")
    except Exception:
        _log.exception("Feedback was persisted but the notification email failed")

    return {"status": "ok"}


@router.get("/api/v1/feedback/public")
async def list_public_feedback(x_feedback_sync_key: str | None = Header(default=None)):
    if not settings.feedback_sync_key or x_feedback_sync_key != settings.feedback_sync_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(FeedbackModel)
            .order_by(FeedbackModel.created_at.desc())
            .limit(_PUBLIC_FEEDBACK_LIMIT)
        )
        rows = result.scalars().all()

    return [
        {
            "name": row.name,
            "rating": row.rating,
            "comments": row.comments,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]

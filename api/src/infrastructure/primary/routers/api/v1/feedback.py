import logging
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from core.email import email_service
from core.config import settings
from . import ERROR_INTERNO

_log = logging.getLogger(__name__)

router = APIRouter(tags=["Feedback"])


class FeedbackPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=1, max_length=255)
    rating: int = Field(..., ge=0, le=5)
    comments: str = Field(..., min_length=1, max_length=2000)


@router.post("/api/v1/feedback", status_code=status.HTTP_201_CREATED)
async def submit_feedback(payload: FeedbackPayload):
    try:
        await email_service.send_feedback_email({
            "name": payload.name,
            "email": payload.email,
            "rating": payload.rating,
            "comments": payload.comments,
        })
        _log.info("Feedback received and email sent")
        return {"status": "ok"}
    except Exception:
        _log.exception("Feedback email failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo enviar el feedback. Por favor, inténtalo de nuevo más tarde.",
        )

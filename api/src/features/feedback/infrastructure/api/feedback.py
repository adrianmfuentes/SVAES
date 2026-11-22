import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from shared.infrastructure.config import settings
from features.feedback.application.feedback import ListPublicFeedback, SubmitFeedback
from features.feedback.container import get_list_public_feedback, get_submit_feedback
from shared.infrastructure.api_errors import ERROR_INTERNO


_log = logging.getLogger(__name__)
router = APIRouter(tags=["Feedback"])


class FeedbackPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(default="", max_length=255)
    rating: int = Field(..., ge=0, le=5)
    comments: str = Field(..., min_length=1, max_length=2000)


@router.post("/api/v1/feedback", status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    payload: FeedbackPayload,
    use_case: Annotated[SubmitFeedback, Depends(get_submit_feedback)],
):
    try:
        await use_case.execute(payload.name, payload.email, payload.rating, payload.comments)
    except Exception:
        _log.exception("Failed to persist feedback")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)
    return {"status": "ok"}


@router.get("/api/v1/feedback/public")
async def list_public_feedback(
    use_case: Annotated[ListPublicFeedback, Depends(get_list_public_feedback)],
    x_feedback_sync_key: Annotated[str | None, Header()] = None,
):
    if not settings.feedback_sync_key or x_feedback_sync_key != settings.feedback_sync_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    rows = await use_case.execute()
    return [
        {"name": row.name, "rating": row.rating, "comments": row.comments, "created_at": row.created_at.isoformat()}
        for row in rows
    ]

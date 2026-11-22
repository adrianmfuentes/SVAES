import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from shared.application.i_mailer import IMailer


_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class PublicFeedback:
    name: str
    rating: int
    comments: str
    created_at: datetime


class IFeedbackRepository(Protocol):
    async def add(self, name: str, email: str, rating: int, comments: str) -> None: ...
    async def list_recent(self, limit: int) -> list[PublicFeedback]: ...


class SubmitFeedback:
    def __init__(self, repository: IFeedbackRepository, mailer: IMailer) -> None:
        self._repository = repository
        self._mailer = mailer

    async def execute(self, name: str, email: str, rating: int, comments: str) -> None:
        await self._repository.add(name, email, rating, comments)
        try:
            await self._mailer.send_feedback_email({
                "name": name, "email": email, "rating": rating, "comments": comments,
            })
            _log.info("Feedback received and email sent")
        except Exception:
            _log.exception("Feedback was persisted but the notification email failed")


class ListPublicFeedback:
    def __init__(self, repository: IFeedbackRepository) -> None:
        self._repository = repository

    async def execute(self) -> list[PublicFeedback]:
        return await self._repository.list_recent(50)

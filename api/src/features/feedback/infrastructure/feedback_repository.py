from uuid import uuid4

from sqlalchemy import select

from features.feedback.application.feedback import PublicFeedback
from shared.infrastructure.database.get_async_session import AsyncSessionLocal
from shared.infrastructure.database.models.feedback_model import FeedbackModel


class SqlFeedbackRepository:
    async def add(self, name: str, email: str, rating: int, comments: str) -> None:
        async with AsyncSessionLocal() as session:
            session.add(FeedbackModel(id=uuid4(), name=name, email=email or None, rating=rating, comments=comments))
            await session.commit()

    async def list_recent(self, limit: int) -> list[PublicFeedback]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(FeedbackModel).order_by(FeedbackModel.created_at.desc()).limit(limit)
            )
            return [
                PublicFeedback(row.name, row.rating, row.comments, row.created_at)
                for row in result.scalars().all()
            ]

import uuid
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
from infrastructure.database.base import Base

if TYPE_CHECKING:
    from infrastructure.database.models.release import ReleaseModel


class VerificationResultModel(Base):
    __tablename__ = "verification_result"
    __table_args__ = (
        Index("ix_verification_result_release_id", "release_id"),
        Index("ix_verification_result_executed_at", "executed_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    release_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("release.id"), nullable=False)
    verdict: Mapped[str] = mapped_column(
        Enum("VALIDO", "CON_ADVERTENCIAS", "NO_VALIDO", name="verdict_type"),
        nullable=False,
    )
    rule_results: Mapped[dict] = mapped_column(JSONB, nullable=True)
    profile_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=True)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=True)

    release: Mapped["ReleaseModel"] = relationship(back_populates="verification_results")
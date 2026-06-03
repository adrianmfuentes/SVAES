from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from infrastructure.secondary.database.models.base import Base
from domain.enums import VerdictType


class VerificationResultModel(Base):
    __tablename__ = "verification_result"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    release_id = Column(PG_UUID(as_uuid=True), ForeignKey("release.id"), nullable=False)
    verdict = Column(String(30), nullable=False, default=VerdictType.INVALID.value)
    duration_ms = Column(Integer, nullable=False, default=0)
    summary = Column(JSON, nullable=True, default=dict)
    rule_results = Column(JSON, nullable=True, default=list)
    profile_snapshot = Column(JSON, nullable=True, default=dict)
    executed_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
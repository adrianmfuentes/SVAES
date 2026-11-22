from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, JSON
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from shared.infrastructure.database_base import Base
from shared.domain.enums import VerdictType


class VerificationResultModel(Base):
    __tablename__ = "verification_result"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    release_id = Column(PG_UUID(as_uuid=True), ForeignKey("release.id", ondelete="CASCADE"), nullable=False, index=True)
    verdict = Column(String(30), nullable=False, default=VerdictType.INVALID.value)
    duration_ms = Column(Integer, nullable=True, default=0)
    summary = Column(JSON().with_variant(JSONB(), "postgresql"), nullable=True, default=dict)
    rule_results = Column(JSON().with_variant(JSONB(), "postgresql"), nullable=True, default=list)
    profile_snapshot = Column(JSON().with_variant(JSONB(), "postgresql"), nullable=True, default=dict)
    executed_at = Column(DateTime(timezone=True), nullable=False, index=True, default=lambda: datetime.now(timezone.utc))
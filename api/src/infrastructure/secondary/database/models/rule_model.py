from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Boolean, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from infrastructure.secondary.database.models.base import Base
from domain.enums import SeverityType


class VerificationRuleModel(Base):
    __tablename__ = "verification_rule"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(PG_UUID(as_uuid=True), ForeignKey("verification_profile.id", ondelete="cascade"), nullable=False)
    rule_template = Column(String(100), nullable=False)
    severity = Column(SQLEnum(SeverityType, name='severity_type_new', create_type=False, native_enum=False), nullable=False, default=SeverityType.HIGH)
    params = Column(JSON, nullable=True, default=dict)
    connector_instance_id = Column(PG_UUID(as_uuid=True), ForeignKey("connector_instance.id"), nullable=True)
    display_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
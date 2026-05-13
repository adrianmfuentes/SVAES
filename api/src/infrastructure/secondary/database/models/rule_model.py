from datetime import datetime
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import declarative_base
from domain.enums import SeverityType

Base = declarative_base()


class VerificationRuleModel(Base):
    __tablename__ = "verification_rule"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(PG_UUID(as_uuid=True), ForeignKey("verification_profile.id"), nullable=False)
    rule_template = Column(String(100), nullable=False)
    severity = Column(String(20), nullable=False, default=SeverityType.HIGH.value)
    params = Column(JSON, nullable=True, default=dict)
    connector_instance_id = Column(PG_UUID(as_uuid=True), ForeignKey("connector_instance.id"), nullable=True)
    display_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
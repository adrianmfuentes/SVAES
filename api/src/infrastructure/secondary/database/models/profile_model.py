from datetime import datetime
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class VerificationProfileModel(Base):
    __tablename__ = "verification_profile"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(PG_UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True, default="")
    is_default = Column(Boolean, nullable=False, default=False)
    rules = Column(JSON, nullable=True, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
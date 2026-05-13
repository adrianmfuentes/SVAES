from datetime import datetime
import uuid
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class OrganizationModel(Base):
    __tablename__ = "organization"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    owner_id = Column(PG_UUID(as_uuid=True), ForeignKey("user.id"), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    plan = Column(String(50), nullable=False, default="default")
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
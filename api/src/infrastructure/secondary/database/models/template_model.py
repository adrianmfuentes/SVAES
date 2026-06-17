from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from infrastructure.secondary.database.models.base import Base


class TemplateModel(Base):
    __tablename__ = "template"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(PG_UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True, default="")
    profile_id = Column(PG_UUID(as_uuid=True), ForeignKey("verification_profile.id", ondelete="cascade"), nullable=False)
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    project_name_template = Column(String(200), nullable=True)
    is_archived = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from shared.infrastructure.database.models.base import Base


class OrganizationModel(Base):
    __tablename__ = "organization"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    owner_id = Column(PG_UUID(as_uuid=True), ForeignKey("user.id", name="fk_org_owner"), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
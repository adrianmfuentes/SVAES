"""
Modelo de SQLAlchemy para la entidad Project, representando la tabla 'projects' en la base de datos.
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from shared.infrastructure.database.models.base import Base
import uuid

class ProjectModel(Base):
    __tablename__ = 'project'
    __table_args__ = (UniqueConstraint('organization_id', 'name'),)
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organization.id", ondelete="CASCADE"), nullable=False)
    profile_id = Column(UUID(as_uuid=True), nullable=True)
    is_archived = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)
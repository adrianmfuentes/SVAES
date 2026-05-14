"""
Modelo de SQLAlchemy para la entidad Project, representando la tabla 'projects' en la base de datos.
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()

class ProjectModel(Base):
    __tablename__ = 'projects'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organization.id'), nullable=False)
    profile_id = Column(UUID(as_uuid=True), nullable=False)
    is_archived = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
"""
Modelo de SQLAlchemy para la entidad Project, representando la tabla 'projects' en la base de datos.
"""

from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
import uuid

# Clase base para los modelos de SQLAlchemy, proporcionando funcionalidades comunes para todos los modelos que hereden de ella.
Base = declarative_base() 

class ProjectModel(Base):
    __tablename__ = 'projects'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=False)
    profile_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
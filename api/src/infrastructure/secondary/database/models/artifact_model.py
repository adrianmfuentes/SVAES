from datetime import datetime
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import declarative_base
from domain.enums import ArtifactType

Base = declarative_base()


class ArtifactModel(Base):
    __tablename__ = "artifact"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    release_id = Column(PG_UUID(as_uuid=True), ForeignKey("release.id"), nullable=False)
    connector_instance_id = Column(PG_UUID(as_uuid=True), ForeignKey("connector_instance.id"), nullable=False)
    artifact_type = Column(String(20), nullable=False, default=ArtifactType.TAREA.value)
    external_ref = Column(String(500), nullable=False)
    metadata = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
from datetime import datetime, timezone
import uuid
from sqlalchemy import Index, Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from shared.infrastructure.database.models.base import Base
from shared.domain.enums import ArtifactType


class ArtifactModel(Base):
    __tablename__ = "artifact"
    __table_args__ = (Index("ix_artifact_type", "artifact_type"),)
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    release_id = Column(PG_UUID(as_uuid=True), ForeignKey("release.id", ondelete="CASCADE"), nullable=False, index=True)
    connector_instance_id = Column(PG_UUID(as_uuid=True), ForeignKey("connector_instance.id"), nullable=True)
    connector_implementation = Column(String(50), nullable=False)
    artifact_type = Column(String(20), nullable=False, default=ArtifactType.TAREA.value)
    external_ref = Column(String(500), nullable=False)
    description = Column(String(1000), nullable=True, default="")
    artifact_metadata = Column('metadata', JSON().with_variant(JSONB(), 'postgresql'), nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
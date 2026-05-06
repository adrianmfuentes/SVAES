import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
from infrastructure.database.base import Base

if TYPE_CHECKING:
    from infrastructure.database.models.release import ReleaseModel

class ArtifactModel(Base):
    __tablename__ = "artifact"
    __table_args__ = (
        Index("ix_artifact_release_id", "release_id"),
        Index("ix_artifact_type", "artifact_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    release_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("release.id"), nullable=False)
    connector_instance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("connector_instance.id"), nullable=True)
    artifact_type: Mapped[str] = mapped_column(String, nullable=False)  # TAREA, CODIGO, DOCUMENTO
    external_ref: Mapped[str] = mapped_column(String, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    release: Mapped["ReleaseModel"] = relationship(back_populates="artifacts")
import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from api.src.infrastructure.secondary.database.base import Base

if TYPE_CHECKING:
    from api.src.infrastructure.secondary.database.models.project import ProjectModel
    from api.src.infrastructure.secondary.database.models.artifact import ArtifactModel
    from api.src.infrastructure.secondary.database.models.verification_result import VerificationResultModel

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

class ReleaseModel(Base):
    __tablename__ = "release"
    __table_args__ = (UniqueConstraint("project_id", "version"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("project.id"), nullable=False)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("verification_profile.id"), nullable=True)
    version: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("BORRADOR", "PENDIENTE", "EN_VERIFICACION", "VALIDA", "CON_ADVERTENCIAS", "NO_VALIDA", "ARCHIVADA", name="release_status"),
        default="BORRADOR",
        nullable=False,
    )
    description: Mapped[str] = mapped_column(String, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    project: Mapped["ProjectModel"] = relationship(back_populates="releases")
    artifacts: Mapped[list["ArtifactModel"]] = relationship(back_populates="release")
    verification_results: Mapped[list["VerificationResultModel"]] = relationship(back_populates="release")
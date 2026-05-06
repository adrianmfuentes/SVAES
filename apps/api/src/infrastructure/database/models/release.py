import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from infrastructure.database.base import Base

if TYPE_CHECKING:
    from infrastructure.database.models.project import ProjectModel
    from infrastructure.database.models.artifact import ArtifactModel
    from infrastructure.database.models.verification_result import VerificationResultModel


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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    project: Mapped["ProjectModel"] = relationship(back_populates="releases")
    artifacts: Mapped[list["ArtifactModel"]] = relationship(back_populates="release")
    verification_results: Mapped[list["VerificationResultModel"]] = relationship(back_populates="release")
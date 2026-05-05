from __future__ import annotations
import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import Enum, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

_NOW = text("now()")
from domain.entities.enums import ReleaseStatus

if TYPE_CHECKING:
    from .project import ProjectModel

class ReleaseModel(Base):
    __tablename__ = "release"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        server_default=text("gen_random_uuid()")
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("project.id", ondelete="CASCADE"), nullable=False
    )
    # Asumimos que más adelante crearás verification_profile y user
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    
    version: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    
    # Uso de tipo Enum nativo de PostgreSQL
    status: Mapped[ReleaseStatus] = mapped_column(
        Enum(ReleaseStatus, name="release_status_enum", create_type=True), 
        default=ReleaseStatus.BORRADOR,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=_NOW
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=_NOW, onupdate=_NOW
    )

    # Restricción UNIQUE según esquema (project_id, version)
    __table_args__ = (
        UniqueConstraint('project_id', 'version', name='uq_release_project_version'),
    )

    # Relaciones
    project: Mapped["ProjectModel"] = relationship(
        "ProjectModel", back_populates="releases"
    )
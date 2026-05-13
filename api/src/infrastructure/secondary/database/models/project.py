import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from api.src.infrastructure.secondary.database.base import Base

if TYPE_CHECKING:
    from api.src.infrastructure.secondary.database.models.organization import OrganizationModel
    from api.src.infrastructure.secondary.database.models.release import ReleaseModel

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

class ProjectModel(Base):
    __tablename__ = "project"
    __table_args__ = (UniqueConstraint("organization_id", "name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    organization: Mapped["OrganizationModel"] = relationship(back_populates="projects")
    releases: Mapped[list["ReleaseModel"]] = relationship(back_populates="project")
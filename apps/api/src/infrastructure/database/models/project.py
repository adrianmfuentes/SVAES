import uuid
from datetime import datetime
from sqlalchemy import String, text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from .base import Base

class ProjectModel(Base):
    __tablename__ = "project"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), onupdate=text("now()")
    )

    # Restricción UNIQUE según esquema (org_id, name)
    __table_args__ = (
        UniqueConstraint('organization_id', 'name', name='uq_project_org_name'),
    )

    # Relaciones
    organization: Mapped["OrganizationModel"] = relationship(
        "OrganizationModel", back_populates="projects"
    )
    releases: Mapped[list["ReleaseModel"]] = relationship(
        "ReleaseModel", back_populates="project", cascade="all, delete-orphan"
    )
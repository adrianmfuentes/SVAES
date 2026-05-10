import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
from infrastructure.database.base import Base

if TYPE_CHECKING:
    from infrastructure.database.models.user_membership import UserMembershipModel
    from infrastructure.database.models.project import ProjectModel
    from infrastructure.database.models.connector_instance import ConnectorInstanceModel
    from infrastructure.database.models.verification_profile import VerificationProfileModel

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

class OrganizationModel(Base):
    __tablename__ = "organization"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    plan: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    memberships: Mapped[list["UserMembershipModel"]] = relationship(back_populates="organization")
    projects: Mapped[list["ProjectModel"]] = relationship(back_populates="organization")
    connectors: Mapped[list["ConnectorInstanceModel"]] = relationship(back_populates="organization")
    profiles: Mapped[list["VerificationProfileModel"]] = relationship(back_populates="organization")
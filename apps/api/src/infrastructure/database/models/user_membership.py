import uuid
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
from infrastructure.database.base import Base

if TYPE_CHECKING:
    from infrastructure.database.models.organization import OrganizationModel
    from infrastructure.database.models.user import UserModel


class UserMembershipModel(Base):
    __tablename__ = "user_membership"
    __table_args__ = (UniqueConstraint("organization_id", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    role: Mapped[str] = mapped_column(Enum("VIEWER", "OPERATOR", "MANAGER", "ADMIN", name="membership_role"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    organization: Mapped["OrganizationModel"] = relationship(back_populates="memberships")
    user: Mapped["UserModel"] = relationship(back_populates="memberships")
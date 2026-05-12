import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
from infrastructure.database.base import Base

if TYPE_CHECKING:
    from infrastructure.database.models.user_membership import UserMembershipModel

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserModel(Base):
    __tablename__ = "user"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=True)
    role: Mapped[str] = mapped_column(
        Enum("VIEWER", "OPERATOR", "MANAGER", "ADMIN", name="user_role"),
        nullable=False,
        default="VIEWER",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    memberships: Mapped[list["UserMembershipModel"]] = relationship(back_populates="user")

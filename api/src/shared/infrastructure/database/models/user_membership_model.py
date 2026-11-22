from datetime import datetime, timezone
import uuid
from sqlalchemy import ForeignKey, Column, DateTime, Enum, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from shared.infrastructure.database.models.base import Base
from shared.domain.enums import UserRole


class UserMembershipModel(Base):
    __tablename__ = "user_membership"
    __table_args__ = (UniqueConstraint("organization_id", "user_id"),)

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(PG_UUID(as_uuid=True), ForeignKey("organization.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    role = Column(Enum(UserRole, name='membership_role', values_callable=lambda x: [e.value for e in x]), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

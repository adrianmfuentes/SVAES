from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Integer, Enum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from shared.infrastructure.database.models.base import Base
from shared.domain.enums import UserRole


class UserModel(Base):
    __tablename__ = "user"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    display_name = Column(String(100), nullable=True)
    role = Column(Enum(UserRole, name='user_role', values_callable=lambda x: [e.value for e in x]), nullable=False, default=UserRole.U2)
    organization_id = Column(PG_UUID(as_uuid=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    failed_login_attempts = Column(Integer, nullable=False, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    terms_accepted_at = Column(DateTime(timezone=True), nullable=True)
    privacy_accepted_at = Column(DateTime(timezone=True), nullable=True)
    activation_token = Column(String(255), nullable=True, index=True, unique=True)
    activation_token_expiry = Column(DateTime(timezone=True), nullable=True)
    totp_secret = Column(String(255), nullable=True)
    totp_enabled = Column(Boolean, nullable=False, default=False)
    password_reset_token = Column(String(255), nullable=True, index=True, unique=True)
    password_reset_token_expiry = Column(DateTime(timezone=True), nullable=True)
    token_version = Column(Integer, nullable=False, default=0)
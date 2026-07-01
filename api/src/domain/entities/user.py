from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID
from ..enums import UserRole

@dataclass
class User:
    id: UUID
    email: str
    hashed_password: str
    display_name: str
    role: UserRole
    is_active: bool = True
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    organization_ids: List[UUID] = field(default_factory=list)
    terms_accepted_at: Optional[datetime] = None
    privacy_accepted_at: Optional[datetime] = None
    activation_token: Optional[str] = None
    activation_token_expiry: Optional[datetime] = None
    totp_secret: Optional[str] = None
    totp_enabled: bool = False
    password_reset_token: Optional[str] = None
    password_reset_token_expiry: Optional[datetime] = None

    @property
    def organization_id(self) -> Optional[UUID]:
        return self.organization_ids[0] if self.organization_ids else None

    @organization_id.setter
    def organization_id(self, value: Optional[UUID]) -> None:
        # organization_ids only ever holds 0 or 1 elements in practice (the
        # user's active organization); this must replace it, not append, or
        # switching/reassigning the active org silently keeps the old value.
        self.organization_ids = [] if value is None else [value]


@dataclass
class UserMembership:
    id: UUID
    user_id: UUID
    organization_id: UUID
    role: UserRole
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
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

    @property
    def organization_id(self) -> Optional[UUID]:
        return self.organization_ids[0] if self.organization_ids else None

    @organization_id.setter
    def organization_id(self, value: Optional[UUID]) -> None:
        if value is None:
            self.organization_ids = []
        elif value not in self.organization_ids:
            self.organization_ids.append(value)


@dataclass
class UserMembership:
    id: UUID
    user_id: UUID
    organization_id: UUID
    role: UserRole
    joined_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
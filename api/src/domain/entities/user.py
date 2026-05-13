from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from ..enums import UserRole

@dataclass
class User:
    id: UUID
    email: str
    hashed_password: str
    role: UserRole
    organization_id: Optional[UUID]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
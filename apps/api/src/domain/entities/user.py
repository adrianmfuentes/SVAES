from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID
from .enums import UserRole

@dataclass
class User:
    """Core domain entity for authenticated users.

    Role determines permissions across all organization resources.
    organization_id is None for superadmins or users not yet assigned to a tenant.
    """
    id: UUID
    email: str
    hashed_password: str
    role: UserRole
    organization_id: Optional[UUID]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
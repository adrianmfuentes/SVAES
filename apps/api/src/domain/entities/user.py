from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID
from .enums import UserRole

@dataclass
class User:
    id: UUID
    email: str
    hashed_password: str
    role: UserRole
    organization_id: Optional[UUID]
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
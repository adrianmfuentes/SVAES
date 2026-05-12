from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID
from .enums import UserRole

@dataclass
class User:
    """Entity representing a user within the system. Each user has a unique identifier, email, hashed password, role, and an optional association 
    with an organization.

    Attributes:
        id (UUID): Unique identifier for the user.
        email (str): Email address of the user, used for authentication and communication.
        hashed_password (str): Hashed password for secure authentication.
        role (UserRole): Role of the user within the system (e.g., 'ADMIN', 'USER').
        organization_id (Optional[UUID]): Optional identifier of the organization the user belongs to, if any.
        created_at (datetime): Timestamp when the user was created.
        updated_at (datetime): Timestamp when the user was last updated.
    """
    id: UUID
    email: str
    hashed_password: str
    role: UserRole
    organization_id: Optional[UUID]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
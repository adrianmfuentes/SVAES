from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID
import uuid
from domain.enums import Permission


@dataclass
class CustomRole:
    organization_id: UUID
    name: str
    permissions: List[Permission]
    id: UUID = field(default_factory=uuid.uuid4)
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
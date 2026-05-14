from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID


@dataclass
class APIKey:
    id: UUID
    user_id: UUID
    organization_id: UUID
    name: str
    key_hash: str
    prefix: str
    is_active: bool
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
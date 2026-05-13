from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import uuid

@dataclass
class Organization:
    name: str
    slug: str
    owner_id: Optional[uuid.UUID] = None
    is_active: bool = True
    plan: str = "default"
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
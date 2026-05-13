from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid

@dataclass
class Project:
    organization_id: uuid.UUID
    name: str
    description: str
    profile_id: uuid.UUID
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
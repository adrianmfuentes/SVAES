from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
import uuid


@dataclass
class Template:
    organization_id: UUID
    name: str
    description: str
    profile_id: UUID
    created_by: UUID
    id: UUID = field(default_factory=uuid.uuid4)
    project_name_template: Optional[str] = None
    is_archived: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

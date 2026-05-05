from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
from .enums import ReleaseStatus

@dataclass
class Release:
    project_id: uuid.UUID
    profile_id: uuid.UUID
    version: str
    created_by: uuid.UUID
    description: str = ""
    status: ReleaseStatus = ReleaseStatus.BORRADOR
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
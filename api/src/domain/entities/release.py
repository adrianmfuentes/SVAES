from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import uuid
from ..enums import ReleaseStatus

@dataclass
class Release:
    name: str
    project_id: uuid.UUID
    profile_id: uuid.UUID
    version: str
    created_by: uuid.UUID
    description: str = ""
    status: ReleaseStatus = ReleaseStatus.BORRADOR
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    artifacts: list = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    organization_id: Optional[uuid.UUID] = None
    organization_name: Optional[str] = None
    project_name: Optional[str] = None
    pending_task_id: Optional[str] = None
    previous_status: Optional[ReleaseStatus] = None

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any
from uuid import UUID
import uuid


@dataclass
class NotificationChannel:
    organization_id: UUID
    channel_type: str
    enabled: bool
    config_data: Dict[str, Any] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

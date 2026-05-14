from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID
import uuid


@dataclass
class NotificationSubscription:
    user_id: UUID
    event_type: str
    enabled: bool = True
    id: UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

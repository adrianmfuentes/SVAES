from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import uuid
from domain.enums import AccessRequestStatus


@dataclass
class AccessRequest:
    requester_name: str
    requester_email: str
    organization_name: str
    status: AccessRequestStatus = AccessRequestStatus.PENDING
    organization_description: Optional[str] = None
    slug_preview: Optional[str] = None
    rejection_reason: Optional[str] = None
    reviewed_by: Optional[uuid.UUID] = None
    reviewed_at: Optional[datetime] = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

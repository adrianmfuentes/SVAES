from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from ..enums import ConnectorStatus

@dataclass
class ConnectorInstance:
    id: UUID
    organization_id: UUID
    connector_type: str
    name: str
    encrypted_credentials: bytes
    status: ConnectorStatus
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_tested_at: Optional[datetime] = None
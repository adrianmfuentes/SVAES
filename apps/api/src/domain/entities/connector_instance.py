from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID
from .enums import ConnectorStatus

@dataclass
class ConnectorInstance:
    id: UUID
    organization_id: UUID
    connector_type: str
    encrypted_credentials: bytes
    status: ConnectorStatus
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID
from .enums import ConnectorStatus

@dataclass
class ConnectorInstance:
    """A configured and persisted connection to an external tool (e.g., Jira, GitHub, GitLab).

    Credentials are stored encrypted. Status reflects the last known connection health.
    """
    id: UUID
    organization_id: UUID
    connector_type: str
    encrypted_credentials: bytes
    status: ConnectorStatus
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
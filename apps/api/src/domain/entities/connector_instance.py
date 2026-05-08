from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID
from .enums import ConnectorStatus

@dataclass
class ConnectorInstance:
    """Entity representing an instance of an external connector integrated with the system. Each connector instance is associated with a specific 
    organization and has its own encrypted credentials for authentication with the external system. 
    The status field indicates whether the connector is active, inactive, or has encountered an error.

    Attributes:
        id (UUID): Unique identifier for the connector instance.
        organization_id (UUID): Identifier of the organization this connector instance belongs to.
        connector_type (str): Type of the connector (e.g., 'jira', 'github', 'confluence').
        encrypted_credentials (bytes): Encrypted credentials for authenticating with the external system.
        status (ConnectorStatus): Current status of the connector instance.
        created_at (datetime): Timestamp when the connector instance was created.
        updated_at (datetime): Timestamp when the connector instance was last updated.
    """
    id: UUID
    organization_id: UUID
    connector_type: str
    encrypted_credentials: bytes
    status: ConnectorStatus
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
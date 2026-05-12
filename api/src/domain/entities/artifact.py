from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid

@dataclass
class Artifact:
    """Entity representing a raw artifact fetched from an external connector. 
    This is the foundational data structure that will be processed and transformed into structured events for the event store.

    Attributes:
        id (uuid.UUID): Unique identifier for the artifact.
        release_id (uuid.UUID): Identifier of the release this artifact is associated with.
        connector_instance_id (uuid.UUID): Identifier of the connector instance that fetched this artifact.
        artifact_type (str): Type of the artifact (e.g., 'task', 'commit', 'doc').
        external_ref (str): External reference or ID from the source system.
        metadata (dict): Additional metadata about the artifact, stored as JSONB in the database.
        created_at (datetime): Timestamp when the artifact was created.
    """
    release_id: uuid.UUID
    connector_instance_id: uuid.UUID
    artifact_type: str  # e.g., 'task', 'commit', 'doc'
    external_ref: str
    metadata: dict = field(default_factory=dict) # JSONB en DB
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
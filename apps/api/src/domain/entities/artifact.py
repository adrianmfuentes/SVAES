from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid

@dataclass
class Artifact:
    """Raw data object fetched from an external connector and associated with a release for verification."""
    release_id: uuid.UUID
    connector_instance_id: uuid.UUID
    artifact_type: str  # e.g., 'task', 'commit', 'doc'
    external_ref: str
    metadata: dict = field(default_factory=dict) # JSONB en DB
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
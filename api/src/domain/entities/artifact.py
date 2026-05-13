from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid

@dataclass
class Artifact:
    release_id: uuid.UUID
    connector_instance_id: uuid.UUID
    connector_implementation: str
    artifact_type: str
    external_ref: str
    metadata: dict = field(default_factory=dict)
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
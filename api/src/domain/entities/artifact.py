from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid

@dataclass
class Artifact:
    release_id: uuid.UUID                                                                           # ID del release al que pertenece el artifact
    connector_instance_id: uuid.UUID                                                                # ID de la instancia del conector que generó el artifact
    artifact_type: str                                                                              # E.j., 'task', 'commit', 'doc'
    external_ref: str                                                                               # Referencia externa al artifact 
    metadata: dict = field(default_factory=dict)                                                    #  JSONB en DB
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
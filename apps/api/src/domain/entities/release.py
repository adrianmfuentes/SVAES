from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
from .enums import ReleaseStatus

@dataclass
class Release:
    """Central aggregate tracking a versioned software delivery submitted for verification.

    Progresses through a state machine: BORRADOR → PENDIENTE → EN_VERIFICACION → COMPLETADA.
    """
    project_id: uuid.UUID
    profile_id: uuid.UUID
    version: str
    created_by: uuid.UUID
    description: str = ""
    status: ReleaseStatus = ReleaseStatus.BORRADOR
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
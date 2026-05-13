from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
from ..enums import ReleaseStatus

@dataclass
class Release:
    name: str
    project_id: uuid.UUID                                                                       # Referencia al proyecto al que pertenece el release
    profile_id: uuid.UUID                                                                       # Referencia al perfil de verificación asociado al release
    version: str
    created_by: uuid.UUID
    description: str = ""
    status: ReleaseStatus = ReleaseStatus.BORRADOR
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    artifacts: list = field(default_factory=list)                                               # Lista de artifacts asociados al release
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

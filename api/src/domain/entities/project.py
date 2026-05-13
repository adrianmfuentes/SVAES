from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid

@dataclass
class Project:
    organization_id: uuid.UUID # Referencia a la organización a la que pertenece el proyecto
    name: str
    description: str
    profile_id: uuid.UUID # Referencia al perfil de verificación por defecto del proyecto
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
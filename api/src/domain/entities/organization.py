from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid

@dataclass
class Organization:
    name: str
    slug: str
    is_active: bool = True
    plan: str = "default"
    id: uuid.UUID = field(default_factory=uuid.uuid4) # Genera un UUID automáticamente al crear una nueva organización
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
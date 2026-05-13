from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import uuid

from ..enums import SeverityType


@dataclass
class VerificationRule:
    profile_id: uuid.UUID # Referencia al perfil de verificación al que pertenece la regla
    rule_template: str
    severity: SeverityType = SeverityType.HIGH
    params: dict = field(default_factory=dict) # Parámetros para cada regla
    connector_instance_id: Optional[uuid.UUID] = None
    display_order: int = 0
    is_active: bool = True
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
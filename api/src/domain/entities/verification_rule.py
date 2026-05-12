import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class VerificationRule:
    profile_id: uuid.UUID
    rule_template: str             # RV-01 .. RV-10
    severity: str = "OBLIGATORIA"  # OBLIGATORIA | RECOMENDADA | INFORMATIVA
    params: dict = field(default_factory=dict)
    connector_instance_id: Optional[uuid.UUID] = None
    display_order: int = 0
    is_active: bool = True
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
from ..enums import VerdictType

@dataclass
class VerificationResult:
    release_id: uuid.UUID
    verdict: VerdictType
    duration_ms: int
    rule_results: dict = field(default_factory=dict)  # Detalle por regla
    profile_snapshot: dict = field(default_factory=dict) # Trazabilidad histórica
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
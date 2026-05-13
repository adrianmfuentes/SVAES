from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
from ..enums import VerdictType

@dataclass
class VerificationResult:
    release_id: uuid.UUID
    verdict: VerdictType
    rule_results: list = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    profile_snapshot: dict = field(default_factory=dict)
    duration_ms: int = 0
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
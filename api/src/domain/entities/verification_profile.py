from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID
from domain.entities.verification_rule import VerificationRule

@dataclass
class VerificationProfile:
    id: UUID
    organization_id: UUID
    name: str
    rules: list[VerificationRule] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID
from domain.entities.verification_rule import VerificationRule

@dataclass
class VerificationProfile:
    id: UUID
    organization_id: UUID
    name: str
    rules: list[VerificationRule] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
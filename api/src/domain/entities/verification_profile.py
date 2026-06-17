from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from domain.entities.verification_rule import VerificationRule

@dataclass
class VerificationProfile:
    id: UUID
    organization_id: Optional[UUID]
    name: str
    description: str = ""
    is_default: bool = False
    is_system: bool = False
    rules: list[VerificationRule] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

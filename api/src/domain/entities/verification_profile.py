from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID
from domain.entities.verification_rule import VerificationRule

@dataclass
class VerificationProfile:
    """Entity representing a verification profile within the system. A verification profile is associated with a specific organization and contains
    information about the profile's name, rules, and timestamps for creation and updates.

    Attributes:
        id (UUID): Unique identifier for the verification profile.
        organization_id (UUID): Identifier of the organization this verification profile belongs to.
        name (str): Name of the verification profile.
        rules (list[VerificationRule]): List of verification rules associated with this profile.
        created_at (datetime): Timestamp when the verification profile was created.
        updated_at (datetime): Timestamp when the verification profile was last updated.
    """
    id: UUID
    organization_id: UUID
    name: str
    rules: list[VerificationRule] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid

@dataclass
class Organization:
    """Tenant root aggregate. All resources (projects, connectors, profiles) are scoped to an organization."""
    name: str
    slug: str
    is_active: bool = True
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
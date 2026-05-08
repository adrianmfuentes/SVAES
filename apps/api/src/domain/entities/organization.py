from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid

@dataclass
class Organization:
    """Entity representing an organization within the system. Each organization can have multiple connector instances associated with it, 
    allowing for integration with various external systems. The organization entity serves as a central point for managing these connectors and 
    their related artifacts. 

    Attributes:
        id (uuid.UUID): Unique identifier for the organization.
        name (str): Name of the organization.
        slug (str): URL-friendly slug for the organization, used for routing and identification.
        is_active (bool): Flag indicating whether the organization is active or not.
        created_at (datetime): Timestamp when the organization was created.
        updated_at (datetime): Timestamp when the organization was last updated.
    """
    name: str
    slug: str
    is_active: bool = True
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
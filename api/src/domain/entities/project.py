from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid

@dataclass
class Project:
    """Entity representing a project within the system. Each project is associated with a specific organization and contains information about 
    the project's name, description, and timestamps for creation and updates.

    Attributes:
        organization_id (uuid.UUID): Identifier of the organization this project belongs to.
        name (str): Name of the project.
        description (str): Description of the project.
        id (uuid.UUID): Unique identifier for the project.
        created_at (datetime): Timestamp when the project was created.
        updated_at (datetime): Timestamp when the project was last updated.
    """
    organization_id: uuid.UUID
    name: str
    description: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
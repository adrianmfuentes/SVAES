from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
from .enums import ReleaseStatus

@dataclass
class Release:
    """Entity representing a release within the system. A release is associated with a specific project and profile, and it contains information 
    about the version, description, and status of the release.
    
    Attributes:
        project_id (uuid.UUID): Identifier of the project this release belongs to.
        profile_id (uuid.UUID): Identifier of the profile associated with this release.
        version (str): Version string for the release (e.g., '1.0.0').
        created_by (uuid.UUID): Identifier of the user who created the release.
        description (str): Optional description of the release.
        status (ReleaseStatus): Current status of the release (e.g., 'BORRADOR', 'PUBLICADO').
        id (uuid.UUID): Unique identifier for the release.
    """
    project_id: uuid.UUID
    profile_id: uuid.UUID
    version: str
    created_by: uuid.UUID
    description: str = ""
    status: ReleaseStatus = ReleaseStatus.BORRADOR
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
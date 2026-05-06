from pydantic import BaseModel
import uuid
from datetime import datetime
from domain.entities.enums import ReleaseStatus

class ReleaseResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    profile_id: uuid.UUID
    version: str
    status: ReleaseStatus
    description: str
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}

class VerificationTaskResponse(BaseModel):
    """Response returned when a verification task is accepted and enqueued."""
    message: str
    task_id: str

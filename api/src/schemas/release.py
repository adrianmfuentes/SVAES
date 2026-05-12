import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from domain.entities.enums import ReleaseStatus


class ReleaseCreate(BaseModel):
    project_id: uuid.UUID
    profile_id: uuid.UUID
    version: str = Field(..., min_length=1, max_length=50)
    description: str = Field(default="", max_length=1000)


class ReleaseUpdate(BaseModel):
    description: str | None = Field(None, max_length=1000)


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
    message: str
    task_id: str

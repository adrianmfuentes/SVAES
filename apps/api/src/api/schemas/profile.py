import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ProfileCreate(BaseModel):
    organization_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=120)


class ProfileUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)


class ProfileResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}

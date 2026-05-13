import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


ALLOWED_ARTIFACT_TYPES = {"TAREA", "CODIGO", "DOCUMENTO", "PRUEBA", "INCIDENTE"}


class ArtifactCreateRequest(BaseModel):
    artifact_type: str = Field(..., description="TAREA | CODIGO | DOCUMENTO | PRUEBA | INCIDENTE")
    external_ref: str = Field(..., min_length=1, max_length=512)
    connector_instance_id: Optional[uuid.UUID] = None
    metadata: dict = Field(default_factory=dict)

    @field_validator("artifact_type")
    @classmethod
    def validate_artifact_type(cls, v: str) -> str:
        if v not in ALLOWED_ARTIFACT_TYPES:
            raise ValueError(f"artifact_type must be one of {sorted(ALLOWED_ARTIFACT_TYPES)}")
        return v


class ArtifactResponse(BaseModel):
    id: uuid.UUID
    release_id: uuid.UUID
    connector_instance_id: Optional[uuid.UUID] = None
    artifact_type: str
    external_ref: str
    metadata: dict
    created_at: datetime

    model_config = {"from_attributes": True}

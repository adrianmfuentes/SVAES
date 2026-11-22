from uuid import UUID
from pydantic import BaseModel, ConfigDict
from typing import Optional
from shared.domain.enums import ArtifactType


RELEASE_NOT_FOUND = "Release no encontrada"


class ArtifactCreateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    artifact_type: ArtifactType
    connector_instance_id: UUID
    connector_implementation: str
    external_ref: str
    description: str = ""
    metadata: Optional[dict] = None

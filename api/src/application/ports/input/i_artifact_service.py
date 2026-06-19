from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from domain.entities.artifact import Artifact
from domain.enums import ArtifactType


class IArtifactService(ABC):
    @abstractmethod
    async def list_artifacts(self, release_id: UUID) -> List[Artifact]:
        pass

    @abstractmethod
    async def add_artifact(
        self,
        release_id: UUID,
        connector_instance_id: UUID,
        connector_implementation: str,
        artifact_type: ArtifactType,
        external_ref: str,
        description: str = "",
        metadata: Optional[dict] = None,
    ) -> Artifact:
        pass

    @abstractmethod
    async def remove_artifact(self, release_id: UUID, artifact_id: UUID) -> None:
        pass
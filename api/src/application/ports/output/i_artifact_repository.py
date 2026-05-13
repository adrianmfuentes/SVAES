from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID
from domain.entities.artifact import Artifact

class IArtifactRepository(ABC):
    @abstractmethod
    async def save(self, artifact: Artifact) -> Artifact:
        pass

    @abstractmethod
    async def find_by_id(self, artifact_id: UUID) -> Optional[Artifact]:
        pass

    @abstractmethod
    async def find_by_release(self, release_id: UUID, skip: int = 0, limit: int = 100) -> List[Artifact]:
        pass

    @abstractmethod
    async def delete(self, artifact_id: UUID) -> None:
        pass

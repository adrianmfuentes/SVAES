from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID
from domain.entities.artifact import Artifact


class IArtifactRepository(ABC):
    """Outbound port for persisting raw artifacts fetched from external connectors."""

    @abstractmethod
    def save(self, artifact: Artifact) -> Artifact:
        pass

    @abstractmethod
    def find_by_id(self, artifact_id: UUID) -> Optional[Artifact]:
        pass

    @abstractmethod
    def find_by_release(self, release_id: UUID) -> List[Artifact]:
        pass

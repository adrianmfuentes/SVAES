from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID
from domain.entities.artifact import Artifact


class IArtifactRepository(ABC):
    """Outbound port for managing artifacts associated with releases. This repository interface abstracts 
    the persistence mechanism for artifacts, allowing the application layer to interact with artifact data without 
    being coupled to a specific database or storage solution.

    Methods:
        save(artifact: Artifact) -> Artifact: Saves an artifact to the repository and returns the saved instance.
        find_by_id(artifact_id: UUID) -> Optional[Artifact]: Retrieves an artifact by its unique identifier, returning None if not found.
        find_by_release(release_id: UUID) -> List[Artifact]: Retrieves all artifacts associated with a specific release.
    """
    @abstractmethod
    def save(self, artifact: Artifact) -> Artifact:
        pass

    @abstractmethod
    def find_by_id(self, artifact_id: UUID) -> Optional[Artifact]:
        pass

    @abstractmethod
    def find_by_release(self, release_id: UUID) -> List[Artifact]:
        pass

from abc import ABC, abstractmethod
from typing import Optional, List
import uuid
from domain.entities.release import Release

class IReleaseRepository(ABC):
    """Outbound port for managing Release entities in the data store. This interface defines the contract for persisting, retrieving, listing, and updating
    release data, abstracting away the underlying database or storage mechanism. Implementations of this interface can use SQL databases, NoSQL databases,
    or any other form of storage, while the application layer interacts with it through these defined methods.

    Methods:
        create(release: Release) -> Release: Persists a new release and returns the created entity.
        get_by_id(release_id: uuid.UUID) -> Optional[Release]: Retrieves a release by its unique identifier, or returns None if not found.
        list_by_project(project_id: uuid.UUID) -> List[Release]: Returns a list of releases associated with a given project.
        update(release: Release) -> Release: Updates the state or other fields of the release.
    """
    @abstractmethod
    async def create(self, release: Release) -> Release:
        pass

    @abstractmethod
    async def get_by_id(self, release_id: uuid.UUID) -> Optional[Release]:
        pass

    @abstractmethod
    async def list_by_project(self, project_id: uuid.UUID) -> List[Release]:
        pass

    @abstractmethod
    async def update(self, release: Release) -> Release:
        pass

    @abstractmethod
    async def delete(self, release_id: uuid.UUID) -> None:
        pass
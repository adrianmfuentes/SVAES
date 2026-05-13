from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID
from domain.entities.project import Project


class IProjectRepository(ABC):
    """Outbound port for managing Project entities in the data store. This interface defines the contract for persisting, retrieving, and listing
    project data, abstracting away the underlying database or storage mechanism. Implementations of this interface can use SQL databases, NoSQL databases,
    or any other form of storage, while the application layer interacts with it through these defined methods.
    
    Methods:
        create(project: Project) -> Project: Persists a new project and returns the created entity.
        get_by_id(project_id: UUID) -> Optional[Project]: Retrieves a project by its unique identifier, or returns None if not found.
        list_by_organization(organization_id: UUID) -> List[Project]: Returns a list of projects associated with a given organization.
    """
    @abstractmethod
    async def create(self, project: Project) -> Project:
        pass

    @abstractmethod
    async def get_by_id(self, project_id: UUID) -> Optional[Project]:
        pass

    @abstractmethod
    async def list_by_organization(self, organization_id: UUID, skip: int = 0, limit: int = 50) -> List[Project]:
        pass

    @abstractmethod
    async def update(self, project: Project) -> Project:
        pass

    @abstractmethod
    async def delete(self, project_id: UUID) -> None:
        pass

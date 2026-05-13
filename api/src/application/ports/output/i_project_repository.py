from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID
from domain.entities.project import Project

class IProjectRepository(ABC):
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

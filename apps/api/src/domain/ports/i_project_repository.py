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
    async def list_by_organization(self, organization_id: UUID) -> List[Project]:
        pass

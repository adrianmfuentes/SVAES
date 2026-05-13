from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from domain.entities.organization import Organization
from domain.entities.project import Project


class IOrganizationService(ABC):
    @abstractmethod
    async def create_organization(
        self,
        name: str,
        slug: str,
        plan: str = "default",
        owner_id: Optional[UUID] = None,
    ) -> Organization:
        pass

    @abstractmethod
    async def get_organization(self, organization_id: UUID) -> Optional[Organization]:
        pass

    @abstractmethod
    async def list_organizations(
        self,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = True,
    ) -> List[Organization]:
        pass

    @abstractmethod
    async def create_project(
        self,
        organization_id: UUID,
        name: str,
        description: str,
        profile_id: UUID,
    ) -> Project:
        pass

    @abstractmethod
    async def list_projects(
        self,
        organization_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Project]:
        pass

    @abstractmethod
    async def get_project(self, project_id: UUID) -> Optional[Project]:
        pass

    @abstractmethod
    async def transfer_ownership(
        self,
        organization_id: UUID,
        new_owner_id: UUID,
    ) -> Organization:
        pass
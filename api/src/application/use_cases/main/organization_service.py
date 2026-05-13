from typing import List, Optional
from uuid import UUID
from application.ports.input.i_organization_service import IOrganizationService
from application.ports.output.i_organization_repository import IOrganizationRepository
from application.ports.output.i_project_repository import IProjectRepository
from domain.entities.organization import Organization
from domain.entities.project import Project
from domain.exceptions import DuplicateEntityError, EntityNotFoundError, ValidationError


class OrganizationService(IOrganizationService):
    def __init__(
        self,
        organization_repository: IOrganizationRepository,
        project_repository: IProjectRepository,
    ) -> None:
        self._org_repo = organization_repository
        self._project_repo = project_repository


    async def create_organization(
        self,
        name: str,
        slug: str,
        plan: str = "default",
        owner_id: Optional[UUID] = None,
    ) -> Organization:
        existing = await self._org_repo.get_by_slug(slug)
        if existing:
            raise DuplicateEntityError(f"Ya existe una organización con slug: {slug}")

        org = Organization(name=name, slug=slug, owner_id=owner_id, plan=plan)
        return await self._org_repo.create(org)


    async def get_organization(self, organization_id: UUID) -> Optional[Organization]:
        return await self._org_repo.get_by_id(organization_id)


    async def list_organizations(
        self,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = True,
    ) -> List[Organization]:
        return await self._org_repo.list_all(active_only=active_only, skip=skip, limit=limit)


    async def create_project(
        self,
        organization_id: UUID,
        name: str,
        description: str,
        profile_id: UUID,
    ) -> Project:
        org = await self._org_repo.get_by_id(organization_id)
        if not org:
            raise EntityNotFoundError(f"Organización no encontrada: {organization_id}")

        project = Project(
            organization_id=organization_id,
            name=name,
            description=description,
            profile_id=profile_id,
        )
        return await self._project_repo.create(project)


    async def list_projects(
        self,
        organization_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Project]:
        return await self._project_repo.list_by_organization(organization_id, skip=skip, limit=limit)


    async def get_project(self, project_id: UUID) -> Optional[Project]:
        return await self._project_repo.get_by_id(project_id)


    async def transfer_ownership(
        self,
        organization_id: UUID,
        new_owner_id: UUID,
    ) -> Organization:
        org = await self._org_repo.get_by_id(organization_id)
        if not org:
            raise EntityNotFoundError(f"Organización no encontrada: {organization_id}")

        org.owner_id = new_owner_id
        return await self._org_repo.update(org)
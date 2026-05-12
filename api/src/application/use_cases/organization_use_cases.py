import uuid
from dataclasses import dataclass
from typing import List, Optional

from domain.entities.organization import Organization
from domain.exceptions import EntityNotFoundError
from domain.ports.i_organization_repository import IOrganizationRepository


@dataclass
class CreateOrganizationCommand:
    name: str
    slug: str
    plan: str = "free"


@dataclass
class UpdateOrganizationCommand:
    organization_id: uuid.UUID
    name: str | None = None
    slug: str | None = None
    is_active: bool | None = None


class CreateOrganizationUseCase:
    def __init__(self, org_repo: IOrganizationRepository):
        self.org_repo = org_repo

    async def execute(self, command: CreateOrganizationCommand) -> Organization:
        org = Organization(name=command.name, slug=command.slug)
        return await self.org_repo.create(org)


class GetOrganizationUseCase:
    def __init__(self, org_repo: IOrganizationRepository):
        self.org_repo = org_repo

    async def execute(self, organization_id: uuid.UUID) -> Organization:
        org = await self.org_repo.get_by_id(organization_id)
        if not org:
            raise EntityNotFoundError(f"Organization {organization_id} not found")
        return org


class ListOrganizationsUseCase:
    def __init__(self, org_repo: IOrganizationRepository):
        self.org_repo = org_repo

    async def execute(self, skip: int = 0, limit: int = 100) -> List[Organization]:
        return await self.org_repo.list_all(active_only=True, skip=skip, limit=limit)


class UpdateOrganizationUseCase:
    def __init__(self, org_repo: IOrganizationRepository):
        self.org_repo = org_repo

    async def execute(self, command: UpdateOrganizationCommand) -> Organization:
        org = await self.org_repo.get_by_id(command.organization_id)
        if not org:
            raise EntityNotFoundError(f"Organization {command.organization_id} not found")

        if command.name is not None:
            org.name = command.name
        if command.slug is not None:
            org.slug = command.slug
        if command.is_active is not None:
            org.is_active = command.is_active

        return await self.org_repo.update(org)


class DeleteOrganizationUseCase:
    def __init__(self, org_repo: IOrganizationRepository):
        self.org_repo = org_repo

    async def execute(self, organization_id: uuid.UUID) -> None:
        org = await self.org_repo.get_by_id(organization_id)
        if not org:
            raise EntityNotFoundError(f"Organization {organization_id} not found")
        org.is_active = False
        await self.org_repo.update(org)

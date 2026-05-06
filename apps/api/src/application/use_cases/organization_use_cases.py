from dataclasses import dataclass
from typing import List
from domain.entities.organization import Organization
from domain.ports.i_organization_repository import IOrganizationRepository


@dataclass
class CreateOrganizationCommand:
    name: str
    slug: str
    plan: str = "free"


class CreateOrganizationUseCase:
    """Creates a new tenant organization. Slug must be unique across the system."""

    def __init__(self, org_repo: IOrganizationRepository):
        self.org_repo = org_repo

    async def execute(self, command: CreateOrganizationCommand) -> Organization:
        org = Organization(name=command.name, slug=command.slug)
        return await self.org_repo.create(org)


class ListOrganizationsUseCase:
    def __init__(self, org_repo: IOrganizationRepository):
        self.org_repo = org_repo

    async def execute(self) -> List[Organization]:
        return await self.org_repo.list_all(active_only=True)

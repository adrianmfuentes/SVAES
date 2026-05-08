from dataclasses import dataclass
from typing import List
from domain.entities.organization import Organization
from domain.ports.i_organization_repository import IOrganizationRepository


@dataclass
class CreateOrganizationCommand:
    """Command object for creating a new tenant organization. Slug must be unique across the system."""
    name: str
    slug: str
    plan: str = "free"


class CreateOrganizationUseCase:
    """Use case for creating a new tenant organization. 
    
    Attributes:
        org_repo (IOrganizationRepository): Repository for managing organization entities.
    """

    def __init__(self, org_repo: IOrganizationRepository):
        self.org_repo = org_repo

    async def execute(self, command: CreateOrganizationCommand) -> Organization:
        org = Organization(name=command.name, slug=command.slug)
        return await self.org_repo.create(org)


class ListOrganizationsUseCase:
    """Use case for listing all active tenant organizations. This is typically used for administrative purposes.

    Attributes:
        org_repo (IOrganizationRepository): Repository for managing organization entities.
    """
    def __init__(self, org_repo: IOrganizationRepository):
        self.org_repo = org_repo

    async def execute(self) -> List[Organization]:
        return await self.org_repo.list_all(active_only=True)

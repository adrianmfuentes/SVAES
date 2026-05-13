from uuid import UUID
from application.ports.output.i_organization_repository import IOrganizationRepository
from domain.entities.organization import Organization
from domain.exceptions import DuplicateEntityError


class CreateOrganizationUseCase:
    def __init__(self, organization_repository: IOrganizationRepository) -> None:
        self._org_repo = organization_repository

    async def execute(self, name: str, slug: str, plan: str = "default") -> Organization:
        existing = await self._org_repo.get_by_slug(slug)
        if existing:
            raise DuplicateEntityError(f"Ya existe una organización con slug: {slug}")

        org = Organization(name=name, slug=slug, plan=plan)
        return await self._org_repo.create(org)
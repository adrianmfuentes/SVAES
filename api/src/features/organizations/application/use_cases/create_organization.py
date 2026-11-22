from uuid import UUID

from features.organizations.application.ports.i_organization_service import IOrganizationService
from features.organizations.domain.organization import Organization
from shared.application.i_unit_of_work import IUnitOfWork


class CreateOrganization:
    def __init__(self, organizations: IOrganizationService, unit_of_work: IUnitOfWork) -> None:
        self._organizations = organizations
        self._unit_of_work = unit_of_work

    async def execute(self, name: str, slug: str, owner_id: UUID) -> Organization:
        async with self._unit_of_work.transaction():
            return await self._organizations.create_organization(name, slug, owner_id)

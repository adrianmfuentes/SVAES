from uuid import UUID
from application.ports.output.i_organization_repository import IOrganizationRepository
from domain.entities.organization import Organization
from domain.exceptions import DuplicateEntityError

"""
Este módulo define el caso de uso para crear una nueva organización, que es responsable de validar que no exista una organización con el mismo slug y
crear una nueva organización en el sistema. Incluye la lógica de negocio para verificar que el slug es único y lanzar una excepción si ya existe una organización
con el mismo slug. Si la creación es exitosa, se devuelve la nueva organización creada.
"""
class CreateOrganizationUseCase:
    def __init__(self, organization_repository: IOrganizationRepository) -> None:
        self._org_repo = organization_repository

    async def execute(self, name: str, slug: str, plan: str = "default") -> Organization:
        existing = await self._org_repo.get_by_slug(slug)
        if existing:
            raise DuplicateEntityError(f"Ya existe una organización con slug: {slug}")

        org = Organization(name=name, slug=slug, plan=plan)
        return await self._org_repo.create(org)
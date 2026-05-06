import uuid
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from domain.ports.i_organization_repository import IOrganizationRepository
from domain.entities.organization import Organization
from infrastructure.database.models.organization import OrganizationModel


class SQLOrganizationRepository(IOrganizationRepository):
    """
    Implementación en SQLAlchemy del puerto IOrganizationRepository.
    Maneja la traducción entre modelos de BD y entidades de dominio puras.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_domain(self, model: OrganizationModel) -> Organization:
        """Convierte el modelo de BD a la Entidad de Dominio pura."""
        return Organization(
            id=model.id,
            name=model.name,
            slug=model.slug,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at
        )

    async def create(self, organization: Organization) -> Organization:
        """Guarda una nueva organización en Postgres."""
        model = OrganizationModel(
            id=organization.id,
            name=organization.name,
            slug=organization.slug,
            is_active=organization.is_active,
            created_at=organization.created_at,
            updated_at=organization.updated_at
        )
        self.session.add(model)
        await self.session.commit()
        # Refrescamos para obtener posibles campos autogenerados por Postgres
        await self.session.refresh(model) 
        return self._to_domain(model)

    async def get_by_id(self, organization_id: uuid.UUID) -> Optional[Organization]:
        """Busca una organización por ID."""
        query = select(OrganizationModel).where(OrganizationModel.id == organization_id)
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        
        if model:
            return self._to_domain(model)
        return None

    async def get_by_slug(self, slug: str) -> Optional[Organization]:
        """Busca una organización por su slug único."""
        query = select(OrganizationModel).where(OrganizationModel.slug == slug)
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        
        if model:
            return self._to_domain(model)
        return None

    async def list_all(self, active_only: bool = True) -> List[Organization]:
        """Lista las organizaciones, filtrando opcionalmente por las activas."""
        query = select(OrganizationModel)
        if active_only:
            query = query.where(OrganizationModel.is_active == True)
            
        result = await self.session.execute(query)
        models = result.scalars().all()
        
        return [self._to_domain(m) for m in models]

    async def update(self, organization: Organization) -> Organization:
        """Actualiza los datos de una organización existente."""
        query = select(OrganizationModel).where(OrganizationModel.id == organization.id)
        result = await self.session.execute(query)
        model = result.scalar_one()

        # Actualizamos los campos mutables
        model.name = organization.name
        model.is_active = organization.is_active
        model.updated_at = organization.updated_at

        await self.session.commit()
        await self.session.refresh(model)
        return self._to_domain(model)
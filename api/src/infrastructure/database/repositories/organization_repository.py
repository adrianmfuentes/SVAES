from uuid import UUID
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from domain.entities.organization import Organization
from domain.ports.i_organization_repository import IOrganizationRepository
from infrastructure.database.models.organization import OrganizationModel

class SqlOrganizationRepository(IOrganizationRepository):
    """Async SQLAlchemy adapter for IOrganizationRepository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, organization: Organization) -> Organization:
        model = OrganizationModel(
            id=organization.id,
            name=organization.name,
            slug=organization.slug,
            is_active=organization.is_active,
        )
        self.session.add(model)
        await self.session.flush()
        return organization

    async def get_by_id(self, organization_id: UUID) -> Optional[Organization]:
        model = await self.session.get(OrganizationModel, organization_id)
        return self._to_entity(model) if model else None

    async def get_by_slug(self, slug: str) -> Optional[Organization]:
        result = await self.session.execute(
            select(OrganizationModel).where(OrganizationModel.slug == slug)
        )
        model = result.scalars().first()
        return self._to_entity(model) if model else None

    async def list_all(
        self,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Organization]:
        stmt = select(OrganizationModel)
        if active_only:
            stmt = stmt.where(OrganizationModel.is_active.is_(True))
        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def update(self, organization: Organization) -> Organization:
        model = await self.session.get(OrganizationModel, organization.id)
        if model:
            model.name = organization.name
            model.slug = organization.slug
            model.is_active = organization.is_active
            await self.session.flush()
        return organization

    def _to_entity(self, model: OrganizationModel) -> Organization:
        return Organization(
            id=model.id,
            name=model.name,
            slug=model.slug,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

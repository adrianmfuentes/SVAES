from sqlalchemy.future import select
from typing import Optional, List, cast
import uuid
from datetime import datetime
from application.ports.output.i_organization_repository import IOrganizationRepository
from domain.entities.organization import Organization
from infrastructure.secondary.database.models.organization_model import OrganizationModel
from infrastructure.secondary.database.get_async_session import AsyncSessionLocal


class SqlOrganizationRepository(IOrganizationRepository):
    def _model_to_entity(self, row: OrganizationModel) -> Organization:
        return Organization(
            id=cast(uuid.UUID, row.id),
            name=cast(str, row.name),
            slug=cast(str, row.slug),
            owner_id=cast(uuid.UUID | None, row.owner_id),
            is_active=cast(bool, row.is_active),
            created_at=cast(datetime, row.created_at),
            updated_at=cast(datetime, row.updated_at),
        )

    async def create(self, organization: Organization) -> Organization:
        async with AsyncSessionLocal() as session:
            org_model = OrganizationModel(
                id=organization.id,
                name=organization.name,
                slug=organization.slug,
                owner_id=organization.owner_id,
                is_active=organization.is_active,
                created_at=organization.created_at,
                updated_at=organization.updated_at,
            )
            session.add(org_model)
            await session.commit()
            await session.refresh(org_model)

            return self._model_to_entity(org_model)

    async def get_by_id(self, organization_id: uuid.UUID) -> Optional[Organization]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(OrganizationModel).where(OrganizationModel.id == organization_id))
            org_row = result.scalar_one_or_none()
            if not org_row:
                return None

            return self._model_to_entity(org_row)

    async def get_by_slug(self, slug: str) -> Optional[Organization]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(OrganizationModel).where(OrganizationModel.slug == slug))
            org_row = result.scalar_one_or_none()
            if not org_row:
                return None

            return self._model_to_entity(org_row)

    async def list_all(self, active_only: bool = True, skip: int = 0, limit: int = 100) -> List[Organization]:
        async with AsyncSessionLocal() as session:
            query = select(OrganizationModel)
            if active_only:
                query = query.where(OrganizationModel.is_active == True)
            query = query.offset(skip).limit(limit)

            result = await session.execute(query)
            org_rows = result.scalars().all()

            return [self._model_to_entity(row) for row in org_rows]

    async def update(self, organization: Organization) -> Organization:
        async with AsyncSessionLocal() as session:
            org_model = await session.get(OrganizationModel, organization.id)
            if not org_model:
                raise ValueError("Organization not found")

            org_model.name = organization.name  # pyright: ignore[reportAttributeAccessIssue]
            org_model.slug = organization.slug  # pyright: ignore[reportAttributeAccessIssue]
            org_model.owner_id = organization.owner_id  # pyright: ignore[reportAttributeAccessIssue]
            org_model.is_active = organization.is_active  # pyright: ignore[reportAttributeAccessIssue]
            org_model.updated_at = datetime.now(datetime.timezone.utc)

            await session.commit()
            await session.refresh(org_model)

            return self._model_to_entity(org_model)
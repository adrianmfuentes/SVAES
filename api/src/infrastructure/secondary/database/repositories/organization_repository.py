from sqlalchemy.future import select
from typing import Optional, List
import uuid
from datetime import datetime
from application.ports.output.i_organization_repository import IOrganizationRepository
from domain.entities.organization import Organization
from infrastructure.secondary.database.models.organization_model import OrganizationModel
from infrastructure.secondary.database.get_async_session import get_async_session


class SqlOrganizationRepository(IOrganizationRepository):
    def _model_to_entity(self, row: OrganizationModel) -> Organization:
        return Organization(
            id=row.id,
            name=row.name,
            slug=row.slug,
            owner_id=row.owner_id,
            is_active=row.is_active,
            plan=row.plan,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def create(self, organization: Organization) -> Organization:
        session = await get_async_session().__anext__()

        try:
            org_model = OrganizationModel(
                id=organization.id,
                name=organization.name,
                slug=organization.slug,
                owner_id=organization.owner_id,
                is_active=organization.is_active,
                plan=organization.plan,
                created_at=organization.created_at,
                updated_at=organization.updated_at,
            )
            session.add(org_model)
            await session.commit()
            await session.refresh(org_model)

            return self._model_to_entity(org_model)
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def get_by_id(self, organization_id: uuid.UUID) -> Optional[Organization]:
        session = await get_async_session().__anext__()

        try:
            result = await session.execute(select(OrganizationModel).where(OrganizationModel.id == organization_id))
            org_row = result.scalar_one_or_none()
            if not org_row:
                return None

            return self._model_to_entity(org_row)
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def get_by_slug(self, slug: str) -> Optional[Organization]:
        session = await get_async_session().__anext__()

        try:
            result = await session.execute(select(OrganizationModel).where(OrganizationModel.slug == slug))
            org_row = result.scalar_one_or_none()
            if not org_row:
                return None

            return self._model_to_entity(org_row)
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def list_all(self, active_only: bool = True, skip: int = 0, limit: int = 100) -> List[Organization]:
        session = await get_async_session().__anext__()

        try:
            query = select(OrganizationModel)
            if active_only:
                query = query.where(OrganizationModel.is_active == True)
            query = query.offset(skip).limit(limit)

            result = await session.execute(query)
            org_rows = result.scalars().all()

            return [self._model_to_entity(row) for row in org_rows]
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def update(self, organization: Organization) -> Organization:
        session = await get_async_session().__anext__()

        try:
            org_model = await session.get(OrganizationModel, organization.id)
            if not org_model:
                raise ValueError("Organization not found")

            org_model.name = organization.name
            org_model.slug = organization.slug
            org_model.owner_id = organization.owner_id
            org_model.is_active = organization.is_active
            org_model.plan = organization.plan
            org_model.updated_at = datetime.utcnow()

            await session.commit()
            await session.refresh(org_model)

            return self._model_to_entity(org_model)
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()
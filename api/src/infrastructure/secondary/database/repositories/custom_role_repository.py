from sqlalchemy.future import select
from typing import Optional, List, cast
import uuid
from datetime import datetime
from application.ports.output.i_custom_role_repository import ICustomRoleRepository
from domain.entities.custom_role import CustomRole
from domain.enums import Permission
from infrastructure.secondary.database.models.custom_role_model import CustomRoleModel
from infrastructure.secondary.database.get_async_session import AsyncSessionLocal


class SqlCustomRoleRepository(ICustomRoleRepository):
    def _model_to_entity(self, row: CustomRoleModel) -> CustomRole:
        return CustomRole(
            id=cast(uuid.UUID, row.id),
            organization_id=cast(uuid.UUID, row.organization_id),
            name=cast(str, row.name),
            permissions=[Permission(p) for p in row.permissions],
            is_active=cast(bool, row.is_active),
            created_at=cast(datetime, row.created_at),
            updated_at=cast(datetime, row.updated_at),
        )

    async def create(self, role: CustomRole) -> CustomRole:
        async with AsyncSessionLocal() as session:
            model = CustomRoleModel(
                id=role.id,
                organization_id=role.organization_id,
                name=role.name,
                permissions=[p.value for p in role.permissions],
                is_active=role.is_active,
                created_at=role.created_at,
                updated_at=role.updated_at,
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)

            return self._model_to_entity(model)

    async def get_by_id(self, role_id: uuid.UUID) -> Optional[CustomRole]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(CustomRoleModel).where(CustomRoleModel.id == role_id))
            row = result.scalar_one_or_none()
            if not row:
                return None

            return self._model_to_entity(row)

    async def list_by_organization(self, organization_id: uuid.UUID) -> List[CustomRole]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(CustomRoleModel).where(CustomRoleModel.organization_id == organization_id)
            )
            rows = result.scalars().all()

            return [self._model_to_entity(row) for row in rows]

    async def update(self, role: CustomRole) -> CustomRole:
        async with AsyncSessionLocal() as session:
            model = await session.get(CustomRoleModel, role.id)
            if not model:
                raise ValueError("Custom role not found")

            model.name = role.name  # pyright: ignore[reportAttributeAccessIssue]
            model.permissions = [p.value for p in role.permissions]  # pyright: ignore[reportAttributeAccessIssue]
            model.is_active = role.is_active  # pyright: ignore[reportAttributeAccessIssue]
            model.updated_at = datetime.now(datetime.timezone.utc)

            await session.commit()
            await session.refresh(model)

            return self._model_to_entity(model)

    async def delete(self, role_id: uuid.UUID) -> None:
        async with AsyncSessionLocal() as session:
            model = await session.get(CustomRoleModel, role_id)
            if not model:
                raise ValueError("Custom role not found")

            await session.delete(model)
            await session.commit()
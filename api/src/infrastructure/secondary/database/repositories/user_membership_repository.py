from sqlalchemy.future import select
from typing import Optional, List, cast
import uuid
from datetime import datetime
from application.ports.output.i_user_membership_repository import IUserMembershipRepository
from domain.entities.user import UserMembership
from domain.enums import UserRole
from infrastructure.secondary.database.models.user_membership_model import UserMembershipModel
from infrastructure.secondary.database.get_async_session import AsyncSessionLocal


class SqlUserMembershipRepository(IUserMembershipRepository):
    def _model_to_entity(self, row: UserMembershipModel) -> UserMembership:
        return UserMembership(
            id=cast(uuid.UUID, row.id),
            user_id=cast(uuid.UUID, row.user_id),
            organization_id=cast(uuid.UUID, row.organization_id),
            role=UserRole(row.role),
            created_at=cast(datetime, row.created_at),
        )

    async def create(self, membership: UserMembership) -> UserMembership:
        async with AsyncSessionLocal() as session:
            model = UserMembershipModel(
                id=membership.id,
                organization_id=membership.organization_id,
                user_id=membership.user_id,
                role=membership.role.value,
                created_at=membership.created_at,
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return self._model_to_entity(model)

    async def get(self, user_id: uuid.UUID, organization_id: uuid.UUID) -> Optional[UserMembership]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(UserMembershipModel).where(
                    UserMembershipModel.user_id == user_id,
                    UserMembershipModel.organization_id == organization_id,
                )
            )
            row = result.scalar_one_or_none()
            return self._model_to_entity(row) if row else None

    async def list_by_user(self, user_id: uuid.UUID) -> List[UserMembership]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(UserMembershipModel).where(UserMembershipModel.user_id == user_id)
            )
            return [self._model_to_entity(row) for row in result.scalars().all()]

    async def list_by_organization(self, organization_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[UserMembership]:
        async with AsyncSessionLocal() as session:
            query = (
                select(UserMembershipModel)
                .where(UserMembershipModel.organization_id == organization_id)
                .offset(skip)
                .limit(limit)
            )
            result = await session.execute(query)
            return [self._model_to_entity(row) for row in result.scalars().all()]

    async def update_role(self, user_id: uuid.UUID, organization_id: uuid.UUID, role: UserRole) -> UserMembership:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(UserMembershipModel).where(
                    UserMembershipModel.user_id == user_id,
                    UserMembershipModel.organization_id == organization_id,
                )
            )
            model = result.scalar_one_or_none()
            if not model:
                raise ValueError("Membership not found")
            model.role = role.value  # pyright: ignore[reportAttributeAccessIssue]
            await session.commit()
            await session.refresh(model)
            return self._model_to_entity(model)

    async def delete(self, user_id: uuid.UUID, organization_id: uuid.UUID) -> None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(UserMembershipModel).where(
                    UserMembershipModel.user_id == user_id,
                    UserMembershipModel.organization_id == organization_id,
                )
            )
            model = result.scalar_one_or_none()
            if model:
                await session.delete(model)
                await session.commit()

    async def delete_all_for_user(self, user_id: uuid.UUID) -> None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(UserMembershipModel).where(UserMembershipModel.user_id == user_id)
            )
            for model in result.scalars().all():
                await session.delete(model)
            await session.commit()

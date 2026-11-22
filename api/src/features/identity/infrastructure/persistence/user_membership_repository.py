from sqlalchemy.future import select
from typing import Optional, List, cast
import uuid
from datetime import datetime
from features.identity.application.ports.i_user_membership_repository import IUserMembershipRepository
from features.identity.domain.user import UserMembership
from shared.domain.enums import UserRole
from shared.infrastructure.database.models.user_membership_model import UserMembershipModel
from shared.infrastructure.database.get_async_session import AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from shared.infrastructure.database.repository_session import repository_session, persist_repository_changes


class SqlUserMembershipRepository(IUserMembershipRepository):
    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session

    def _model_to_entity(self, row: UserMembershipModel) -> UserMembership:
        return UserMembership(
            id=cast(uuid.UUID, row.id),
            user_id=cast(uuid.UUID, row.user_id),
            organization_id=cast(uuid.UUID, row.organization_id),
            role=UserRole(row.role),
            created_at=cast(datetime, row.created_at),
        )

    async def create(self, membership: UserMembership) -> UserMembership:
        async with repository_session(self._session, AsyncSessionLocal) as session:
            model = UserMembershipModel(
                id=membership.id,
                organization_id=membership.organization_id,
                user_id=membership.user_id,
                role=membership.role.value,
                created_at=membership.created_at,
            )
            session.add(model)
            await persist_repository_changes(session, in_transaction=self._session is not None)
            await session.refresh(model)
            return self._model_to_entity(model)

    async def get(self, user_id: uuid.UUID, organization_id: uuid.UUID) -> Optional[UserMembership]:
        async with repository_session(self._session, AsyncSessionLocal) as session:
            result = await session.execute(
                select(UserMembershipModel).where(
                    UserMembershipModel.user_id == user_id,
                    UserMembershipModel.organization_id == organization_id,
                )
            )
            row = result.scalar_one_or_none()
            return self._model_to_entity(row) if row else None

    async def list_by_user(self, user_id: uuid.UUID) -> List[UserMembership]:
        async with repository_session(self._session, AsyncSessionLocal) as session:
            result = await session.execute(
                select(UserMembershipModel).where(UserMembershipModel.user_id == user_id)
            )
            return [self._model_to_entity(row) for row in result.scalars().all()]

    async def list_by_organization(self, organization_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[UserMembership]:
        async with repository_session(self._session, AsyncSessionLocal) as session:
            query = (
                select(UserMembershipModel)
                .where(UserMembershipModel.organization_id == organization_id)
                .offset(skip)
                .limit(limit)
            )
            result = await session.execute(query)
            return [self._model_to_entity(row) for row in result.scalars().all()]

    async def update_role(self, user_id: uuid.UUID, organization_id: uuid.UUID, role: UserRole) -> UserMembership:
        async with repository_session(self._session, AsyncSessionLocal) as session:
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
            await persist_repository_changes(session, in_transaction=self._session is not None)
            await session.refresh(model)
            return self._model_to_entity(model)

    async def delete(self, user_id: uuid.UUID, organization_id: uuid.UUID) -> None:
        async with repository_session(self._session, AsyncSessionLocal) as session:
            result = await session.execute(
                select(UserMembershipModel).where(
                    UserMembershipModel.user_id == user_id,
                    UserMembershipModel.organization_id == organization_id,
                )
            )
            model = result.scalar_one_or_none()
            if model:
                await session.delete(model)
                await persist_repository_changes(session, in_transaction=self._session is not None)

    async def delete_all_for_user(self, user_id: uuid.UUID) -> None:
        async with repository_session(self._session, AsyncSessionLocal) as session:
            result = await session.execute(
                select(UserMembershipModel).where(UserMembershipModel.user_id == user_id)
            )
            for model in result.scalars().all():
                await session.delete(model)
            await persist_repository_changes(session, in_transaction=self._session is not None)

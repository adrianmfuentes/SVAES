from uuid import UUID
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from domain.entities.user import User, UserRole
from domain.ports.i_user_repository import IUserRepository
from infrastructure.database.models.user import UserModel


class SqlUserRepository(IUserRepository):
    """Async SQLAlchemy adapter for IUserRepository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user: User) -> User:
        model = UserModel(
            id=user.id,
            email=user.email,
            password_hash=user.hashed_password,
            display_name=user.email,
            role=user.role.value,
            is_active=True,
        )
        self.session.add(model)
        await self.session.flush()
        return user

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        model = await self.session.get(UserModel, user_id)
        return self._to_entity(model) if model else None

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(select(UserModel).where(UserModel.email == email))
        model = result.scalars().first()
        return self._to_entity(model) if model else None

    async def list_all(self, active_only: bool = True, skip: int = 0, limit: int = 100) -> List[User]:
        stmt = select(UserModel)
        if active_only:
            stmt = stmt.where(UserModel.is_active.is_(True))
        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def update(self, user: User) -> User:
        model = await self.session.get(UserModel, user.id)
        if model:
            model.email = user.email
            model.password_hash = user.hashed_password
            model.role = user.role.value
            await self.session.flush()
        return user

    async def delete(self, user_id: UUID) -> None:
        model = await self.session.get(UserModel, user_id)
        if model:
            model.is_active = False
            await self.session.flush()

    def _to_entity(self, model: UserModel) -> User:
        return User(
            id=model.id,
            email=model.email,
            hashed_password=model.password_hash,
            role=UserRole(model.role),
            organization_id=None,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

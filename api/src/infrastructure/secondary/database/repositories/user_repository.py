from sqlalchemy.future import select
from typing import Optional, List
import uuid
from datetime import datetime
from application.ports.output.i_user_repository import IUserRepository
from domain.entities.user import User
from domain.enums import UserRole
from infrastructure.secondary.database.models.user_model import UserModel
from infrastructure.secondary.database.get_async_session import get_async_session


class SqlUserRepository(IUserRepository):
    async def create(self, user: User) -> User:
        session = await get_async_session().__anext__()

        try:
            user_model = UserModel(
                id=user.id,
                email=user.email,
                hashed_password=user.hashed_password,
                display_name=user.display_name,
                role=user.role.value,
                organization_id=user.organization_id,
                is_active=user.is_active,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )
            session.add(user_model)
            await session.commit()
            await session.refresh(user_model)

            return User(
                id=user_model.id,
                email=user_model.email,
                hashed_password=user_model.hashed_password,
                display_name=user_model.display_name,
                role=UserRole(user_model.role),
                organization_id=user_model.organization_id,
                is_active=user_model.is_active,
                created_at=user_model.created_at,
                updated_at=user_model.updated_at,
            )
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        session = await get_async_session().__anext__()

        try:
            result = await session.execute(select(UserModel).where(UserModel.id == user_id))
            user_row = result.scalar_one_or_none()
            if not user_row:
                return None

            return User(
                id=user_row.id,
                email=user_row.email,
                hashed_password=user_row.hashed_password,
                display_name=user_row.display_name,
                role=UserRole(user_row.role),
                organization_id=user_row.organization_id,
                is_active=user_row.is_active,
                created_at=user_row.created_at,
                updated_at=user_row.updated_at,
            )
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def get_by_email(self, email: str) -> Optional[User]:
        session = await get_async_session().__anext__()

        try:
            result = await session.execute(select(UserModel).where(UserModel.email == email))
            user_row = result.scalar_one_or_none()
            if not user_row:
                return None

            return User(
                id=user_row.id,
                email=user_row.email,
                hashed_password=user_row.hashed_password,
                display_name=user_row.display_name,
                role=UserRole(user_row.role),
                organization_id=user_row.organization_id,
                is_active=user_row.is_active,
                created_at=user_row.created_at,
                updated_at=user_row.updated_at,
            )
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def list_all(self, active_only: bool = True, skip: int = 0, limit: int = 100) -> List[User]:
        session = await get_async_session().__anext__()

        try:
            query = select(UserModel)
            if active_only:
                query = query.where(UserModel.is_active == True)
            query = query.offset(skip).limit(limit)

            result = await session.execute(query)
            user_rows = result.scalars().all()

            return [
                User(
                    id=row.id,
                    email=row.email,
                    hashed_password=row.hashed_password,
                    display_name=row.display_name,
                    role=UserRole(row.role),
                    organization_id=row.organization_id,
                    is_active=row.is_active,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )
                for row in user_rows
            ]
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def update(self, user: User) -> User:
        session = await get_async_session().__anext__()

        try:
            user_model = await session.get(UserModel, user.id)
            if not user_model:
                raise ValueError("User not found")

            user_model.email = user.email
            user_model.hashed_password = user.hashed_password
            user_model.display_name = user.display_name
            user_model.role = user.role.value
            user_model.organization_id = user.organization_id
            user_model.is_active = user.is_active
            user_model.updated_at = datetime.utcnow()

            await session.commit()
            await session.refresh(user_model)

            return User(
                id=user_model.id,
                email=user_model.email,
                hashed_password=user_model.hashed_password,
                display_name=user_model.display_name,
                role=UserRole(user_model.role),
                organization_id=user_model.organization_id,
                is_active=user_model.is_active,
                created_at=user_model.created_at,
                updated_at=user_model.updated_at,
            )
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def delete(self, user_id: uuid.UUID) -> None:
        session = await get_async_session().__anext__()

        try:
            user_model = await session.get(UserModel, user_id)
            if not user_model:
                raise ValueError("User not found")

            await session.delete(user_model)
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()
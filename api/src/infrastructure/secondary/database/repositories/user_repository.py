from sqlalchemy.future import select
from typing import Optional, List, cast
import uuid
from datetime import datetime, timezone
from application.ports.output.i_user_repository import IUserRepository
from domain.entities.user import User
from domain.enums import UserRole
from infrastructure.secondary.database.models.user_model import UserModel
from infrastructure.secondary.database.get_async_session import AsyncSessionLocal


class SqlUserRepository(IUserRepository):
    def _model_to_entity(self, row: UserModel) -> User:
        org_id = cast(uuid.UUID | None, row.organization_id)
        return User(
            id=cast(uuid.UUID, row.id),
            email=cast(str, row.email),
            hashed_password=cast(str, row.hashed_password),
            display_name=cast(str, row.display_name),
            role=UserRole(row.role),
            organization_ids=[org_id] if org_id is not None else [],
            is_active=cast(bool, row.is_active),
            failed_login_attempts=cast(int, row.failed_login_attempts),
            locked_until=cast(datetime | None, row.locked_until),
            created_at=cast(datetime, row.created_at),
            updated_at=cast(datetime, row.updated_at),
            terms_accepted_at=cast(datetime | None, row.terms_accepted_at),
            privacy_accepted_at=cast(datetime | None, row.privacy_accepted_at),
            activation_token=cast(str | None, row.activation_token),
            activation_token_expiry=cast(datetime | None, row.activation_token_expiry),
            totp_secret=cast(str | None, row.totp_secret),
            totp_enabled=cast(bool, row.totp_enabled) if row.totp_enabled is not None else False,
            password_reset_token=cast(str | None, row.password_reset_token),
            password_reset_token_expiry=cast(datetime | None, row.password_reset_token_expiry),
        )

    async def create(self, user: User) -> User:
        async with AsyncSessionLocal() as session:
            user_model = UserModel(
                id=user.id,
                email=user.email,
                hashed_password=user.hashed_password,
                display_name=user.display_name,
                role=user.role.value,
                organization_id=user.organization_id,
                is_active=user.is_active,
                failed_login_attempts=user.failed_login_attempts,
                locked_until=user.locked_until,
                created_at=user.created_at,
                updated_at=user.updated_at,
                terms_accepted_at=user.terms_accepted_at,
                privacy_accepted_at=user.privacy_accepted_at,
            )
            user_model.activation_token = user.activation_token  # pyright: ignore[reportAttributeAccessIssue]
            user_model.activation_token_expiry = user.activation_token_expiry  # pyright: ignore[reportAttributeAccessIssue]
            session.add(user_model)
            await session.commit()
            await session.refresh(user_model)
            return self._model_to_entity(user_model)

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(UserModel).where(UserModel.id == user_id))
            user_row = result.scalar_one_or_none()
            if not user_row:
                return None
            return self._model_to_entity(user_row)

    async def get_by_email(self, email: str) -> Optional[User]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(UserModel).where(UserModel.email == email))
            user_row = result.scalar_one_or_none()
            if not user_row:
                return None
            return self._model_to_entity(user_row)

    async def list_all(self, organization_id: Optional[uuid.UUID] = None, active_only: bool = True, skip: int = 0, limit: int = 100) -> List[User]:
        async with AsyncSessionLocal() as session:
            query = select(UserModel)
            if organization_id is not None:
                query = query.where(UserModel.organization_id == organization_id)
            if active_only:
                query = query.where(UserModel.is_active == True)
            query = query.offset(skip).limit(limit)
            result = await session.execute(query)
            user_rows = result.scalars().all()
            return [self._model_to_entity(row) for row in user_rows]

    async def update(self, user: User) -> User:
        async with AsyncSessionLocal() as session:
            user_model = await session.get(UserModel, user.id)
            if not user_model:
                raise ValueError("User not found")
            user_model.email = user.email  # pyright: ignore[reportAttributeAccessIssue]
            user_model.hashed_password = user.hashed_password  # pyright: ignore[reportAttributeAccessIssue]
            user_model.display_name = user.display_name  # pyright: ignore[reportAttributeAccessIssue]
            user_model.role = user.role  # pyright: ignore[reportAttributeAccessIssue]
            user_model.organization_id = user.organization_id  # pyright: ignore[reportAttributeAccessIssue]
            user_model.is_active = user.is_active  # pyright: ignore[reportAttributeAccessIssue]
            user_model.failed_login_attempts = user.failed_login_attempts  # pyright: ignore[reportAttributeAccessIssue]
            user_model.locked_until = user.locked_until  # pyright: ignore[reportAttributeAccessIssue]
            user_model.activation_token = user.activation_token  # pyright: ignore[reportAttributeAccessIssue]
            user_model.activation_token_expiry = user.activation_token_expiry  # pyright: ignore[reportAttributeAccessIssue]
            user_model.totp_secret = user.totp_secret  # pyright: ignore[reportAttributeAccessIssue]
            user_model.totp_enabled = user.totp_enabled  # pyright: ignore[reportAttributeAccessIssue]
            user_model.password_reset_token = user.password_reset_token  # pyright: ignore[reportAttributeAccessIssue]
            user_model.password_reset_token_expiry = user.password_reset_token_expiry  # pyright: ignore[reportAttributeAccessIssue]
            user_model.updated_at = datetime.now(timezone.utc)  # pyright: ignore[reportAttributeAccessIssue]
            await session.commit()
            await session.refresh(user_model)
            return self._model_to_entity(user_model)

    async def get_by_password_reset_token(self, token: str) -> Optional[User]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(UserModel).where(UserModel.password_reset_token == token))
            row = result.scalar_one_or_none()
            return self._model_to_entity(row) if row else None

    async def get_by_activation_token(self, token: str) -> Optional[User]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(UserModel).where(UserModel.activation_token == token))
            row = result.scalar_one_or_none()
            return self._model_to_entity(row) if row else None

    async def delete(self, user_id: uuid.UUID) -> None:
        async with AsyncSessionLocal() as session:
            user_model = await session.get(UserModel, user_id)
            if not user_model:
                raise ValueError("User not found")
            session.delete(user_model)  # pyright: ignore[reportUnusedCoroutine]
            await session.commit()
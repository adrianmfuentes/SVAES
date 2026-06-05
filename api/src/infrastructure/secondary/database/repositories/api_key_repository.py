from sqlalchemy.future import select
from typing import List, Optional, cast
from datetime import datetime
import uuid
import hashlib
from application.ports.output.i_api_key_repository import IAPIKeyRepository
from domain.entities.api_key import APIKey
from infrastructure.secondary.database.models.api_key_model import APIKeyModel
from infrastructure.secondary.database.get_async_session import AsyncSessionLocal


def _model_to_entity(row: APIKeyModel) -> APIKey:
    return APIKey(
        id=cast(uuid.UUID, row.id),
        user_id=cast(uuid.UUID, row.user_id),
        organization_id=cast(uuid.UUID, row.organization_id),
        name=cast(str, row.name),
        key_hash=cast(str, row.key_hash),
        prefix=cast(str, row.prefix),
        is_active=cast(bool, row.is_active),
        created_at=cast(datetime, row.created_at),
        expires_at=cast(datetime | None, row.expires_at),
        last_used_at=cast(datetime | None, row.last_used_at),
    )


class SqlAPIKeyRepository(IAPIKeyRepository):
    async def save(self, api_key: APIKey) -> APIKey:
        async with AsyncSessionLocal() as session:
            model = APIKeyModel(
                id=api_key.id,
                user_id=api_key.user_id,
                organization_id=api_key.organization_id,
                name=api_key.name,
                key_hash=api_key.key_hash,
                prefix=api_key.prefix,
                is_active=api_key.is_active,
                created_at=api_key.created_at,
                expires_at=api_key.expires_at,
                last_used_at=api_key.last_used_at,
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return _model_to_entity(model)

    async def get_by_id(self, api_key_id: uuid.UUID) -> Optional[APIKey]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(APIKeyModel).where(APIKeyModel.id == api_key_id)
            )
            row = result.scalar_one_or_none()
            return _model_to_entity(row) if row else None

    async def get_by_hash(self, key_hash: str) -> Optional[APIKey]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(APIKeyModel).where(APIKeyModel.key_hash == key_hash)
            )
            row = result.scalar_one_or_none()
            return _model_to_entity(row) if row else None

    async def list_by_organization(self, organization_id: uuid.UUID) -> List[APIKey]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(APIKeyModel).where(APIKeyModel.organization_id == organization_id)
            )
            rows = result.scalars().all()
            return [_model_to_entity(row) for row in rows]

    async def list_by_user(self, user_id: uuid.UUID) -> List[APIKey]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(APIKeyModel).where(APIKeyModel.user_id == user_id)
            )
            rows = result.scalars().all()
            return [_model_to_entity(row) for row in rows]

    async def update(self, api_key: APIKey) -> APIKey:
        async with AsyncSessionLocal() as session:
            model = await session.get(APIKeyModel, api_key.id)
            if not model:
                raise ValueError("API key not found")
            model.name = api_key.name  # pyright: ignore[reportAttributeAccessIssue]
            model.is_active = api_key.is_active  # pyright: ignore[reportAttributeAccessIssue]
            model.expires_at = api_key.expires_at  # pyright: ignore[reportAttributeAccessIssue]
            model.last_used_at = api_key.last_used_at  # pyright: ignore[reportAttributeAccessIssue]
            await session.commit()
            await session.refresh(model)
            return _model_to_entity(model)

    async def delete(self, api_key_id: uuid.UUID) -> None:
        async with AsyncSessionLocal() as session:
            model = await session.get(APIKeyModel, api_key_id)
            if not model:
                raise ValueError("API key not found")
            session.delete(model)
            await session.commit()

    @staticmethod
    def hash_key(key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()
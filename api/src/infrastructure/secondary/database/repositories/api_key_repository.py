from sqlalchemy.future import select
from typing import List, Optional
import uuid
import hashlib
from application.ports.output.i_api_key_repository import IAPIKeyRepository
from domain.entities.api_key import APIKey
from infrastructure.secondary.database.models.api_key_model import APIKeyModel
from infrastructure.secondary.database.get_async_session import get_async_session


def _model_to_entity(row: APIKeyModel) -> APIKey:
    return APIKey(
        id=row.id,
        user_id=row.user_id,
        organization_id=row.organization_id,
        name=row.name,
        key_hash=row.key_hash,
        prefix=row.prefix,
        is_active=row.is_active,
        created_at=row.created_at,
        expires_at=row.expires_at,
        last_used_at=row.last_used_at,
    )


class SqlAPIKeyRepository(IAPIKeyRepository):
    async def save(self, api_key: APIKey) -> APIKey:
        session = await get_async_session().__anext__()
        try:
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
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def get_by_id(self, api_key_id: uuid.UUID) -> Optional[APIKey]:
        session = await get_async_session().__anext__()
        try:
            result = await session.execute(
                select(APIKeyModel).where(APIKeyModel.id == api_key_id)
            )
            row = result.scalar_one_or_none()
            return _model_to_entity(row) if row else None
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def get_by_hash(self, key_hash: str) -> Optional[APIKey]:
        session = await get_async_session().__anext__()
        try:
            result = await session.execute(
                select(APIKeyModel).where(APIKeyModel.key_hash == key_hash)
            )
            row = result.scalar_one_or_none()
            return _model_to_entity(row) if row else None
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def list_by_organization(self, organization_id: uuid.UUID) -> List[APIKey]:
        session = await get_async_session().__anext__()
        try:
            result = await session.execute(
                select(APIKeyModel).where(APIKeyModel.organization_id == organization_id)
            )
            rows = result.scalars().all()
            return [_model_to_entity(row) for row in rows]
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def list_by_user(self, user_id: uuid.UUID) -> List[APIKey]:
        session = await get_async_session().__anext__()
        try:
            result = await session.execute(
                select(APIKeyModel).where(APIKeyModel.user_id == user_id)
            )
            rows = result.scalars().all()
            return [_model_to_entity(row) for row in rows]
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def update(self, api_key: APIKey) -> APIKey:
        session = await get_async_session().__anext__()
        try:
            model = await session.get(APIKeyModel, api_key.id)
            if not model:
                raise ValueError("API key not found")
            model.name = api_key.name
            model.is_active = api_key.is_active
            model.expires_at = api_key.expires_at
            model.last_used_at = api_key.last_used_at
            await session.commit()
            await session.refresh(model)
            return _model_to_entity(model)
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def delete(self, api_key_id: uuid.UUID) -> None:
        session = await get_async_session().__anext__()
        try:
            model = await session.get(APIKeyModel, api_key_id)
            if not model:
                raise ValueError("API key not found")
            await session.delete(model)
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    @staticmethod
    def hash_key(key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()
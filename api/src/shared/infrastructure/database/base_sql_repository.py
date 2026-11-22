from typing import Any, List, Optional, Protocol
import uuid
from sqlalchemy.future import select

from shared.infrastructure.database.get_async_session import AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from shared.infrastructure.database.repository_session import repository_session, persist_repository_changes


def _session_scope():
    return repository_session(None, AsyncSessionLocal)


class _HasId(Protocol):
    id: uuid.UUID


class _ModelProtocol(Protocol):
    id: uuid.UUID

    def __init__(self, *, id: uuid.UUID, **kwargs: Any) -> None: ...


class BaseSqlRepository[T: _HasId, M: _ModelProtocol]:
    model_class: type[M]
    entity_class: type[T]

    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session

    async def _create(self, entity: T, **extra_model_attrs: Any) -> T:
        async with repository_session(self._session, AsyncSessionLocal) as session:
            model = self.model_class(id=entity.id, **extra_model_attrs)
            session.add(model)
            await persist_repository_changes(session, in_transaction=self._session is not None)
            await session.refresh(model)
            return self._model_to_entity(model)

    async def _get_by_id(self, id: uuid.UUID) -> Optional[T]:
        async with repository_session(self._session, AsyncSessionLocal) as session:
            result = await session.execute(select(self.model_class).filter_by(id=id))
            row = result.scalar_one_or_none()
            if row is None:
                return None
            return self._model_to_entity(row)

    async def _list_all(self) -> List[T]:
        async with repository_session(self._session, AsyncSessionLocal) as session:
            result = await session.execute(select(self.model_class))
            rows = result.scalars().all()
            return [self._model_to_entity(row) for row in rows]

    async def _delete(self, id: uuid.UUID) -> None:
        async with repository_session(self._session, AsyncSessionLocal) as session:
            model = await session.get(self.model_class, id)
            if model is None:
                raise ValueError(f"{self.entity_class.__name__} not found")
            await session.delete(model)
            await persist_repository_changes(session, in_transaction=self._session is not None)

    def _model_to_entity(self, row: M) -> T:
        raise NotImplementedError

    def _entity_to_model_attrs(self, entity: T) -> dict:
        raise NotImplementedError

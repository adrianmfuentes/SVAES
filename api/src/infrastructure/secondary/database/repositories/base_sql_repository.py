from contextlib import asynccontextmanager
from typing import Any, List, Optional
import uuid
from sqlalchemy.future import select

from infrastructure.secondary.database.get_async_session import get_async_session


@asynccontextmanager
async def _session_scope():
    session = await get_async_session().__anext__()
    try:
        yield session
    finally:
        await session.close()


class BaseSqlRepository[T, M]:
    model_class: type[M]
    entity_class: type[T]

    async def _create(self, entity: T, **extra_model_attrs: Any) -> T:
        async with _session_scope() as session:
            model = self.model_class(id=entity.id, **extra_model_attrs)
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return self._model_to_entity(model)

    async def _get_by_id(self, id: uuid.UUID) -> Optional[T]:
        async with _session_scope() as session:
            result = await session.execute(select(self.model_class).where(self.model_class.id == id))
            row = result.scalar_one_or_none()
            if row is None:
                return None
            return self._model_to_entity(row)

    async def _list_all(self) -> List[T]:
        async with _session_scope() as session:
            result = await session.execute(select(self.model_class))
            rows = result.scalars().all()
            return [self._model_to_entity(row) for row in rows]

    async def _delete(self, id: uuid.UUID) -> None:
        async with _session_scope() as session:
            model = await session.get(self.model_class, id)
            if model is None:
                raise ValueError(f"{self.entity_class.__name__} not found")
            await session.delete(model)
            await session.commit()

    def _model_to_entity(self, row: M) -> T:
        raise NotImplementedError

    def _entity_to_model_attrs(self, entity: T) -> dict:
        raise NotImplementedError
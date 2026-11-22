from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


@asynccontextmanager
async def repository_session(
    bound_session: AsyncSession | None, factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    if bound_session is not None:
        yield bound_session
    else:
        async with factory() as session:
            yield session


async def persist_repository_changes(session: AsyncSession, *, in_transaction: bool) -> None:
    if in_transaction:
        await session.flush()
    else:
        await session.commit()

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession


class SqlUnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        async with self.session, self.session.begin():
            yield

import asyncio
from collections.abc import Coroutine
from typing import Any

from shared.infrastructure.database.get_async_session import engine


def run_worker_coroutine[T](work: Coroutine[Any, Any, T]) -> T:
    async def execute() -> T:
        try:
            return await work
        finally:
            await engine.dispose()

    return asyncio.run(execute())

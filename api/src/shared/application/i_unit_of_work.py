from contextlib import AbstractAsyncContextManager
from typing import Protocol


class IUnitOfWork(Protocol):
    def transaction(self) -> AbstractAsyncContextManager[None]: ...

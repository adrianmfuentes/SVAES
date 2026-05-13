from abc import ABC, abstractmethod
import uuid
from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"
    REVOKED = "REVOKED"


class ITaskQueue(ABC):
    @abstractmethod
    async def enqueue_verification_task(self, release_id: uuid.UUID) -> str:
        pass

    @abstractmethod
    async def get_task_status(self, task_id: str) -> TaskStatus:
        pass

    @abstractmethod
    async def cancel_task(self, task_id: str) -> bool:
        pass
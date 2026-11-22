from abc import ABC, abstractmethod
from features.verification.domain.verification_result import VerificationResult
from shared.application.i_task_queue import TaskStatus


class ITaskService(ABC):
    @abstractmethod
    async def get_task_status(self, task_id: str) -> TaskStatus:
        pass
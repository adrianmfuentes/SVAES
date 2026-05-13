from abc import ABC, abstractmethod
from domain.entities.verification_result import VerificationResult
from application.ports.output.i_task_queue import TaskStatus


class ITaskService(ABC):
    @abstractmethod
    async def get_task_status(self, task_id: str) -> TaskStatus:
        pass
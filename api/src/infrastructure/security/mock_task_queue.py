import uuid
from domain.ports.i_task_queue import ITaskQueue

class MockTaskQueue(ITaskQueue):
    """Mock implementation of ITaskQueue for testing purposes. This class simulates the behavior of a task queue by generating unique task IDs
    and returning a fixed status for any given task. It allows for testing the integration of task queue functionality without relying on
    an actual message broker or task processing system.

    Methods:
        enqueue_verification_task(release_id: uuid.UUID) -> str: Simulates enqueuing a verification task for a given release ID and returns a unique task ID.
        get_task_status(task_id: str) -> str: Simulates retrieving the status of a task by returning a fixed
    """
    async def enqueue_verification_task(self, release_id: uuid.UUID) -> str:
        return str(uuid.uuid4())

    async def get_task_status(self, task_id: str) -> str:
        return "PENDING"

    async def cancel_task(self, task_id: str) -> bool:
        return True

import uuid
from domain.ports.i_task_queue import ITaskQueue

class MockTaskQueue(ITaskQueue):
    """Development stub for ITaskQueue.

    Returns random UUIDs as task IDs without real queueing. Replace with a
    Celery/ARQ/Redis Streams implementation before connecting the verification engine.
    """

    async def enqueue_verification_task(self, release_id: uuid.UUID) -> str:
        return str(uuid.uuid4())

    async def get_task_status(self, task_id: str) -> str:
        return "PENDING"

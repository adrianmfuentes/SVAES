import uuid
from domain.ports.i_task_queue import ITaskQueue
from infrastructure.queue.celery_app import celery_app


class CeleryTaskQueue(ITaskQueue):
    async def enqueue_verification_task(self, release_id: uuid.UUID) -> str:
        result = celery_app.send_task(
            "infrastructure.workers.verification_worker.run_verification",
            args=[str(release_id)],
            queue="verification",
        )
        return result.id

    async def get_task_status(self, task_id: str) -> str:
        result = celery_app.AsyncResult(task_id)
        return result.status  # PENDING | STARTED | SUCCESS | FAILURE | RETRY
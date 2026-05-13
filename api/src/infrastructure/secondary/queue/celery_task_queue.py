import uuid
from application.ports.output.i_task_queue import ITaskQueue, TaskStatus
from infrastructure.secondary.queue.celery_app import celery_app

"""
Este archivo implementa la interfaz ITaskQueue utilizando Celery para manejar tareas asíncronas en el proyecto SVAES.
La clase CeleryTaskQueue proporciona métodos para encolar tareas de verificación, obtener el estado de las tareas y cancelar tareas en ejecución.
"""
class CeleryTaskQueue(ITaskQueue):
    async def enqueue_verification_task(self, release_id: uuid.UUID) -> str:
        result = celery_app.send_task(
            "infrastructure.workers.verification_worker.run_verification",
            args=[str(release_id)],
            queue="verification",
        )
        return result.id


    async def get_task_status(self, task_id: str) -> TaskStatus:
        result = celery_app.AsyncResult(task_id)
        status_str = result.status

        try:
            return TaskStatus[status_str]
        except Exception:
            return TaskStatus.PENDING


    async def cancel_task(self, task_id: str) -> bool:
        result = celery_app.AsyncResult(task_id)
        result.revoke(terminate=True)
        return True
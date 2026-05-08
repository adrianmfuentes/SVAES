from abc import ABC, abstractmethod
import uuid

class ITaskQueue(ABC):
    """Outbound port for managing asynchronous tasks related to release verification. This interface defines the contract for enqueuing verification 
    tasks and checking their status, abstracting away the underlying task queue or message broker implementation. 
    Implementations of this interface can use Celery, RabbitMQ, Redis, or any other task queue system, while the application layer interacts with 
    it through these defined methods.

    Methods:
        enqueue_verification_task(release_id: uuid.UUID) -> str: Enqueues a verification task for a given release and returns the task ID for later status checks.
        get_task_status(task_id: str) -> str: Retrieves the current status of the enqueued task.
    """
    @abstractmethod
    async def enqueue_verification_task(self, release_id: uuid.UUID) -> str:
        """
        Encola la verificación de una release.
        Retorna el ID de la tarea (task_id) para poder consultarla luego.
        """
        pass
        
    @abstractmethod
    async def get_task_status(self, task_id: str) -> str:
        """Consulta el estado actual de la tarea encolada."""
        pass
from abc import ABC, abstractmethod
import uuid

class ITaskQueue(ABC):
    """Puerto para la gestión de tareas asíncronas."""

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
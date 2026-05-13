from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict

from application.ports.input.i_task_service import ITaskService
from core.dependencies import get_task_service, get_current_user, CurrentUser
from application.ports.output.i_task_queue import TaskStatus

router = APIRouter(tags=["Tasks"])

class TaskStatusResponse(BaseModel):
    model_config = ConfigDict(extra='forbid')
    task_id: str
    status: str
    result: str | None = None


@router.get("/api/v1/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    service: ITaskService = Depends(get_task_service),
):
    """ Endpoint para obtener el estado de una tarea asíncrona.

    Atributos:
        - task_id: str - El ID de la tarea a consultar.
        - service: ITaskService - El servicio de tareas, inyectado mediante dependencias
        
    Retorna:
        - Un diccionario con el ID de la tarea, su estado actual y el resultado si está disponible.
        - Lanza HTTPException con status 404 si la tarea no existe.
        - Lanza HTTPException con status 500 para cualquier error inesperado.
    """
    try:
        task_status = await service.get_task_status(task_id)
        return {
            "task_id": task_id,
            "status": task_status.value,
            "result": None,
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from application.ports.input.i_task_service import ITaskService
from core.dependencies import get_task_service, get_current_user, CurrentUser
from application.ports.output.i_task_queue import TaskStatus
from celery.result import AsyncResult
from infrastructure.secondary.queue.celery_app import celery_app
from . import ERROR_INTERNO

router = APIRouter(tags=["Tasks"])


class TaskProgressInfo(BaseModel):
    model_config = ConfigDict(extra='forbid')
    current: int
    total: int
    stage: str
    pct: int


class TaskStatusResponse(BaseModel):
    model_config = ConfigDict(extra='forbid')
    task_id: str
    status: str
    result: Optional[str] = None
    progress: Optional[TaskProgressInfo] = None


@router.get("/api/v1/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[ITaskService, Depends(get_task_service)],
):
    try:
        task_status = await service.get_task_status(task_id)
        celery_result = celery_app.AsyncResult(task_id)
        result_value = celery_result.result if celery_result.ready() else None

        progress: Optional[TaskProgressInfo] = None
        if celery_result.state == 'PROGRESS' and isinstance(celery_result.info, dict):
            info = celery_result.info
            try:
                progress = TaskProgressInfo(
                    current=int(info.get('current', 0)),
                    total=int(info.get('total', 1)),
                    stage=str(info.get('stage', 'loading')),
                    pct=int(info.get('pct', 0)),
                )
            except Exception:
                pass

        return TaskStatusResponse(
            task_id=task_id,
            status=task_status.value,
            result=str(result_value) if result_value is not None else None,
            progress=progress,
        )
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)

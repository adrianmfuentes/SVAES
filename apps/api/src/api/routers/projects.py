import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from application.use_cases.project_use_cases import CreateProjectUseCase, CreateProjectCommand
from api.dependencies import get_create_project_use_case


class ProjectCreate(BaseModel):
    organization_id: uuid.UUID
    name: str
    description: str = ""


router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_project(
    request: ProjectCreate,
    use_case: Annotated[CreateProjectUseCase, Depends(get_create_project_use_case)],
):
    command = CreateProjectCommand(
        organization_id=request.organization_id,
        name=request.name,
        description=request.description,
    )
    return await use_case.execute(command)

from typing import Annotated

from fastapi import APIRouter, Depends, status

from api.schemas.project import ProjectCreate, ProjectResponse
from application.use_cases.project_use_cases import CreateProjectUseCase, CreateProjectCommand
from api.dependencies import get_create_project_use_case, get_current_user
from domain.entities.user import User

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ProjectResponse)
async def create_project(
    request: ProjectCreate,
    use_case: Annotated[CreateProjectUseCase, Depends(get_create_project_use_case)],
    _current_user: Annotated[User, Depends(get_current_user)],
):
    command = CreateProjectCommand(
        organization_id=request.organization_id,
        name=request.name,
        description=request.description,
    )
    return await use_case.execute(command)

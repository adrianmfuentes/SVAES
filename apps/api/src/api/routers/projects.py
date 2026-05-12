import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from application.use_cases.project_use_cases import (
    CreateProjectUseCase,
    CreateProjectCommand,
    GetProjectUseCase,
    ListProjectsUseCase,
    UpdateProjectUseCase,
    UpdateProjectCommand,
    DeleteProjectUseCase,
)
from api.dependencies import (
    get_create_project_use_case,
    get_get_project_use_case,
    get_list_projects_use_case,
    get_update_project_use_case,
    get_delete_project_use_case,
    get_current_user,
    require_min_role,
)
from domain.entities.user import User
from domain.entities.enums import UserRole
from domain.exceptions import EntityNotFoundError

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ProjectResponse)
async def create_project(
    request: ProjectCreate,
    use_case: Annotated[CreateProjectUseCase, Depends(get_create_project_use_case)],
    _current_user: Annotated[User, require_min_role(UserRole.MANAGER)],
):
    command = CreateProjectCommand(
        organization_id=request.organization_id,
        name=request.name,
        description=request.description,
    )
    return await use_case.execute(command)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    use_case: Annotated[ListProjectsUseCase, Depends(get_list_projects_use_case)],
    _current_user: Annotated[User, Depends(get_current_user)],
    organization_id: Annotated[uuid.UUID, Query()],
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
):
    return await use_case.execute(organization_id, skip=skip, limit=limit)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    use_case: Annotated[GetProjectUseCase, Depends(get_get_project_use_case)],
    _current_user: Annotated[User, Depends(get_current_user)],
):
    try:
        return await use_case.execute(project_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    request: ProjectUpdate,
    use_case: Annotated[UpdateProjectUseCase, Depends(get_update_project_use_case)],
    _current_user: Annotated[User, require_min_role(UserRole.MANAGER)],
):
    try:
        command = UpdateProjectCommand(
            project_id=project_id,
            name=request.name,
            description=request.description,
        )
        return await use_case.execute(command)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: uuid.UUID,
    use_case: Annotated[DeleteProjectUseCase, Depends(get_delete_project_use_case)],
    _current_user: Annotated[User, require_min_role(UserRole.ADMIN)],
):
    try:
        await use_case.execute(project_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

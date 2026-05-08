import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from domain.entities.user import User
from application.use_cases.project_use_cases import CreateProjectUseCase, CreateProjectCommand
from api.dependencies import get_create_project_use_case, get_current_user

class ProjectCreate(BaseModel):
    """Pydantic model for creating a project.
    Attributes:
        organization_id (uuid.UUID): The ID of the organization to which the project belongs.
        name (str): The name of the project.
        description (str): An optional description of the project.
    """
    organization_id: uuid.UUID
    name: str
    description: str = ""

router = APIRouter(
    prefix="/projects", 
    tags=["Projects"]
)

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_project(
    request: ProjectCreate,
    use_case: Annotated[CreateProjectUseCase, Depends(get_create_project_use_case)],
    _current_user: Annotated[User, Depends(get_current_user)],
):
    """Endpoint to create a new project.
    Args:
        request (ProjectCreate): The request body containing project details.
        use_case (CreateProjectUseCase): The use case for creating a project, injected via
            FastAPI's dependency injection system.
        _current_user (User): The currently authenticated user, injected via FastAPI's dependency injection system.
    Returns:
        The result of the project creation, typically the created project's details or an identifier.
    """
    command = CreateProjectCommand(
        organization_id=request.organization_id,
        name=request.name,
        description=request.description,
    )
    return await use_case.execute(command)

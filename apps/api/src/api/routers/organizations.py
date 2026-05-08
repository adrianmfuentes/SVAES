from typing import Annotated
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from domain.entities.user import User
from application.use_cases.organization_use_cases import (
    CreateOrganizationUseCase,
    CreateOrganizationCommand,
    ListOrganizationsUseCase,
)
from api.dependencies import (
    get_create_organization_use_case,
    get_list_organizations_use_case,
    get_current_user,
)

class OrganizationCreate(BaseModel):
    """Pydantic model for creating an organization.
    Attributes:
        name (str): The name of the organization.
        slug (str): A unique identifier for the organization, typically used in URLs.
        plan (str): The subscription plan for the organization, default is "free".
    """
    name: str
    slug: str
    plan: str = "free"

router = APIRouter(
    prefix="/organizations", 
    tags=["Organizations"]
)

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_org(
    request: OrganizationCreate,
    use_case: Annotated[CreateOrganizationUseCase, Depends(get_create_organization_use_case)],
    _current_user: Annotated[User, Depends(get_current_user)],
):
    """Endpoint to create a new organization.
    Args:
        request (OrganizationCreate): The request body containing organization details.
        use_case (CreateOrganizationUseCase): The use case for creating an organization, injected via
            FastAPI's dependency injection system.
        _current_user (User): The currently authenticated user, injected via FastAPI's dependency injection system.
    Returns:
        The result of the organization creation, typically the created organization's details or an identifier.
    """
    command = CreateOrganizationCommand(name=request.name, slug=request.slug, plan=request.plan)
    return await use_case.execute(command)


@router.get("")
async def list_orgs(
    use_case: Annotated[ListOrganizationsUseCase, Depends(get_list_organizations_use_case)],
    _current_user: Annotated[User, Depends(get_current_user)],
):
    """Endpoint to list all organizations accessible to the current user.
    Args:
        use_case (ListOrganizationsUseCase): The use case for listing organizations, injected via
            FastAPI's dependency injection system.
        _current_user (User): The currently authenticated user, injected via FastAPI's dependency injection system.
    Returns:
        A list of organizations that the current user has access to.
    """
    return await use_case.execute()

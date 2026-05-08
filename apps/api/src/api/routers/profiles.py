import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from domain.entities.user import User
from application.use_cases.manage_profile import ManageProfileUseCase, CreateProfileCommand
from api.dependencies import get_manage_profile_use_case, get_current_user

class ProfileCreate(BaseModel):
    """Pydantic model for creating a profile.
    Attributes:
        organization_id (uuid.UUID): The ID of the organization to which the profile belongs.
        name (str): The name of the profile.
    """
    organization_id: uuid.UUID
    name: str

router = APIRouter(
    prefix="/profiles", 
    tags=["Profiles"]
)

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_profile(
    request: ProfileCreate,
    use_case: Annotated[ManageProfileUseCase, Depends(get_manage_profile_use_case)],
    _current_user: Annotated[User, Depends(get_current_user)],
):
    """Endpoint to create a new profile for a user within an organization.
    Args:
        request (ProfileCreate): The request body containing the organization ID and profile name.
        use_case (ManageProfileUseCase): The use case for managing profiles, injected via
            FastAPI's dependency injection system.
        _current_user (User): The currently authenticated user, injected via FastAPI's dependency injection system.

    Returns:
        The result of the profile creation, typically the created profile's details or an identifier.
    """
    command = CreateProfileCommand(
        organization_id=request.organization_id,
        name=request.name,
    )
    return await use_case.create_profile(command)

from typing import Annotated

from fastapi import APIRouter, Depends, status

from api.schemas.profile import ProfileCreate, ProfileResponse
from application.use_cases.manage_profile import ManageProfileUseCase, CreateProfileCommand
from api.dependencies import get_manage_profile_use_case, get_current_user
from domain.entities.user import User

router = APIRouter(prefix="/profiles", tags=["Profiles"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ProfileResponse)
async def create_profile(
    request: ProfileCreate,
    use_case: Annotated[ManageProfileUseCase, Depends(get_manage_profile_use_case)],
    _current_user: Annotated[User, Depends(get_current_user)],
):
    command = CreateProfileCommand(
        organization_id=request.organization_id,
        name=request.name,
    )
    return await use_case.create_profile(command)

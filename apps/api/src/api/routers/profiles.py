import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.schemas.profile import ProfileCreate, ProfileUpdate, ProfileResponse
from application.use_cases.manage_profile import ManageProfileUseCase, CreateProfileCommand, UpdateProfileCommand
from api.dependencies import get_manage_profile_use_case, get_current_user, require_min_role
from domain.entities.user import User
from domain.entities.enums import UserRole
from domain.exceptions import EntityNotFoundError

router = APIRouter(prefix="/profiles", tags=["Profiles"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ProfileResponse)
async def create_profile(
    request: ProfileCreate,
    use_case: Annotated[ManageProfileUseCase, Depends(get_manage_profile_use_case)],
    _current_user: Annotated[User, require_min_role(UserRole.MANAGER)],
):
    command = CreateProfileCommand(
        organization_id=request.organization_id,
        name=request.name,
    )
    return await use_case.create_profile(command)


@router.get("", response_model=list[ProfileResponse])
async def list_profiles(
    use_case: Annotated[ManageProfileUseCase, Depends(get_manage_profile_use_case)],
    _current_user: Annotated[User, Depends(get_current_user)],
    organization_id: Annotated[uuid.UUID, Query()],
    skip: Annotated[int, Query(default=0, ge=0)] = 0,
    limit: Annotated[int, Query(default=50, ge=1, le=200)] = 50,
):
    return await use_case.list_profiles(organization_id, skip=skip, limit=limit)


@router.get("/{profile_id}", response_model=ProfileResponse)
async def get_profile(
    profile_id: uuid.UUID,
    use_case: Annotated[ManageProfileUseCase, Depends(get_manage_profile_use_case)],
    _current_user: Annotated[User, Depends(get_current_user)],
):
    try:
        return await use_case.get_profile(profile_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/{profile_id}", response_model=ProfileResponse)
async def update_profile(
    profile_id: uuid.UUID,
    request: ProfileUpdate,
    use_case: Annotated[ManageProfileUseCase, Depends(get_manage_profile_use_case)],
    _current_user: Annotated[User, require_min_role(UserRole.MANAGER)],
):
    try:
        command = UpdateProfileCommand(profile_id=profile_id, name=request.name)
        return await use_case.update_profile(command)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    profile_id: uuid.UUID,
    use_case: Annotated[ManageProfileUseCase, Depends(get_manage_profile_use_case)],
    _current_user: Annotated[User, require_min_role(UserRole.ADMIN)],
):
    try:
        await use_case.delete_profile(profile_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

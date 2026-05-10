import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from domain.entities.user import User
from domain.entities.enums import UserRole
from domain.exceptions import EntityNotFoundError, ReleaseInvalidStateError
from api.schemas.release import ReleaseCreate, ReleaseUpdate, ReleaseResponse, VerificationTaskResponse
from application.use_cases.launch_verification import LaunchVerificationUseCase, LaunchVerificationCommand
from application.use_cases.create_release import (
    CreateReleaseUseCase,
    CreateReleaseCommand,
    GetReleaseUseCase,
    ListReleasesUseCase,
    UpdateReleaseUseCase,
    UpdateReleaseCommand,
    DeleteReleaseUseCase,
)
from application.use_cases.get_verification_history import GetVerificationHistoryUseCase
from api.dependencies import (
    get_launch_verification_use_case,
    get_create_release_use_case,
    get_get_release_use_case,
    get_list_releases_use_case,
    get_update_release_use_case,
    get_delete_release_use_case,
    get_verification_history_use_case,
    get_current_user,
    require_min_role,
)

router = APIRouter(prefix="/releases", tags=["Releases"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ReleaseResponse)
async def create_release(
    request: ReleaseCreate,
    use_case: Annotated[CreateReleaseUseCase, Depends(get_create_release_use_case)],
    current_user: Annotated[User, require_min_role(UserRole.OPERATOR)],
):
    command = CreateReleaseCommand(
        project_id=request.project_id,
        profile_id=request.profile_id,
        version=request.version,
        description=request.description,
        created_by=current_user.id,
    )
    return await use_case.execute(command)


@router.get("", response_model=list[ReleaseResponse])
async def list_releases(
    use_case: Annotated[ListReleasesUseCase, Depends(get_list_releases_use_case)],
    _current_user: Annotated[User, Depends(get_current_user)],
    project_id: Annotated[uuid.UUID, Query()],
):
    return await use_case.execute(project_id)


@router.get("/{release_id}", response_model=ReleaseResponse)
async def get_release(
    release_id: uuid.UUID,
    use_case: Annotated[GetReleaseUseCase, Depends(get_get_release_use_case)],
    _current_user: Annotated[User, Depends(get_current_user)],
):
    try:
        return await use_case.execute(release_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/{release_id}", response_model=ReleaseResponse)
async def update_release(
    release_id: uuid.UUID,
    request: ReleaseUpdate,
    use_case: Annotated[UpdateReleaseUseCase, Depends(get_update_release_use_case)],
    _current_user: Annotated[User, require_min_role(UserRole.OPERATOR)],
):
    try:
        command = UpdateReleaseCommand(release_id=release_id, description=request.description)
        return await use_case.execute(command)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ReleaseInvalidStateError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.delete("/{release_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_release(
    release_id: uuid.UUID,
    use_case: Annotated[DeleteReleaseUseCase, Depends(get_delete_release_use_case)],
    _current_user: Annotated[User, require_min_role(UserRole.MANAGER)],
):
    try:
        await use_case.execute(release_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ReleaseInvalidStateError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/{release_id}/results")
async def get_results(
    release_id: uuid.UUID,
    use_case: Annotated[GetVerificationHistoryUseCase, Depends(get_verification_history_use_case)],
    _current_user: Annotated[User, Depends(get_current_user)],
):
    try:
        return await use_case.execute(release_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/{release_id}/verify",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=VerificationTaskResponse,
)
async def verify_release(
    release_id: uuid.UUID,
    use_case: Annotated[LaunchVerificationUseCase, Depends(get_launch_verification_use_case)],
    current_user: Annotated[User, require_min_role(UserRole.OPERATOR)],
):
    command = LaunchVerificationCommand(release_id=release_id, user_id=current_user.id)

    try:
        _, task_id = await use_case.execute(command)
        return VerificationTaskResponse(
            message="Verification successfully queued",
            task_id=task_id,
        )
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ReleaseInvalidStateError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except (ValueError, RuntimeError) as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e

import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from domain.entities.user import User
from domain.exceptions import EntityNotFoundError, ReleaseInvalidStateError
from api.schemas.release import ReleaseResponse, VerificationTaskResponse
from application.use_cases.launch_verification import LaunchVerificationUseCase, LaunchVerificationCommand
from application.use_cases.create_release import CreateReleaseUseCase, CreateReleaseCommand
from application.use_cases.get_verification_history import GetVerificationHistoryUseCase
from api.dependencies import (
    get_launch_verification_use_case,
    get_create_release_use_case,
    get_verification_history_use_case,
    get_current_user,
)

class ReleaseCreate(BaseModel):
    """Pydantic model for creating a release.
    Attributes:
        project_id (uuid.UUID): The ID of the project to which the release belongs.
        profile_id (uuid.UUID): The ID of the profile associated with the release.
        version (str): The version of the release.
        description (str): An optional description of the release.
    """
    project_id: uuid.UUID
    profile_id: uuid.UUID
    version: str
    description: str = ""

router = APIRouter(
    prefix="/releases",
    tags=["Releases"]
)

@router.post("", status_code=status.HTTP_201_CREATED, response_model=ReleaseResponse)
async def create_release(
    request: ReleaseCreate,
    use_case: Annotated[
        CreateReleaseUseCase,
        Depends(get_create_release_use_case),
    ],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Endpoint to create a new release.
    Args:
        request (ReleaseCreate): The request body containing release details.
        use_case (CreateReleaseUseCase): The use case for creating a release, injected via
            FastAPI's dependency injection system.
        current_user (User): The currently authenticated user, injected via FastAPI's dependency injection system.
    Returns:
        The result of the release creation, typically the created release's details or an identifier.
    """
    command = CreateReleaseCommand(
        project_id=request.project_id,
        profile_id=request.profile_id,
        version=request.version,
        description=request.description,
        created_by=current_user.id,
    )
    return await use_case.execute(command)


@router.get("/{release_id}/results")
async def get_results(
    release_id: uuid.UUID,
    use_case: Annotated[
        GetVerificationHistoryUseCase,
        Depends(get_verification_history_use_case),
    ],
    _current_user: Annotated[User, Depends(get_current_user)],
):
    """Endpoint to get the verification results for a specific release.
    Args:
        release_id (uuid.UUID): The ID of the release for which to get verification results.
        use_case (GetVerificationHistoryUseCase): The use case for getting verification history, injected via
            FastAPI's dependency injection system.
        _current_user (User): The currently authenticated user, injected via FastAPI's dependency injection system.
    Returns:
        The verification results for the specified release.
    """
    try:
        return await use_case.execute(release_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/{release_id}/verify",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=VerificationTaskResponse,
    summary="Launch asynchronous verification of a release",
)
async def verify_release(
    release_id: uuid.UUID,
    use_case: Annotated[
        LaunchVerificationUseCase,
        Depends(get_launch_verification_use_case),
    ],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Endpoint to launch asynchronous verification of a release.
    Args:
        release_id (uuid.UUID): The ID of the release to verify.
        use_case (LaunchVerificationUseCase): The use case for launching verification, injected via
            FastAPI's dependency injection system.
        current_user (User): The currently authenticated user, injected via FastAPI's dependency injection system.
    Returns:
        A response indicating the verification task has been queued.
    """
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

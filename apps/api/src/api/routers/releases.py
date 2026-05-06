import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from domain.entities.user import User
from domain.exceptions import EntityNotFoundError, ReleaseInvalidStateError
from api.schemas.release import VerificationTaskResponse
from api.dependencies import (
    get_launch_verification_use_case,
    get_create_release_use_case,
    get_verification_history_use_case,
    get_current_user,
)
from application.use_cases.launch_verification import LaunchVerificationUseCase, LaunchVerificationCommand
from application.use_cases.create_release import CreateReleaseUseCase, CreateReleaseCommand
from application.use_cases.get_verification_history import GetVerificationHistoryUseCase

router = APIRouter(prefix="/releases", tags=["Releases"])

class ReleaseCreate(BaseModel):
    project_id: uuid.UUID
    profile_id: uuid.UUID
    version: str
    description: str = ""


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_release(
    request: ReleaseCreate,
    use_case: Annotated[
        CreateReleaseUseCase,
        Depends(get_create_release_use_case),
    ],
    current_user: Annotated[User, Depends(get_current_user)],
):
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
    try:
        return await use_case.execute(release_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/{release_id}/verify",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=VerificationTaskResponse,
    summary="Lanza la verificación asíncrona de una release",
)
async def verify_release(
    release_id: uuid.UUID,
    use_case: Annotated[
        LaunchVerificationUseCase,
        Depends(get_launch_verification_use_case),
    ],
    current_user: Annotated[User, Depends(get_current_user)],
):
    command = LaunchVerificationCommand(release_id=release_id, user_id=current_user.id)

    try:
        _, task_id = await use_case.execute(command)
        return VerificationTaskResponse(
            message="Verificación encolada correctamente",
            task_id=task_id,
        )
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ReleaseInvalidStateError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except (ValueError, RuntimeError) as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor",
        ) from e

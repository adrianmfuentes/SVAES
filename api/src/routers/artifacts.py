import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from api.dependencies import (
    get_artifact_repository,
    get_current_user,
    get_release_repository,
    require_min_role,
)
from api.schemas.artifact import ArtifactCreateRequest, ArtifactResponse
from application.use_cases.artifact_use_cases import (
    DeleteArtifactUseCase,
    GetArtifactUseCase,
    ListArtifactsUseCase,
    RegisterArtifactCommand,
    RegisterArtifactUseCase,
)
from api.rate_limit import limiter
from domain.entities.enums import UserRole
from domain.entities.user import User
from domain.exceptions import EntityNotFoundError
from infrastructure.database.repositories.artifact_repository import SqlArtifactRepository
from infrastructure.database.repositories.release_repository import SqlReleaseRepository

router = APIRouter(prefix="/releases/{release_id}/artifacts", tags=["Artifacts"])


# ---------------------------------------------------------------------------
# POST /releases/{release_id}/artifacts
# ---------------------------------------------------------------------------
@router.post("", response_model=ArtifactResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def register_artifact(
    req: Request,
    release_id: uuid.UUID,
    request: ArtifactCreateRequest,
    artifact_repo: Annotated[SqlArtifactRepository, Depends(get_artifact_repository)],
    release_repo: Annotated[SqlReleaseRepository, Depends(get_release_repository)],
    _current_user: Annotated[User, require_min_role(UserRole.OPERATOR)],
):
    use_case = RegisterArtifactUseCase(artifact_repo=artifact_repo, release_repo=release_repo)
    try:
        return await use_case.execute(
            RegisterArtifactCommand(
                release_id=release_id,
                artifact_type=request.artifact_type,
                external_ref=request.external_ref,
                connector_instance_id=request.connector_instance_id,
                metadata=request.metadata,
            )
        )
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


# ---------------------------------------------------------------------------
# GET /releases/{release_id}/artifacts
# ---------------------------------------------------------------------------
@router.get("", response_model=list[ArtifactResponse])
async def list_artifacts(
    release_id: uuid.UUID,
    artifact_repo: Annotated[SqlArtifactRepository, Depends(get_artifact_repository)],
    release_repo: Annotated[SqlReleaseRepository, Depends(get_release_repository)],
    _current_user: Annotated[User, require_min_role(UserRole.VIEWER)],
    skip: Annotated[int, Query(default=0, ge=0)],
    limit: Annotated[int, Query(default=100, ge=1, le=500)],
):
    use_case = ListArtifactsUseCase(artifact_repo=artifact_repo, release_repo=release_repo)
    try:
        return await use_case.execute(release_id, skip=skip, limit=limit)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ---------------------------------------------------------------------------
# GET /releases/{release_id}/artifacts/{artifact_id}
# ---------------------------------------------------------------------------
@router.get("/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(
    release_id: uuid.UUID,
    artifact_id: uuid.UUID,
    artifact_repo: Annotated[SqlArtifactRepository, Depends(get_artifact_repository)],
    _current_user: Annotated[User, require_min_role(UserRole.VIEWER)],
):
    use_case = GetArtifactUseCase(artifact_repo=artifact_repo)
    try:
        return await use_case.execute(release_id=release_id, artifact_id=artifact_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ---------------------------------------------------------------------------
# DELETE /releases/{release_id}/artifacts/{artifact_id}
# ---------------------------------------------------------------------------
@router.delete("/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_artifact(
    release_id: uuid.UUID,
    artifact_id: uuid.UUID,
    artifact_repo: Annotated[SqlArtifactRepository, Depends(get_artifact_repository)],
    _current_user: Annotated[User, require_min_role(UserRole.MANAGER)],
):
    use_case = DeleteArtifactUseCase(artifact_repo=artifact_repo)
    try:
        await use_case.execute(release_id=release_id, artifact_id=artifact_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

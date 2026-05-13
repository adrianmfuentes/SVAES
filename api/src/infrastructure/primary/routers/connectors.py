import uuid
from typing import Annotated, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from api.dependencies import (
    get_configure_connector_use_case,
    get_connector_repository,
    get_connector_registry,
    get_credential_encryptor,
    get_current_user,
    require_min_role,
)
from api.schemas.connector import ConnectorCreateRequest, ConnectorResponse, ConnectorUpdateRequest
from application.use_cases.configure_connector import ConfigureConnectorCommand, ConfigureConnectorUseCase
from api.src.application.use_cases.crud_connector import (
    DeleteConnectorCommand,
    DeleteConnectorUseCase,
    GetConnectorCommand,
    GetConnectorUseCase,
    ListConnectorsUseCase,
    TestConnectorCommand,
    TestConnectorUseCase,
    UpdateConnectorCommand,
    UpdateConnectorUseCase,
)
from api.rate_limit import limiter
from api.src.domain.enums import ConnectorStatus, UserRole
from domain.entities.user import User
from domain.exceptions import ConnectorConnectionFailedError, EntityNotFoundError
from api.src.infrastructure.secondary.database.repositories.connector_repository import SqlConnectorRepository

CONNECTOR_NOT_FOUND = "Connector not found"
router = APIRouter(tags=["Connectors"])


# ---------------------------------------------------------------------------
# POST /organizations/{org_id}/connectors
# ---------------------------------------------------------------------------
@router.post(
    "/organizations/{org_id}/connectors",
    response_model=ConnectorResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("20/minute")
async def create_connector(
    req: Request,
    org_id: uuid.UUID,
    request: ConnectorCreateRequest,
    use_case: Annotated[ConfigureConnectorUseCase, Depends(get_configure_connector_use_case)],
    _current_user: Annotated[User, require_min_role(UserRole.MANAGER)],
):
    command = ConfigureConnectorCommand(
        organization_id=org_id,
        connector_type=request.connector_type,
        name=request.name,
        config_data=request.config_data,
    )
    try:
        return await use_case.execute(command)
    except ConnectorConnectionFailedError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ---------------------------------------------------------------------------
# GET /organizations/{org_id}/connectors
# ---------------------------------------------------------------------------
@router.get(
    "/organizations/{org_id}/connectors",
    response_model=list[ConnectorResponse],
)
async def list_connectors(
    org_id: uuid.UUID,
    repo: Annotated[SqlConnectorRepository, Depends(get_connector_repository)],
    _current_user: Annotated[User, require_min_role(UserRole.VIEWER)],
    include_inactive: Annotated[bool, Query(default=False)],
    skip: Annotated[int, Query(default=0, ge=0)],
    limit: Annotated[int, Query(default=50, ge=1, le=200)],
):
    use_case = ListConnectorsUseCase(connector_repo=repo)
    return await use_case.execute(org_id, include_inactive=include_inactive, skip=skip, limit=limit)


# ---------------------------------------------------------------------------
# GET /organizations/{org_id}/connectors/{connector_id}
# ---------------------------------------------------------------------------
@router.get(
    "/organizations/{org_id}/connectors/{connector_id}",
    response_model=ConnectorResponse,
)
async def get_connector(
    org_id: uuid.UUID,
    connector_id: uuid.UUID,
    repo: Annotated[SqlConnectorRepository, Depends(get_connector_repository)],
    _current_user: Annotated[User, require_min_role(UserRole.VIEWER)],
):
    use_case = GetConnectorUseCase(connector_repo=repo)
    try:
        return await use_case.execute(GetConnectorCommand(organization_id=org_id, connector_id=connector_id))
    except EntityNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=CONNECTOR_NOT_FOUND)


# ---------------------------------------------------------------------------
# PATCH /organizations/{org_id}/connectors/{connector_id}
# ---------------------------------------------------------------------------
@router.patch(
    "/organizations/{org_id}/connectors/{connector_id}",
    response_model=ConnectorResponse,
)
async def update_connector(
    org_id: uuid.UUID,
    connector_id: uuid.UUID,
    request: ConnectorUpdateRequest,
    repo: Annotated[SqlConnectorRepository, Depends(get_connector_repository)],
    _current_user: Annotated[User, require_min_role(UserRole.MANAGER)],
):
    use_case = UpdateConnectorUseCase(connector_repo=repo)
    resolved_status = ConnectorStatus(request.status) if request.status else None
    try:
        return await use_case.execute(
            UpdateConnectorCommand(
                organization_id=org_id,
                connector_id=connector_id,
                name=request.name,
                status=resolved_status,
            )
        )
    except EntityNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=CONNECTOR_NOT_FOUND)


# ---------------------------------------------------------------------------
# DELETE /organizations/{org_id}/connectors/{connector_id}
# ---------------------------------------------------------------------------
@router.delete(
    "/organizations/{org_id}/connectors/{connector_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_connector(
    org_id: uuid.UUID,
    connector_id: uuid.UUID,
    repo: Annotated[SqlConnectorRepository, Depends(get_connector_repository)],
    _current_user: Annotated[User, require_min_role(UserRole.ADMIN)],
):
    use_case = DeleteConnectorUseCase(connector_repo=repo)
    try:
        await use_case.execute(DeleteConnectorCommand(organization_id=org_id, connector_id=connector_id))
    except EntityNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=CONNECTOR_NOT_FOUND)


# ---------------------------------------------------------------------------
# POST /organizations/{org_id}/connectors/{connector_id}/test
# ---------------------------------------------------------------------------
@router.post(
    "/organizations/{org_id}/connectors/{connector_id}/test",
    response_model=ConnectorResponse,
)
async def test_connector(
    org_id: uuid.UUID,
    connector_id: uuid.UUID,
    repo: Annotated[SqlConnectorRepository, Depends(get_connector_repository)],
    _current_user: Annotated[User, require_min_role(UserRole.MANAGER)],
    registry: Annotated[Any, Depends(get_connector_registry)],
    encryptor: Annotated[Any, Depends(get_credential_encryptor)],
):
    use_case = TestConnectorUseCase(
        connector_repo=repo,
        connector_registry=registry,
        credential_encryptor=encryptor,
    )
    try:
        return await use_case.execute(TestConnectorCommand(organization_id=org_id, connector_id=connector_id))
    except EntityNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=CONNECTOR_NOT_FOUND)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown connector type: {e}")

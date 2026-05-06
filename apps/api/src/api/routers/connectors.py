import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from domain.entities.user import User
from domain.exceptions import ConnectorConnectionFailedError
from api.schemas.connector import ConnectorCreateRequest, ConnectorResponse
from api.dependencies import get_configure_connector_use_case, get_current_user
from application.use_cases.configure_connector import ConfigureConnectorUseCase, ConfigureConnectorCommand

router = APIRouter(tags=["Connectors"])

@router.post(
    "/organizations/{org_id}/connectors",
    response_model=ConnectorResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_connector(
    org_id: uuid.UUID,
    request: ConnectorCreateRequest,
    use_case: Annotated[ConfigureConnectorUseCase, Depends(get_configure_connector_use_case)],
    _current_user: Annotated[User, Depends(get_current_user)],
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
    except (ValueError, RuntimeError) as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno",
        ) from e

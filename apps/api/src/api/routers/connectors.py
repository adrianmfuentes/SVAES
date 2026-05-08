import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from domain.entities.user import User
from domain.exceptions import ConnectorConnectionFailedError
from api.schemas.connector import ConnectorCreateRequest, ConnectorResponse
from api.dependencies import get_configure_connector_use_case, get_current_user
from application.use_cases.configure_connector import ConfigureConnectorUseCase, ConfigureConnectorCommand

router = APIRouter( # This router does not have a prefix because the endpoints are already nested under /organizations/{org_id}
    tags=["Connectors"]
)

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
    """ Function to handle the creation of a new connector for a given organization. 
    It validates the request, executes the use case, and handles potential errors.
    Args:
        org_id (uuid.UUID): The ID of the organization for which the connector is being created
        request (ConnectorCreateRequest): The request body containing the connector details
        use_case (ConfigureConnectorUseCase): The use case instance responsible for configuring the connector,
        _current_user (User): The currently authenticated user (injected but not used in this function)
    Raises:
        HTTPException: If the connector connection fails or if there is an internal error during the process
    Returns:
        ConnectorResponse: The response containing the details of the created connector
    """
    command = ConfigureConnectorCommand(
        organization_id=org_id,
        connector_type=request.connector_type,
        name=request.name,
        config_data=request.config_data,
    )

    try:
        return await use_case.execute(command)
    except ConnectorConnectionFailedError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )
    except (ValueError, RuntimeError) as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e

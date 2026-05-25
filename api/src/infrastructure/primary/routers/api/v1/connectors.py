from uuid import UUID
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from application.ports.input.i_connector_service import IConnectorService
from core.dependencies import get_connector_service, get_current_user, CurrentUser, require_permission, require_org_access, require_connector_access
from domain.enums import ConnectorStatus
from domain.exceptions import EntityNotFoundError, ValidationError, ConnectorConnectionFailedError, DuplicateEntityError
from . import ERROR_INTERNO

router = APIRouter(tags=["Connectors"])

_LABEL_EMAIL_ATLASSIAN = "Email de Atlassian"
_LABEL_API_TOKEN = "API Token"
_LABEL_BASE_URL = "Base URL"
_LABEL_API_KEY = "API Key"
_LABEL_PERSONAL_ACCESS_TOKEN = "Personal Access Token"
_LABEL_PROJECT_ID = "Project ID"
_URL_ATLASSIAN_API = "https://api.atlassian.com"

class ConnectorCreateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    connector_type: str = Field(..., min_length=1, max_length=50)
    connector_implementation: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    credentials: dict = Field(..., description="Credenciales y configuración del conector")

class ConnectorUpdateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    config: Optional[dict] = None

class ConnectorTestRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')


@router.get("/api/v1/connectors/types")
async def list_connector_types(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Endpoint para listar los tipos de conectores disponibles y sus implementaciones.

    Retorna la lista de todas las implementaciones de conectores registradas,
    agrupadas por tipo de conector, junto con sus metadatos y esquemas de
    configuración.

    Atributos:
        - current_user: Usuario autenticado con permisos del token JWT.

    Retorna:
        - Diccionario con la lista de implementaciones y la agrupación por tipo.
        - 401 Unauthorized si el token es inválido.
        - 500 Internal Server Error para cualquier error inesperado.
    """
    from infrastructure.secondary.connectors import create_registered_connector_registry
    registry = create_registered_connector_registry()
    implementations = registry.list_all_implementations()
    result = []
    for impl_name in implementations:
        conn = registry.get_by_implementation(impl_name)
        result.append({
            "implementation": conn.get_connector_implementation(),
            "type": conn.get_connector_type(),
            "metadata": conn.get_metadata(),
            "config_schema": _get_config_schema(conn.get_connector_implementation()),
        })
    by_type = {}
    for r in result:
        ct = r["type"]
        if ct not in by_type:
            by_type[ct] = []
        by_type[ct].append({
            "implementation": r["implementation"],
            "metadata": r["metadata"],
            "config_schema": r["config_schema"],
        })
    return {"implementations": result, "by_type": by_type}


def _get_config_schema(implementation: str) -> dict:
    schemas = {
        "JIRA": {
            "email": {"type": "string", "label": _LABEL_EMAIL_ATLASSIAN, "required": True},
            "api_token": {"type": "string", "label": _LABEL_API_TOKEN, "required": True, "sensitive": True},
            "cloud_id": {"type": "string", "label": "Cloud ID", "required": False},
            "base_url": {"type": "string", "label": _LABEL_BASE_URL, "required": False, "default": _URL_ATLASSIAN_API},
        },
        "LINEAR": {
            "api_key": {"type": "string", "label": _LABEL_API_KEY, "required": True, "sensitive": True},
        },
        "TRELLO": {
            "api_key": {"type": "string", "label": _LABEL_API_KEY, "required": True, "sensitive": True},
            "token": {"type": "string", "label": "Token", "required": True, "sensitive": True},
            "board_id": {"type": "string", "label": "Board ID", "required": False},
        },
        "ASANA": {
            "token": {"type": "string", "label": _LABEL_PERSONAL_ACCESS_TOKEN, "required": True, "sensitive": True},
            "workspace": {"type": "string", "label": "Workspace GID", "required": False},
            "project_gid": {"type": "string", "label": "Project GID", "required": False},
        },
        "GITLAB": {
            "token": {"type": "string", "label": _LABEL_PERSONAL_ACCESS_TOKEN, "required": True, "sensitive": True},
            "project_id": {"type": "string", "label": _LABEL_PROJECT_ID, "required": False},
            "base_url": {"type": "string", "label": _LABEL_BASE_URL, "required": False, "default": "https://gitlab.com/api/v4"},
        },
        "GITHUB": {
            "token": {"type": "string", "label": _LABEL_PERSONAL_ACCESS_TOKEN, "required": True, "sensitive": True},
            "owner": {"type": "string", "label": "Owner/Organization", "required": False},
            "repo": {"type": "string", "label": "Repository", "required": False},
            "base_url": {"type": "string", "label": _LABEL_BASE_URL, "required": False, "default": "https://api.github.com"},
        },
        "BITBUCKET": {
            "token": {"type": "string", "label": "App Password", "required": True, "sensitive": True},
            "owner": {"type": "string", "label": "Workspace", "required": False},
            "repo": {"type": "string", "label": "Repository", "required": False},
        },
        "GITEA": {
            "token": {"type": "string", "label": "Access Token", "required": True, "sensitive": True},
            "owner": {"type": "string", "label": "Owner/Organization", "required": False},
            "repo": {"type": "string", "label": "Repository", "required": False},
            "base_url": {"type": "string", "label": _LABEL_BASE_URL, "required": True},
        },
        "CONFLUENCE": {
            "email": {"type": "string", "label": _LABEL_EMAIL_ATLASSIAN, "required": True},
            "api_token": {"type": "string", "label": _LABEL_API_TOKEN, "required": True, "sensitive": True},
            "cloud_id": {"type": "string", "label": "Cloud ID", "required": False},
            "space_key": {"type": "string", "label": "Space Key", "required": False},
            "base_url": {"type": "string", "label": _LABEL_BASE_URL, "required": False, "default": _URL_ATLASSIAN_API},
        },
        "NOTION": {
            "token": {"type": "string", "label": "Integration Token", "required": True, "sensitive": True},
            "database_id": {"type": "string", "label": "Database ID", "required": False},
        },
        "WIKIJS": {
            "token": {"type": "string", "label": _LABEL_API_TOKEN, "required": True, "sensitive": True},
            "base_url": {"type": "string", "label": _LABEL_BASE_URL, "required": True},
        },
        "BOOKSTACK": {
            "token": {"type": "string", "label": _LABEL_API_TOKEN, "required": True, "sensitive": True},
            "base_url": {"type": "string", "label": _LABEL_BASE_URL, "required": True},
        },
        "CLICKUP": {
            "token": {"type": "string", "label": _LABEL_API_TOKEN, "required": True, "sensitive": True},
            "team_id": {"type": "string", "label": "Team ID", "required": True},
            "list_id": {"type": "string", "label": "List ID", "required": False},
        },
        "TAIGA": {
            "token": {"type": "string", "label": "Auth Token", "required": True, "sensitive": True},
            "project_slug": {"type": "string", "label": "Project Slug", "required": False},
            "project": {"type": "string", "label": _LABEL_PROJECT_ID, "required": False},
        },
        "PLANE": {
            "api_key": {"type": "string", "label": _LABEL_API_KEY, "required": True, "sensitive": True},
            "instance_url": {"type": "string", "label": "Instance URL", "required": True},
            "workspace": {"type": "string", "label": "Workspace Slug", "required": True},
            "project": {"type": "string", "label": _LABEL_PROJECT_ID, "required": False},
        },
        "MIRO": {
            "token": {"type": "string", "label": "Access Token", "required": True, "sensitive": True},
        },
        "JIRA_SM": {
            "email": {"type": "string", "label": _LABEL_EMAIL_ATLASSIAN, "required": True},
            "api_token": {"type": "string", "label": _LABEL_API_TOKEN, "required": True, "sensitive": True},
            "site_id": {"type": "string", "label": "Site ID", "required": False},
            "service_desk_id": {"type": "string", "label": "Service Desk ID", "required": False},
            "base_url": {"type": "string", "label": _LABEL_BASE_URL, "required": False, "default": _URL_ATLASSIAN_API},
        },
        "GLPI": {
            "user_token": {"type": "string", "label": "User Token", "required": True, "sensitive": True},
            "app_token": {"type": "string", "label": "App Token", "required": True, "sensitive": True},
            "base_url": {"type": "string", "label": _LABEL_BASE_URL, "required": True},
        },
        "ZAMMAD": {
            "token": {"type": "string", "label": _LABEL_API_TOKEN, "required": True, "sensitive": True},
            "base_url": {"type": "string", "label": _LABEL_BASE_URL, "required": True},
        },
        "REDMINE": {
            "api_key": {"type": "string", "label": _LABEL_API_KEY, "required": True, "sensitive": True},
            "base_url": {"type": "string", "label": _LABEL_BASE_URL, "required": True},
            "project_id": {"type": "string", "label": _LABEL_PROJECT_ID, "required": False},
        },
    }
    return schemas.get(implementation, {})


@router.get("/api/v1/organizations/{org_id}/connectors")
async def list_connectors(
    org_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_org_access())],
    service: Annotated[IConnectorService, Depends(get_connector_service)],
    active_only: bool = False,
):
    """Endpoint para listar los conectores de una organización.

    Atributos:
        - org_id: UUID - El ID de la organización.
        - active_only: bool - Si se deben mostrar solo los conectores activos.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: IConnectorService - El servicio de conectores, inyectado mediante dependencias.

    Retorna:
        - Una lista de diccionarios con la información de cada conector.
        - Lanza HTTPException con status 403 si el usuario no tiene acceso a la organización.
        - Lanza HTTPException con status 500 para cualquier error inesperado.
    """
    try:
        connectors = await service.list_connectors(organization_id=org_id, active_only=active_only)
        return [
            {
                "id": str(c.id),
                "connector_type": c.connector_type,
                "name": c.name,
                "status": c.status.value,
                "created_at": c.created_at.isoformat(),
            }
            for c in connectors
        ]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


@router.post("/api/v1/organizations/{org_id}/connectors", status_code=status.HTTP_201_CREATED)
async def register_connector(
    org_id: UUID,
    payload: ConnectorCreateRequest,
    current_user: Annotated[CurrentUser, Depends(require_org_access())],
    service: Annotated[IConnectorService, Depends(get_connector_service)],
):
    """Endpoint para registrar un nuevo conector en una organización.

    Atributos:
        - org_id: UUID - El ID de la organización.
        - payload: ConnectorCreateRequest - El cuerpo de la solicitud, que incluye el tipo, nombre y configuración del conector.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: IConnectorService - El servicio de conectores, inyectado mediante dependencias.

    Retorna:
        - Un diccionario con el ID, nombre y estado del conector registrado.
        - Lanza HTTPException con status 403 si el usuario no tiene acceso a la organización.
        - Lanza HTTPException con status 422 si los datos de entrada son inválidos.
        - Lanza HTTPException con status 500 para cualquier otro error inesperado.
    """
    try:
        connector = await service.register_connector(
            organization_id=org_id,
            connector_type=payload.connector_type,
            connector_implementation=payload.connector_implementation,
            name=payload.name,
            config=payload.credentials,
            requested_by=current_user.user_id,
        )
        return {"id": str(connector.id), "name": connector.name, "status": connector.status.value}
    except DuplicateEntityError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


@router.patch("/api/v1/organizations/{org_id}/connectors/{connector_id}")
async def update_connector(
    org_id: UUID,
    connector_id: UUID,
    payload: ConnectorUpdateRequest,
    current_user: Annotated[CurrentUser, Depends(require_org_access())],
    service: Annotated[IConnectorService, Depends(get_connector_service)],
    _: Annotated[None, Depends(require_connector_access())],
):
    """Endpoint para actualizar un conector existente.

    Atributos:
        - connector_id: UUID - El ID del conector a actualizar.
        - payload: ConnectorUpdateRequest - El cuerpo de la solicitud, que incluye el nombre y configuración actualizados del conector.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: IConnectorService - El servicio de conectores, inyectado mediante dependencias.

    Retorna:
        - Un diccionario con el ID, nombre y estado del conector actualizado.
        - Lanza HTTPException con status 403 si el usuario no tiene acceso.
        - Lanza HTTPException con status 404 si el conector no es encontrado.
        - Lanza HTTPException con status 422 si los datos de entrada son inválidos.
        - Lanza HTTPException con status 500 para cualquier otro error inesperado.
    """
    try:
        connector = await service.update_connector(
            connector_id=connector_id,
            name=payload.name,
            config=payload.config,
            requested_by=current_user.user_id,
        )
        return {"id": str(connector.id), "name": connector.name, "status": connector.status.value}
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


@router.delete("/api/v1/organizations/{org_id}/connectors/{connector_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connector(
    org_id: UUID,
    connector_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_org_access())],
    _: Annotated[None, Depends(require_connector_access())],
    service: Annotated[IConnectorService, Depends(get_connector_service)],
):
    """Endpoint para eliminar un conector existente.

    Atributos:
        - connector_id: UUID - El ID del conector a eliminar.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: IConnectorService - El servicio de conectores, inyectado mediante dependencias.

    Retorna:
        - No retorna contenido (204) si la eliminación es exitosa.
        - Lanza HTTPException con status 403 si el usuario no tiene acceso.
        - Lanza HTTPException con status 404 si el conector no es encontrado.
        - Lanza HTTPException con status 500 para cualquier otro error inesperado.
    """
    try:
        await service.delete_connector(
            connector_id=connector_id,
            requested_by=current_user.user_id,
        )
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


@router.post("/api/v1/organizations/{org_id}/connectors/{connector_id}/test", status_code=status.HTTP_200_OK)
async def test_connector(
    request: Request,
    org_id: UUID,
    connector_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_org_access())],
    _: Annotated[None, Depends(require_connector_access())],
    service: Annotated[IConnectorService, Depends(get_connector_service)],
):
    """Endpoint para probar la conexión de un conector existente.

    Atributos:
        - connector_id: UUID - El ID del conector a probar.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: IConnectorService - El servicio de conectores, inyectado mediante dependencias.

    Retorna:
        - Un diccionario con el resultado de la prueba y un mensaje informativo.
        - Lanza HTTPException con status 403 si el usuario no tiene acceso.
        - Lanza HTTPException con status 404 si el conector no es encontrado.
        - Lanza HTTPException con status 409 si la conexión falla.
        - Lanza HTTPException con status 500 para cualquier otro error inesperado.
    """
    try:
        result = await service.test_connector_connection(
            connector_id=connector_id,
            requested_by=current_user.user_id,
        )
        return {"success": result, "message": "Conexión exitosa" if result else "Conexión fallida"}
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ConnectorConnectionFailedError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)

from uuid import UUID
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from features.connectors.application.ports.i_connector_service import IConnectorService
from bootstrap.dependencies import (
    get_connector_service,
    CurrentUser,
    require_org_access,
    require_connector_access,
)
from shared.domain.enums import ConnectorStatus
from shared.domain.exceptions import (
    EntityNotFoundError,
    ValidationError,
    ConnectorConnectionFailedError,
    DuplicateEntityError,
)
from shared.infrastructure.api_errors import handle_internal_errors


router = APIRouter(tags=["Connectors"])


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


class ConnectorWebhookConfigRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    enabled: bool
    regenerate_secret: bool = False


@router.get("/api/v1/organizations/{org_id}/connectors")
@handle_internal_errors
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
    connectors = await service.list_connectors(organization_id=org_id, active_only=active_only)
    return [
        {
            "id": str(c.id),
            "connector_type": c.connector_type,
            "connector_implementation": c.connector_implementation,
            "name": c.name,
            "status": c.status.value,
            "created_at": c.created_at.isoformat(),
            "last_tested_at": c.last_tested_at.isoformat() if c.last_tested_at else None,
            "webhook_enabled": c.webhook_enabled,
        }
        for c in connectors
    ]


@router.post("/api/v1/organizations/{org_id}/connectors", status_code=status.HTTP_201_CREATED)
@handle_internal_errors
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
        return {
            "id": str(connector.id),
            "name": connector.name,
            "connector_type": connector.connector_type,
            "status": connector.status.value,
            "last_tested_at": connector.last_tested_at.isoformat() if connector.last_tested_at else None,
        }
    except DuplicateEntityError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))


@router.patch("/api/v1/organizations/{org_id}/connectors/{connector_id}")
@handle_internal_errors
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
        return {
            "id": str(connector.id),
            "name": connector.name,
            "connector_type": connector.connector_type,
            "status": connector.status.value,
            "last_tested_at": connector.last_tested_at.isoformat() if connector.last_tested_at else None,
        }
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))


class ConnectorToggleRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    status: ConnectorStatus


@router.post("/api/v1/organizations/{org_id}/connectors/{connector_id}/toggle", status_code=status.HTTP_200_OK)
@handle_internal_errors
async def toggle_connector_status(
    org_id: UUID,
    connector_id: UUID,
    payload: ConnectorToggleRequest,
    current_user: Annotated[CurrentUser, Depends(require_org_access())],
    service: Annotated[IConnectorService, Depends(get_connector_service)],
    _: Annotated[None, Depends(require_connector_access())],
):
    """Endpoint para cambiar el estado de un conector existente.

    Atributos:
        - connector_id: UUID - El ID del conector cuyo estado se quiere cambiar.
        - payload: ConnectorToggleRequest - El nuevo estado (ACTIVO o INACTIVO).
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: El servicio de conectores.

    Retorna:
        - Un diccionario con el ID, nombre y estado del conector actualizado.
        - Lanza HTTPException con status 403 si el usuario no tiene acceso.
        - Lanza HTTPException con status 404 si el conector no es encontrado.
        - Lanza HTTPException con status 422 si los datos de entrada son inválidos.
        - Lanza HTTPException con status 500 para cualquier otro error inesperado.
    """
    try:
        connector = await service.toggle_connector_status(
            connector_id=connector_id,
            status=payload.status,
            requested_by=current_user.user_id,
        )
        return {
            "id": str(connector.id),
            "name": connector.name,
            "connector_type": connector.connector_type,
            "status": connector.status.value,
            "last_tested_at": connector.last_tested_at.isoformat() if connector.last_tested_at else None,
        }
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))


@router.post("/api/v1/organizations/{org_id}/connectors/{connector_id}/webhook", status_code=status.HTTP_200_OK)
@handle_internal_errors
async def configure_connector_webhook(
    org_id: UUID,
    connector_id: UUID,
    payload: ConnectorWebhookConfigRequest,
    current_user: Annotated[CurrentUser, Depends(require_org_access())],
    service: Annotated[IConnectorService, Depends(get_connector_service)],
    _: Annotated[None, Depends(require_connector_access())],
):
    """Habilita/deshabilita la verificación automática vía webhook entrante
    para un conector de tipo REPO_CODIGO (GitHub/GitLab/Bitbucket/Gitea).

    Atributos:
        - connector_id: UUID - El ID del conector a configurar.
        - payload: ConnectorWebhookConfigRequest - enabled + regenerate_secret opcional.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: IConnectorService, inyectado mediante dependencias.

    Retorna:
        - webhook_path: ruta relativa a la que el proveedor externo debe apuntar
          (el origen ya lo sirve el mismo nginx que la SPA).
        - webhook_secret: solo se devuelve la vez que se genera (primera activación
          o regenerate_secret=True); no se puede recuperar después, solo regenerar.
        - Lanza HTTPException con status 403 si el usuario no tiene acceso.
        - Lanza HTTPException con status 404 si el conector no es encontrado.
        - Lanza HTTPException con status 422 si el conector no es de tipo REPO_CODIGO.
        - Lanza HTTPException con status 500 para cualquier otro error inesperado.
    """
    try:
        connector, secret = await service.configure_webhook(
            connector_id=connector_id,
            enabled=payload.enabled,
            requested_by=current_user.user_id,
            regenerate_secret=payload.regenerate_secret,
        )
        return {
            "id": str(connector.id),
            "webhook_enabled": connector.webhook_enabled,
            "webhook_path": f"/api/v1/webhooks/source-control/{connector.id}",
            "webhook_secret": secret,
        }
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))


@router.delete("/api/v1/organizations/{org_id}/connectors/{connector_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_internal_errors
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


@router.post("/api/v1/organizations/{org_id}/connectors/{connector_id}/test", status_code=status.HTTP_200_OK)
@handle_internal_errors
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
        connector = await service.test_connector_connection(
            connector_id=connector_id,
            requested_by=current_user.user_id,
        )
        return {
            "id": str(connector.id),
            "name": connector.name,
            "connector_type": connector.connector_type,
            "status": connector.status.value,
            "last_tested_at": connector.last_tested_at.isoformat() if connector.last_tested_at else None,
        }
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ConnectorConnectionFailedError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/api/v1/organizations/{org_id}/connectors/{connector_id}/browse")
async def browse_connector_items(
    org_id: UUID,
    connector_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_org_access())],
    _: Annotated[None, Depends(require_connector_access())],
    service: Annotated[IConnectorService, Depends(get_connector_service)],
    q: str = "",
):
    """Lista items del sistema externo del conector para facilitar la selección en formularios."""
    try:
        return await service.browse_connector_items(connector_id=connector_id, query=q)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except ConnectorConnectionFailedError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

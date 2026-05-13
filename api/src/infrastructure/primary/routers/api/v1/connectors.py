from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from application.ports.input.i_connector_service import IConnectorService
from core.dependencies import get_connector_service, get_current_user_id
from domain.enums import ConnectorStatus
from domain.exceptions import EntityNotFoundError, ValidationError, ConnectorConnectionFailedError

router = APIRouter(tags=["Connectors"])

class ConnectorCreateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    connector_type: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    config: dict = Field(..., description="Configuración del conector (credenciales, endpoints, etc.)")

class ConnectorUpdateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    config: Optional[dict] = None

class ConnectorTestRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    pass


@router.get("/api/v1/organizations/{org_id}/connectors")
async def list_connectors(
    org_id: UUID,
    active_only: bool = True,
    service: IConnectorService = Depends(get_connector_service),
):
    """Endpoint para listar los conectores de una organización.

    Atributos:
        - org_id: UUID - El ID de la organización.
        - active_only: bool - Si se deben mostrar solo los conectores activos.
        - service: IConnectorService - El servicio de conectores, inyectado mediante dependencias.

    Retorna:
        - Una lista de diccionarios con la información de cada conector.
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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/api/v1/organizations/{org_id}/connectors", status_code=status.HTTP_201_CREATED)
async def register_connector(
    org_id: UUID,
    payload: ConnectorCreateRequest,
    user_id: UUID = Depends(get_current_user_id),
    service: IConnectorService = Depends(get_connector_service),
):
    """Endpoint para registrar un nuevo conector en una organización.

    Atributos:
        - org_id: UUID - El ID de la organización.
        - payload: ConnectorCreateRequest - El cuerpo de la solicitud, que incluye el tipo, nombre y configuración del conector.
        - user_id: UUID - El ID del usuario que realiza la solicitud.
        - service: IConnectorService - El servicio de conectores, inyectado mediante dependencias.

    Retorna:
        - Un diccionario con el ID, nombre y estado del conector registrado.
        - Lanza HTTPException con status 422 si los datos de entrada son inválidos.
        - Lanza HTTPException con status 500 para cualquier otro error inesperado.
    """
    try:
        connector = await service.register_connector(
            organization_id=org_id,
            connector_type=payload.connector_type,
            name=payload.name,
            config=payload.config,
        )
        return {"id": str(connector.id), "name": connector.name, "status": connector.status.value}
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.patch("/api/v1/connectors/{connector_id}")
async def update_connector(
    connector_id: UUID,
    payload: ConnectorUpdateRequest,
    service: IConnectorService = Depends(get_connector_service),
):
    """Endpoint para actualizar un conector existente.

    Atributos:
        - connector_id: UUID - El ID del conector a actualizar.
        - payload: ConnectorUpdateRequest - El cuerpo de la solicitud, que incluye el nombre y configuración actualizados del conector.
        - service: IConnectorService - El servicio de conectores, inyectado mediante dependencias.

    Retorna:
        - Un diccionario con el ID, nombre y estado del conector actualizado.
        - Lanza HTTPException con status 404 si el conector no es encontrado.
        - Lanza HTTPException con status 422 si los datos de entrada son inválidos.
        - Lanza HTTPException con status 500 para cualquier otro error inesperado.
    """
    try:
        connector = await service.update_connector(
            connector_id=connector_id,
            name=payload.name,
            config=payload.config,
        )
        return {"id": str(connector.id), "name": connector.name, "status": connector.status.value}
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/api/v1/connectors/{connector_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connector(
    connector_id: UUID,
    service: IConnectorService = Depends(get_connector_service),
):
    """Endpoint para eliminar un conector existente. 

    Atributos:
        - connector_id: UUID - El ID del conector a eliminar.
        - service: IConnectorService - El servicio de conectores, inyectado mediante dependencias.

    Retorna:
        - No retorna contenido (204) si la eliminación es exitosa.
        - Lanza HTTPException con status 404 si el conector no es encontrado.
        - Lanza HTTPException con status 500 para cualquier otro error inesperado.
    """
    try:
        await service.delete_connector(connector_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/api/v1/connectors/{connector_id}/test", status_code=status.HTTP_200_OK)
async def test_connector(
    connector_id: UUID,
    service: IConnectorService = Depends(get_connector_service),
):
    """Endpoint para probar la conexión de un conector existente.

    Atributos:
        - connector_id: UUID - El ID del conector a probar.
        - service: IConnectorService - El servicio de conectores, inyectado mediante dependencias.

    Retorna:
        - Un diccionario con el resultado de la prueba y un mensaje informativo.
        - Lanza HTTPException con status 404 si el conector no es encontrado.
        - Lanza HTTPException con status 409 si la conexión falla.
        - Lanza HTTPException con status 500 para cualquier otro error inesperado.
    """
    try:
        result = await service.test_connector_connection(connector_id)
        return {"success": result, "message": "Conexión exitosa" if result else "Conexión fallida"}
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ConnectorConnectionFailedError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
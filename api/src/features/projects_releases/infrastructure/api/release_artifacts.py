from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from typing import Annotated, Optional
from starlette.responses import Response
from features.projects_releases.application.ports.i_release_service import IReleaseService
from features.projects_releases.application.ports.i_artifact_service import IArtifactService
from features.connectors.application.ports.i_connector_service import IConnectorService
from bootstrap.dependencies import (
    get_release_service,
    get_artifact_service,
    get_connector_service,
    CurrentUser,
    require_permission,
    require_release_access,
)
from shared.domain.enums import ArtifactType, Permission
from shared.domain.exceptions import ValidationError
from shared.infrastructure.api_errors import ERROR_INTERNO, handle_internal_errors
from .releases_schemas import ArtifactCreateRequest, RELEASE_NOT_FOUND


router = APIRouter(tags=["Releases"])


@router.get("/api/v1/releases/{id}/artifacts")
@handle_internal_errors
async def list_artifacts(
    id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.VIEW_ORG_PROJECTS))],
    _: Annotated[None, Depends(require_release_access())],
    service: Annotated[IArtifactService, Depends(get_artifact_service)],
):
    """Lista todos los artefactos asociados a una release específica por su ID.

    Atributos:
        - id: ID de la release de la que se quieren listar los artefactos.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: Instancia del servicio de artefactos (inyección de dependencias).

    Retorna:
        - 200 OK con la lista de artefactos si se encuentran exitosamente
        - 403 Forbidden si el usuario no tiene acceso a la release
        - 404 Not Found si la release no se encuentra
        - 500 Internal Server Error para cualquier otro error inesperado
    """
    try:
        artifacts = await service.list_artifacts(release_id=id)
        return artifacts
    except HTTPException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RELEASE_NOT_FOUND)


@router.post("/api/v1/releases/{id}/artifacts", status_code=status.HTTP_201_CREATED)
async def add_artifact(
    id: UUID,
    payload: ArtifactCreateRequest,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.UPDATE_OWN_RELEASES))],
    _: Annotated[None, Depends(require_release_access())],
    service: Annotated[IArtifactService, Depends(get_artifact_service)],
    connector_service: Annotated[IConnectorService, Depends(get_connector_service)],
    release_service: Annotated[IReleaseService, Depends(get_release_service)],
):
    """Agrega un nuevo artefacto a una release específica por su ID.

    Atributos:
        - id: ID de la release a la que se quiere agregar el artefacto.
        - payload: Datos del artefacto a agregar (tipo, conector, referencia externa
            y descripción).
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: Instancia del servicio de artefactos (inyección de dependencias).

    Retorna:
        - 201 Created con el ID del artefacto creado si se agrega exitosamente
        - 403 Forbidden si el usuario no tiene acceso a la release
        - 404 Not Found si la release no se encuentra
        - 422 Unprocessable Entity si los datos de entrada no son válidos
        - 500 Internal Server Error para cualquier otro error inesperado
    """
    try:
        release = await release_service.get_release(id)
        if not release:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RELEASE_NOT_FOUND)
        await connector_service.verify_artifact_ref(
            connector_id=payload.connector_instance_id,
            external_ref=payload.external_ref,
            organization_id=release.organization_id,
        )
        artifact = await service.add_artifact(
            release_id=id,
            connector_instance_id=payload.connector_instance_id,
            connector_implementation=payload.connector_implementation,
            artifact_type=payload.artifact_type,
            external_ref=payload.external_ref,
            description=payload.description,
            metadata=payload.metadata,
        )
        return {"id": artifact.id}
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))
    except HTTPException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RELEASE_NOT_FOUND)
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


@router.delete("/api/v1/releases/{id}/artifacts/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_internal_errors
async def remove_artifact(
    id: UUID,
    artifact_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.UPDATE_OWN_RELEASES))],
    _: Annotated[None, Depends(require_release_access())],
    service: Annotated[IArtifactService, Depends(get_artifact_service)],
):
    """Elimina un artefacto específico de una release por sus IDs.

    Atributos:
        - id: ID de la release de la que se quiere eliminar el artefacto.
        - artifact_id: ID del artefacto a eliminar.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: Instancia del servicio de artefactos (inyección de dependencias).

    Retorna:
        - 204 No Content si se elimina exitosamente
        - 403 Forbidden si el usuario no tiene acceso a la release
        - 404 Not Found si la release o el artefacto no se encuentran
        - 500 Internal Server Error para cualquier otro error inesperado
    """
    try:
        await service.remove_artifact(release_id=id, artifact_id=artifact_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RELEASE_NOT_FOUND)

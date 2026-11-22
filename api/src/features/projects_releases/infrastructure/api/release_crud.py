from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from typing import Annotated, Optional
from features.projects_releases.application.ports.i_release_service import IReleaseService
from bootstrap.dependencies import (
    get_release_service,
    CurrentUser,
    ProjectAccess,
    require_permission,
    require_project_access,
    require_release_access,
    require_role,
)
from shared.domain.enums import ReleaseStatus, Permission, UserRole
from shared.domain.exceptions import ValidationError, EntityNotFoundError, DuplicateEntityError
from shared.infrastructure.api_errors import ERROR_INTERNO, handle_internal_errors
from .releases_schemas import RELEASE_NOT_FOUND


router = APIRouter(tags=["Releases"])


_STATUS_TO_VERDICT = {
    ReleaseStatus.VALIDA: "VALID",
    ReleaseStatus.CON_ADVERTENCIAS: "WITH_WARNINGS",
    ReleaseStatus.NO_VALIDA: "INVALID",
}


class ReleaseCreateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(..., min_length=1, max_length=100)
    version: str
    description: str = Field(default="", max_length=1000)
    profile_id: Optional[UUID] = None


class ReleaseUpdateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    version: Optional[str] = None
    description: Optional[str] = Field(default=None, max_length=1000)
    status: Optional[ReleaseStatus] = None


@router.post("/api/v1/projects/{project_id}/releases", status_code=status.HTTP_201_CREATED)
async def create_release(
    project_id: UUID,
    payload: ReleaseCreateRequest,
    project_access: Annotated[ProjectAccess, Depends(require_project_access())],
    service: Annotated[IReleaseService, Depends(get_release_service)],
):
    """ Crea una nueva release dentro del proyecto especificado.

    Atributos:
        - project_id: ID del proyecto al que pertenece la release.
        - payload: Datos de la release a crear (nombre, versión, descripción).
        - project_access: Acceso validado al proyecto con datos del usuario autenticado.
        - service: Instancia del servicio de releases (inyección de dependencias).

    Retorna:
        - 201 Created con el ID y estado inicial de la release si se crea exitosamente
        - 403 Forbidden si el usuario no tiene permisos en el proyecto
        - 422 Unprocessable Entity si los datos de entrada no son válidos
        - 500 Internal Server Error para cualquier otro error inesperado
    """
    try:
        release = await service.create_release(
            name=payload.name,
            version=payload.version,
            project_id=project_id,
            user_id=project_access.user.user_id,
            description=payload.description,
            profile_id=payload.profile_id,
        )
        return {
            "id": release.id,
            "status": release.status
        }
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))
    except DuplicateEntityError:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


@router.get("/api/v1/projects/{project_id}/releases")
@handle_internal_errors
async def list_releases(
    project_id: UUID,
    project_access: Annotated[ProjectAccess, Depends(require_project_access())],
    service: Annotated[IReleaseService, Depends(get_release_service)],
):
    """
    Lista todas las releases asociadas al proyecto especificado.

    Atributos:
        - project_id: ID del proyecto del que se quieren listar las releases.
        - project_access: Acceso validado al proyecto con datos del usuario autenticado.
        - service: Instancia del servicio de releases (inyección de dependencias).

    Retorna:
        - 200 OK con la lista de releases si se encuentran exitosamente
        - 403 Forbidden si el usuario no tiene acceso al proyecto
        - 500 Internal Server Error para cualquier otro error inesperado
    """
    releases = await service.list_releases(project_id=project_id)
    return [
        {
            "id": str(r.id),
            "name": r.name,
            "version": r.version,
            "status": r.status.value if r.status else None,
            "verdict": _STATUS_TO_VERDICT.get(r.status, "NOT_EVALUATED"),
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "project_name": r.project_name,
        }
        for r in releases
    ]


@router.get("/api/v1/releases")
@handle_internal_errors
async def list_global_releases(
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.VIEW_ORG_PROJECTS))],
    service: Annotated[IReleaseService, Depends(get_release_service)],
):
    org_id = None if current_user.role == UserRole.U3 else current_user.organization_id
    releases = await service.list_org_releases(organization_id=org_id)
    return [
        {
            "id": str(r.id),
            "name": r.name,
            "verdict": _STATUS_TO_VERDICT.get(r.status, "NOT_EVALUATED"),
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "created_by": str(r.created_by) if r.created_by else None,
        }
        for r in releases
    ]


@router.get("/api/v1/releases/{id}")
async def get_release(
    id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.VIEW_ORG_PROJECTS))],
    _: Annotated[None, Depends(require_release_access())],
    service: Annotated[IReleaseService, Depends(get_release_service)],
):
    """Obtiene los detalles de una release específica por su ID.

    Atributos:
        - id: ID de la release a obtener.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: Instancia del servicio de releases (inyección de dependencias).

    Retorna:
        - 200 OK con los detalles de la release si se encuentra exitosamente
        - 403 Forbidden si el usuario no tiene acceso a la release
        - 404 Not Found si la release no se encuentra
        - 500 Internal Server Error para cualquier otro error inesperado
    """
    try:
        release = await service.get_release(release_id=id)
        if not release:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RELEASE_NOT_FOUND)
        return release
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


@router.patch("/api/v1/releases/{id}")
@handle_internal_errors
async def update_release(
    id: UUID,
    payload: ReleaseUpdateRequest,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.UPDATE_OWN_RELEASES))],
    _: Annotated[None, Depends(require_release_access())],
    service: Annotated[IReleaseService, Depends(get_release_service)],
):
    try:
        kwargs = {k: v for k, v in payload.model_dump().items() if v is not None}
        release = await service.update_release(release_id=id, **kwargs)
        return release
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.delete("/api/v1/releases/{id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_internal_errors
async def delete_release(
    id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.UPDATE_OWN_RELEASES))],
    _: Annotated[None, Depends(require_release_access())],
    service: Annotated[IReleaseService, Depends(get_release_service)],
):
    """Elimina una release específica por su ID.

    Atributos:
        - id: ID de la release a eliminar.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: Instancia del servicio de releases (inyección de dependencias).

    Retorna:
        - 204 No Content si se elimina exitosamente
        - 403 Forbidden si el usuario no tiene acceso a la release
        - 404 Not Found si la release no se encuentra
        - 500 Internal Server Error para cualquier otro error inesperado
    """
    await service.delete_release(release_id=id)


@router.post("/api/v1/releases/{id}/archive", status_code=status.HTTP_200_OK)
@handle_internal_errors
async def archive_release(
    id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.ARCHIVE_RELEASE))],
    _: Annotated[None, Depends(require_release_access())],
    service: Annotated[IReleaseService, Depends(get_release_service)],
):
    """Archiva una release específica por su ID, cambiando su estado a 'ARCHIVADA'.

    Atributos:
        - id: ID de la release a archivar.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: Instancia del servicio de releases (inyección de dependencias).

    Retorna:
        - 200 OK con un mensaje de éxito si se archiva exitosamente
        - 403 Forbidden si el usuario no tiene permiso para archivar
        - 404 Not Found si la release no se encuentra
        - 500 Internal Server Error para cualquier otro error inesperado
    """
    await service.update_status(release_id=id, status=ReleaseStatus.ARCHIVADA)
    return {"message": "Release archivada con éxito"}


@router.post("/api/v1/releases/{id}/restore", status_code=status.HTTP_200_OK)
@handle_internal_errors
async def restore_release(
    id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.U3))],
    _: Annotated[None, Depends(require_release_access())],
    service: Annotated[IReleaseService, Depends(get_release_service)],
):
    """Restaura una release archivada, cambiando su estado al anterior (BORRADOR).

    Atributos:
        - id: ID de la release a restaurar.
        - current_user: Usuario autenticado con rol U3 (reservado a administrador global).
        - service: Instancia del servicio de releases (inyección de dependencias).

    Retorna:
        - 200 OK con un mensaje de éxito si se restaura exitosamente
        - 403 Forbidden si el usuario no tiene rol U3
        - 404 Not Found si la release no se encuentra o no está archivada
        - 500 Internal Server Error para cualquier otro error inesperado
    """
    try:
        await service.restore_release(release_id=id)
        return {"message": "Release restaurada con éxito"}
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

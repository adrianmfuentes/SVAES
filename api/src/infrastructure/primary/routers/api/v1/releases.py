import os
import tempfile
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from fastapi.responses import FileResponse
from typing import Annotated, Literal, List, Optional
from starlette.responses import Response

from application.ports.input.i_release_service import IReleaseService
from application.ports.input.i_artifact_service import IArtifactService
from application.ports.input.i_verification_service import IVerificationService
from application.ports.input.i_export_service import IExportService

from core.dependencies import get_release_service, get_artifact_service, get_verification_service, get_export_service, get_current_user, CurrentUser, ProjectAccess, require_permission, require_project_access, require_release_access, require_role
from domain.enums import ArtifactType, ReleaseStatus, Permission, UserRole
from domain.exceptions import ValidationError, EntityNotFoundError, DuplicateEntityError
from . import ERROR_INTERNO

# Constantes de mensajes de error
RELEASE_NOT_FOUND = "Release no encontrada"

_STATUS_TO_VERDICT = {
    ReleaseStatus.VALIDA: "VALID",
    ReleaseStatus.CON_ADVERTENCIAS: "WITH_WARNINGS",
    ReleaseStatus.NO_VALIDA: "INVALID",
}
RELEASE_OR_VERIFICATION_NOT_FOUND = "Release o verificación no encontradas"

# Quitamos el prefix global para poder manejar tanto rutas de proyectos como de releases directas
router = APIRouter(tags=["Releases"])

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

class ArtifactCreateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    artifact_type: ArtifactType
    connector_instance_id: UUID
    connector_implementation: str
    external_ref: str
    description: str = ""
    metadata: Optional[dict] = None


# ==========================
# BLOQUE 1: COLECCIÓN DEL PROYECTO
# ==========================
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
    try:
        releases = await service.list_releases(project_id=project_id)
        return releases
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


# ===================================
# BLOQUE 2: OPERACIONES SOBRE LA RELEASE
# ===================================
@router.get("/api/v1/releases")
async def list_global_releases(
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.VIEW_OWN_PROJECTS))],
    service: Annotated[IReleaseService, Depends(get_release_service)],
):
    try:
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
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


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
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


@router.delete("/api/v1/releases/{id}", status_code=status.HTTP_204_NO_CONTENT)
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
    try:
        await service.delete_release(release_id=id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


@router.post("/api/v1/releases/{id}/archive", status_code=status.HTTP_200_OK)
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
    try:
        await service.update_status(release_id=id, status=ReleaseStatus.ARCHIVADA)
        return {"message": "Release archivada con éxito"}
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


@router.post("/api/v1/releases/{id}/restore", status_code=status.HTTP_200_OK)
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
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


# ========================
# BLOQUE 3: GESTIÓN DE ARTEFACTOS
# ========================
@router.get("/api/v1/releases/{id}/artifacts")
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
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)

@router.post("/api/v1/releases/{id}/artifacts", status_code=status.HTTP_201_CREATED)
async def add_artifact(
    id: UUID,
    payload: ArtifactCreateRequest,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.UPDATE_OWN_RELEASES))],
    _: Annotated[None, Depends(require_release_access())],
    service: Annotated[IArtifactService, Depends(get_artifact_service)],
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
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


# ============================
# BLOQUE 4: VERIFICACIÓN E HISTORIAL
# ============================
@router.post("/api/v1/releases/{id}/verify", status_code=status.HTTP_202_ACCEPTED)
async def verify_release(
    id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.EXECUTE_VERIFICATION))],
    _: Annotated[None, Depends(require_release_access())],
    service: Annotated[IVerificationService, Depends(get_verification_service)],
):
    """ Lanza la verificación asíncrona.

    Atributos:
        - id: ID de la release a verificar.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: Instancia del servicio de verificaciones (inyección de dependencias).

    Retorna:
        - 202 Accepted con el ID de la tarea de verificación y el nuevo estado de
            la release si se lanza exitosamente
        - 403 Forbidden si el usuario no tiene permiso para verificar
        - 404 Not Found si la release no se encuentra
        - 409 Conflict si la release no se encuentra en un estado válido para iniciar la verificación
        - 500 Internal Server Error para cualquier otro error inesperado
    """
    try:
        task_id = await service.launch_verification(
            release_id=id,
            requested_by=current_user.user_id,
        )
        return {
            "task_id": task_id,
            "status": ReleaseStatus.EN_VERIFICACION
        }
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/api/v1/releases/{id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_verification(
    id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.EXECUTE_VERIFICATION))],
    _: Annotated[None, Depends(require_release_access())],
    service: Annotated[IVerificationService, Depends(get_verification_service)],
):
    """ Cancela una verificación en curso y revierte la release a su estado anterior.

    Atributos:
        - id: ID de la release cuya verificación se quiere cancelar.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: Instancia del servicio de verificaciones (inyección de dependencias).

    Retorna:
        - 200 OK si la verificación se cancela exitosamente
        - 403 Forbidden si el usuario no tiene permiso
        - 404 Not Found si la release no se encuentra
        - 409 Conflict si la release no está en verificación
    """
    try:
        cancelled = await service.cancel_verification(release_id=id)
        return {"cancelled": cancelled}
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


@router.get("/api/v1/releases/{id}/results")
async def get_results(
    id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.VIEW_OWN_HISTORY))],
    _: Annotated[None, Depends(require_release_access())],
    service: Annotated[IVerificationService, Depends(get_verification_service)],
):
    """Obtiene el historial paginado de verificaciones de esta release.

    Atributos:
        - id: UUID - ID de la release de la que se quieren obtener las verificaciones.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: Instancia del servicio de verificaciones (inyección de dependencias).

    Retorna:
        - 200 OK con la lista paginada de verificaciones si se encuentran
        - 403 Forbidden si el usuario no tiene acceso
        - 404 Not Found si la release no se encuentra
        - 500 Internal Server Error para cualquier error inesperado
    """
    try:
        results = await service.get_verification_history(release_id=id)
        return results
    except HTTPException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RELEASE_NOT_FOUND)
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


@router.get("/api/v1/releases/{id}/results/{rid}")
async def get_result_detail(
    id: UUID,
    rid: UUID,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.VIEW_OWN_HISTORY))],
    _: Annotated[None, Depends(require_release_access())],
    service: Annotated[IVerificationService, Depends(get_verification_service)],
):
    """Obtiene el informe detallado de una verificación individual.

    Atributos:
        - id: UUID - ID de la release a la que pertenece la verificación.
        - rid: UUID - ID de la verificación individual de la que se quieren obtener los detalles.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: Instancia del servicio de verificaciones (inyección de dependencias).

    Retorna:
        - 200 OK con el informe detallado de la verificación si se encuentra exitosamente
        - 403 Forbidden si el usuario no tiene acceso
        - 404 Not Found si la release o la verificación no se encuentran
        - 500 Internal Server Error para cualquier error inesperado
    """
    try:
        result = await service.get_verification_result(release_id=id, result_id=rid)
        return result
    except HTTPException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RELEASE_OR_VERIFICATION_NOT_FOUND)
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


@router.get("/api/v1/releases/{id}/verifications/{verification_id}")
async def get_verification_detail(
    id: UUID,
    verification_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.VIEW_OWN_HISTORY))],
    _: Annotated[None, Depends(require_release_access())],
    service: Annotated[IVerificationService, Depends(get_verification_service)],
):
    """Obtiene el informe detallado de una verificación individual.

    Atributos:
        - id: ID de la release a la que pertenece la verificación.
        - verification_id: ID de la verificación individual de la que se quieren obtener los detalles.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: Instancia del servicio de verificaciones (inyección de dependencias).

    Retorna:
        - 200 OK con el informe detallado de la verificación si se encuentra exitosamente
        - 403 Forbidden si el usuario no tiene acceso
        - 404 Not Found si la release o la verificación no se encuentran
        - 500 Internal Server Error para cualquier otro error inesperado
    """
    try:
        result = await service.get_verification_result(release_id=id, result_id=verification_id)
        return result
    except HTTPException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RELEASE_OR_VERIFICATION_NOT_FOUND)
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


@router.get("/api/v1/releases/{id}/results/{rid}/export", status_code=status.HTTP_200_OK)
async def export_verification_result_pdf(
    id: UUID,
    rid: UUID,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.VIEW_OWN_HISTORY))],
    _: Annotated[None, Depends(require_release_access())],
    service: Annotated[IVerificationService, Depends(get_verification_service)],
    export_service: Annotated[IExportService, Depends(get_export_service)],
    format: Annotated[Literal["pdf"], Query(description="Formato de exportación")] = "pdf",
    lang: Annotated[str, Query(description="Idioma del informe (es/en)")] = "es",
):
    """Exporta el resultado de una verificación a formato PDF.

    Atributos:
        - id: ID de la release a la que pertenece la verificación.
        - rid: ID de la verificación individual a exportar.
        - format: Formato de exportación (solo PDF soportado actualmente).
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: Instancia del servicio de verificaciones (inyección de dependencias).
        - export_service: Instancia del servicio de exportación (inyección de dependencias).

    Retorna:
        - 200 OK con el archivo PDF si se exporta exitosamente
        - 400 Bad Request si el formato no es soportado
        - 403 Forbidden si el usuario no tiene acceso
        - 404 Not Found si la release o la verificación no se encuentran
        - 500 Internal Server Error para cualquier otro error inesperado
    """
    try:
        if format != "pdf":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Formato no soportado. Use format=pdf")
        result = await service.get_verification_result(release_id=id, result_id=rid)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verificación no encontrada")
        safe_lang = lang if lang in ("es", "en") else "es"
        pdf_path = await export_service.export_verification_to_pdf(release_id=id, result_id=rid, lang=safe_lang)
        if not os.path.realpath(pdf_path).startswith(tempfile.gettempdir()):
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)
        safe_filename = f"verification_{rid}.pdf".replace("\\", "_").replace("/", "_")
        return FileResponse(pdf_path, media_type="application/pdf", filename=safe_filename)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


@router.get("/api/v1/projects/{project_id}/results/export", status_code=status.HTTP_200_OK)
async def export_project_results_csv(
    project_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.VIEW_ORG_PROJECTS))],
    service: Annotated[IVerificationService, Depends(get_verification_service)],
    export_service: Annotated[IExportService, Depends(get_export_service)],
    format: Annotated[Literal["csv"], Query(description="Formato de exportación")] = "csv",
):
    """Exporta el historial de verificaciones de un proyecto a formato CSV.

    Atributos:
        - project_id: ID del proyecto cuyas verificaciones se exportarán.
        - format: Formato de exportación (solo CSV soportado actualmente).
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: Instancia del servicio de verificaciones (inyección de dependencias).
        - export_service: Instancia del servicio de exportación (inyección de dependencias).

    Retorna:
        - 200 OK con el archivo CSV si se exporta exitosamente
        - 400 Bad Request si el formato no es soportado
        - 403 Forbidden si el usuario no tiene acceso al proyecto
        - 500 Internal Server Error para cualquier otro error inesperado
    """
    try:
        if format != "csv":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Formato no soportado. Use format=csv")
        csv_path = await export_service.export_project_results_to_csv(project_id=project_id)
        if not os.path.realpath(csv_path).startswith(tempfile.gettempdir()):
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)
        safe_filename = f"project_{project_id}_results.csv".replace("\\", "_").replace("/", "_")
        return FileResponse(csv_path, media_type="text/csv", filename=safe_filename)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


class ImportArtifactsRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    artifacts: List[ArtifactCreateRequest]


@router.post("/api/v1/releases/{id}/artifacts/import", status_code=status.HTTP_202_ACCEPTED)
async def import_artifacts(
    id: UUID,
    payload: ImportArtifactsRequest,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.UPDATE_OWN_RELEASES))],
    _: Annotated[None, Depends(require_release_access())],
    service: Annotated[IArtifactService, Depends(get_artifact_service)],
):
    """Importa múltiples artefactos a una release desde un fichero CSV.

    Permite la importación masiva de artefactos a partir de un archivo CSV
    proporcionado en la solicitud. La operación se ejecuta de forma asíncrona.

    Atributos:
        - id: ID de la release a la que se importarán los artefactos.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: Instancia del servicio de artefactos (inyección de dependencias).

    Retorna:
        - 202 Accepted si la importación se inicia exitosamente.
        - 403 Forbidden si el usuario no tiene acceso a la release.
        - 404 Not Found si la release no se encuentra.
        - 422 Unprocessable Entity si el fichero CSV no es válido.
        - 500 Internal Server Error para cualquier otro error inesperado.
    """
    try:
        imported = []
        for artifact_data in payload.artifacts:
            artifact = await service.add_artifact(
                release_id=id,
                connector_instance_id=artifact_data.connector_instance_id,
                connector_implementation=artifact_data.connector_implementation,
                artifact_type=artifact_data.artifact_type,
                external_ref=artifact_data.external_ref,
                description=artifact_data.description,
                metadata=artifact_data.metadata,
            )
            imported.append({"id": str(artifact.id), "external_ref": artifact.external_ref})
        return {"imported": imported, "count": len(imported)}
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)
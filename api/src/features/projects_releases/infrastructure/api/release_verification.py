import os
import tempfile
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from fastapi.responses import FileResponse
from typing import Annotated, Literal, List, Optional
from features.projects_releases.application.ports.i_release_service import IReleaseService
from features.projects_releases.application.ports.i_artifact_service import IArtifactService
from features.connectors.application.ports.i_connector_service import IConnectorService
from features.verification.application.ports.i_verification_service import IVerificationService
from features.reporting.application.ports.i_export_service import IExportService
from bootstrap.dependencies import (
    get_release_service,
    get_artifact_service,
    get_connector_service,
    get_verification_service,
    get_export_service,
    CurrentUser,
    require_permission,
    require_project_access,
    require_release_access,
)
from shared.domain.enums import ArtifactType, ReleaseStatus, Permission
from shared.domain.exceptions import ValidationError
from shared.infrastructure.api_errors import ERROR_INTERNO, handle_internal_errors
from .releases_schemas import ArtifactCreateRequest, RELEASE_NOT_FOUND


router = APIRouter(tags=["Releases"])


RELEASE_OR_VERIFICATION_NOT_FOUND = "Release o verificación no encontradas"


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
@handle_internal_errors
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


@router.get("/api/v1/releases/{id}/results")
@handle_internal_errors
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


@router.get("/api/v1/releases/{id}/results/{rid}")
@handle_internal_errors
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


@router.get("/api/v1/releases/{id}/verifications/{verification_id}")
@handle_internal_errors
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
    _: Annotated[None, Depends(require_project_access())],
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
    connector_service: Annotated[IConnectorService, Depends(get_connector_service)],
    release_service: Annotated[IReleaseService, Depends(get_release_service)],
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
        release = await release_service.get_release(id)
        if not release:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RELEASE_NOT_FOUND)
        imported = []
        for artifact_data in payload.artifacts:
            await connector_service.verify_artifact_ref(
                connector_id=artifact_data.connector_instance_id,
                external_ref=artifact_data.external_ref,
                organization_id=release.organization_id,
            )
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
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from fastapi.responses import Response

# Puertos de Entrada (Interfaces)
from application.ports.input.i_release_service import IReleaseService
from application.ports.input.i_artifact_service import IArtifactService
from application.ports.input.i_verification_service import IVerificationService

# Inyección de dependencias
from core.dependencies import get_release_service, get_artifact_service, get_verification_service, get_current_user_id

# Enums y excepciones
from domain.exceptions import ValidationError
from domain.enums import ArtifactType, ReleaseStatus

# Quitamos el prefix global para poder manejar tanto rutas de proyectos como de releases directas
router = APIRouter(tags=["Releases"])

# --- ESQUEMAS PYDANTIC > Sirven para validar y documentar las solicitudes y respuestas de la API. ---
class ReleaseCreateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid') # Seguridad: rechaza campos no definidos
    name: str = Field(..., min_length=1, max_length=100)
    version: str
    description: str = Field(default="", max_length=1000)

class ArtifactCreateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    type: ArtifactType
    connector_id: UUID
    external_ref: str
    description: str = ""


# ==========================
# BLOQUE 1: COLECCIÓN DEL PROYECTO
# ==========================
@router.post("/api/v1/projects/{project_id}/releases", status_code=status.HTTP_201_CREATED)
async def create_release(
    project_id: UUID,
    payload: ReleaseCreateRequest,
    user_id: UUID = Depends(get_current_user_id),
    service: IReleaseService = Depends(get_release_service),
):
    """ Crea una nueva release dentro del proyecto especificado.

    Atributos:
        - project_id: ID del proyecto al que pertenece la release.
        - payload: Datos de la release a crear (nombre, versión, descripción).
        - user_id: ID del usuario autenticado (obtenido del token JWT).
        - service: Instancia del servicio de releases (inyección de dependencias).

    Retorna:
        - 201 Created con el ID y estado inicial de la release si se crea exitosamente
        - 422 Unprocessable Entity si los datos de entrada no son válidos
        - 500 Internal Server Error para cualquier otro error inesperado    
    """
    try:
        release = await service.create_release(
            name=payload.name,
            version=payload.version,
            project_id=project_id,
            user_id=user_id,
            description=payload.description
        )
        return {
            "id": release.id, 
            "status": release.status
        }
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/api/v1/projects/{project_id}/releases")
async def list_releases(
    project_id: UUID,
    service: IReleaseService = Depends(get_release_service),
):
    """
    Lista todas las releases asociadas al proyecto especificado.

    Atributos:
        - project_id: ID del proyecto del que se quieren listar las releases.
        - service: Instancia del servicio de releases (inyección de dependencias).

    Retorna:
        - 200 OK con la lista de releases si se encuentran exitosamente
        - 500 Internal Server Error para cualquier otro error inesperado
    """
    try:
        releases = await service.list_releases(project_id=project_id)
        return releases
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ===================================
# BLOQUE 2: OPERACIONES SOBRE LA RELEASE
# ===================================
@router.get("/api/v1/releases/{id}")
async def get_release(
    id: UUID,
    service: IReleaseService = Depends(get_release_service),
):
    """Obtiene los detalles de una release específica por su ID.
    
    Atributos:
        - id: ID de la release a obtener.
        - service: Instancia del servicio de releases (inyección de dependencias).

    Retorna:
        - 200 OK con los detalles de la release si se encuentra exitosamente
        - 404 Not Found si la release no se encuentra
        - 500 Internal Server Error para cualquier otro error inesperado
    """
    try:
        release = await service.get_release(release_id=id)
        if not release:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Release no encontrada")
        return release
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    

@router.patch("/api/v1/releases/{id}")
async def update_release(
    id: UUID,
    payload: ReleaseCreateRequest,
    service: IReleaseService = Depends(get_release_service),
):
    """Actualiza los detalles de una release específica por su ID.
    
    Atributos:
        - id: ID de la release a actualizar.
        - payload: Datos actualizados de la release (nombre, versión, descripción).
        - service: Instancia del servicio de releases (inyección de dependencias).
        
    Retorna:
        - 200 OK con los detalles actualizados de la release si se actualiza exitosamente
        - 404 Not Found si la release no se encuentra
        - 409 Conflict si los datos de actualización violan alguna regla de validación
        - 500 Internal Server Error para cualquier otro error inesperado"""
    try:
        release = await service.update_release(
            release_id=id,
            name=payload.name,
            version=payload.version,
            description=payload.description
        )
        return release
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/api/v1/releases/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_release(
    id: UUID,
    service: IReleaseService = Depends(get_release_service),
):
    """Elimina una release específica por su ID.

    Atributos:
        - id: ID de la release a eliminar.
        - service: Instancia del servicio de releases (inyección de dependencias).

    Retorna:
        - 204 No Content si se elimina exitosamente
        - 404 Not Found si la release no se encuentra
        - 500 Internal Server Error para cualquier otro error inesperado
    """
    try:
        await service.delete_release(release_id=id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    

@router.post("/api/v1/releases/{id}/archive", status_code=status.HTTP_200_OK)
async def archive_release(
    id: UUID,
    service: IReleaseService = Depends(get_release_service),
):
    """Archiva una release específica por su ID, cambiando su estado a 'ARCHIVADA'.

    Atributos:
        - id: ID de la release a archivar.
        - service: Instancia del servicio de releases (inyección de dependencias).

    Retorna:
        - 200 OK con un mensaje de éxito si se archiva exitosamente
        - 404 Not Found si la release no se encuentra
        - 500 Internal Server Error para cualquier otro error inesperado
    """
    try:
        await service.update_status(release_id=id, status=ReleaseStatus.ARCHIVADA)
        return {"message": "Release archivada con éxito"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ========================
# BLOQUE 3: GESTIÓN DE ARTEFACTOS
# ========================
@router.get("/api/v1/releases/{id}/artifacts")
async def list_artifacts(
    id: UUID,
    service: IArtifactService = Depends(get_artifact_service),
):
    """Lista todos los artefactos asociados a una release específica por su ID.
    
    Atributos:
        - id: ID de la release de la que se quieren listar los artefactos.
        - service: Instancia del servicio de artefactos (inyección de dependencias).

    Retorna:
        - 200 OK con la lista de artefactos si se encuentran exitosamente
        - 404 Not Found si la release no se encuentra
        - 500 Internal Server Error para cualquier otro error inesperado
    """
    try:
        artifacts = await service.list_artifacts(release_id=id)
        return artifacts
    except HTTPException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Release no encontrada")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/api/v1/releases/{id}/artifacts", status_code=status.HTTP_201_CREATED)
async def add_artifact(
    id: UUID,
    payload: ArtifactCreateRequest,
    service: IArtifactService = Depends(get_artifact_service),
):
    """Agrega un nuevo artefacto a una release específica por su ID.

    Atributos:
        - id: ID de la release a la que se quiere agregar el artefacto.
        - payload: Datos del artefacto a agregar (tipo, conector, referencia externa
            y descripción).
        - service: Instancia del servicio de artefactos (inyección de dependencias).

    Retorna:
        - 201 Created con el ID del artefacto creado si se agrega exitosamente
        - 404 Not Found si la release no se encuentra
        - 422 Unprocessable Entity si los datos de entrada no son válidos
        - 500 Internal Server Error para cualquier otro error inesperado
    """
    try:
        artifact = await service.add_artifact(
            release_id=id,
            connector_instance_id=payload.connector_id,
            artifact_type=payload.type,
            external_ref=payload.external_ref,
            metadata={"description": payload.description} if payload.description else None
        )
        return {"id": artifact.id}
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except HTTPException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Release no encontrada")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/api/v1/releases/{id}/artifacts/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_artifact(
    id: UUID,
    artifact_id: UUID,
    service: IArtifactService = Depends(get_artifact_service),
):
    """Elimina un artefacto específico de una release por sus IDs.

    Atributos:
        - id: ID de la release de la que se quiere eliminar el artefacto.
        - artifact_id: ID del artefacto a eliminar.
        - service: Instancia del servicio de artefactos (inyección de dependencias).

    Retorna:
        - 204 No Content si se elimina exitosamente
        - 404 Not Found si la release o el artefacto no se encuentran
        - 500 Internal Server Error para cualquier otro error inesperado
    """
    try:
        await service.remove_artifact(release_id=id, artifact_id=artifact_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Release o artefacto no encontrados")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ============================
# BLOQUE 4: VERIFICACIÓN E HISTORIAL
# ============================
@router.post("/api/v1/releases/{id}/verify", status_code=status.HTTP_202_ACCEPTED)
async def verify_release(
    id: UUID,
    service: IVerificationService = Depends(get_verification_service),
):
    """ Lanza la verificación asíncrona.

    Atributos:
        - id: ID de la release a verificar.
        - service: Instancia del servicio de verificaciones (inyección de dependencias).

    Retorna:
        - 202 Accepted con el ID de la tarea de verificación y el nuevo estado de
            la release si se lanza exitosamente
        - 404 Not Found si la release no se encuentra
        - 409 Conflict si la release no se encuentra en un estado válido para iniciar la verificación
        - 500 Internal Server Error para cualquier otro error inesperado
    """
    try:
        task_id = await service.launch_verification(release_id=id)
        return {
            "task_id": task_id, 
            "status": ReleaseStatus.EN_VERIFICACION
        }
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/api/v1/releases/{id}/results")
async def get_results(
    id: UUID,
    service: IVerificationService = Depends(get_verification_service),
):
    """Obtiene el historial paginado de verificaciones de esta release.
    
    Atributos:
        - id: ID de la release de la que se quieren obtener los resultados.
        - service: Instancia del servicio de verificaciones (inyección de dependencias).

    Retorna:
        - 200 OK con la lista paginada de resultados de verificaciones si se encuentran
        - 404 Not Found si la release no se encuentra
        - 500 Internal Server Error para cualquier otro error inesperado
    """
    try:
        results = await service.list_verification_results(release_id=id)
        return results
    except HTTPException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Release no encontrada")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/api/v1/releases/{id}/results/{rid}")
async def get_result_detail(
    id: UUID,
    rid: UUID,
    service: IVerificationService = Depends(get_verification_service),
):
    """Obtiene el informe detallado de una validación individual.
    
    Atributos:
        - id: ID de la release a la que pertenece la verificación.
        - rid: ID de la verificación individual de la que se quieren obtener los detalles.
        - service: Instancia del servicio de verificaciones (inyección de dependencias).

    Retorna:
        - 200 OK con el informe detallado de la verificación si se encuentra exitosamente
        - 404 Not Found si la release o la verificación no se encuentran
        - 500 Internal Server Error para cualquier otro error inesperado
    """
    try:
        result = await service.get_verification_result(release_id=id, result_id=rid)
        return result
    except HTTPException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Release o verificación no encontradas")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
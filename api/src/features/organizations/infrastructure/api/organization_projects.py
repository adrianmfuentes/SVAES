from uuid import UUID
from typing import Optional, Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from features.organizations.application.ports.i_organization_service import IOrganizationService
from bootstrap.dependencies import (
    get_organization_service,
    get_current_user,
    CurrentUser,
    ProjectAccess,
    require_permission,
    require_project_access,
    require_org_access,
)
from shared.domain.enums import UserRole, Permission
from shared.domain.exceptions import ValidationError, EntityNotFoundError
from shared.infrastructure.api_errors import ERROR_INTERNO, handle_internal_errors, ERROR_PROYECTO_NO_ORGANIZACION


router = APIRouter(tags=["Organizations"])


class ProjectCreateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    profile_id: UUID


class ProjectUpdateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    profile_id: Optional[UUID] = None


@router.get("/api/v1/projects/{project_id}")
async def get_project_by_id(
    project_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[IOrganizationService, Depends(get_organization_service)],
):
    try:
        project = await service.get_project(project_id=project_id)
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado")
        if current_user.role != UserRole.U3 and project.organization_id != current_user.organization_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes acceso a este proyecto")
        return {
            "id": str(project.id),
            "name": project.name,
            "description": project.description,
            "organization_id": str(project.organization_id),
            "profile_id": str(project.profile_id) if project.profile_id else None,
            "is_archived": project.is_archived,
            "created_at": project.created_at.isoformat() if project.created_at else None,
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


@router.get("/api/v1/projects")
@handle_internal_errors
async def list_accessible_projects(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[IOrganizationService, Depends(get_organization_service)],
    page: int = 1,
    size: int = 50,
    skip: int = 0,
    limit: int = 0,
):
    effective_skip = (page - 1) * size if limit == 0 else skip
    effective_limit = size if limit == 0 else limit

    if current_user.role == UserRole.U3:
        projects = await service.list_accessible_projects(
            user_id=current_user.user_id, skip=effective_skip, limit=effective_limit
        )
    elif current_user.organization_id:
        projects = await service.list_projects(
            organization_id=current_user.organization_id, skip=effective_skip, limit=effective_limit
        )
    else:
        return []

    return [
        {
            "id": str(p.id),
            "name": p.name,
            "description": p.description,
            "organization_id": str(p.organization_id),
            "profile_id": str(p.profile_id) if p.profile_id else None,
            "is_archived": p.is_archived,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in projects
    ]


@router.get("/api/v1/organizations/{org_id}/projects")
@handle_internal_errors
async def list_org_projects(
    org_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.VIEW_ORG_PROJECTS))],
    service: Annotated[IOrganizationService, Depends(get_organization_service)],
    skip: int = 0,
    limit: int = 50,
):
    projects = await service.list_projects(organization_id=org_id, skip=skip, limit=limit)
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "description": p.description,
            "organization_id": str(p.organization_id),
            "profile_id": str(p.profile_id) if p.profile_id else None,
            "is_archived": p.is_archived,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in projects
    ]


@router.get("/api/v1/organizations/{org_id}/projects/{project_id}")
async def get_project(
    org_id: UUID,
    project_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.VIEW_ORG_PROJECTS))],
    service: Annotated[IOrganizationService, Depends(get_organization_service)],
):
    try:
        project = await service.get_project(project_id=project_id)
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado")
        if project.organization_id != org_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_PROYECTO_NO_ORGANIZACION)
        return {
            "id": str(project.id),
            "name": project.name,
            "description": project.description,
            "organization_id": str(project.organization_id),
            "profile_id": str(project.profile_id) if project.profile_id else None,
            "is_archived": project.is_archived,
            "created_at": project.created_at.isoformat() if project.created_at else None,
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


@router.post("/api/v1/organizations/{org_id}/projects", status_code=status.HTTP_201_CREATED)
@handle_internal_errors
async def create_project(
    org_id: UUID,
    payload: ProjectCreateRequest,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.CREATE_PROJECT))],
    _: Annotated[CurrentUser, Depends(require_org_access())],
    service: Annotated[IOrganizationService, Depends(get_organization_service)],
):
    """Endpoint para crear un nuevo proyecto dentro de una organización.

    Atributos:
        - org_id: UUID - El ID de la organización.
        - payload: ProjectCreateRequest - El cuerpo de la solicitud con los datos del proyecto a crear.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: IOrganizationService - El servicio de organizaciones, inyectado mediante dependencias.

    Retorna:
        - Un diccionario con la información del proyecto creado (id, name).
        - Lanza HTTPException con status 403 si el usuario no tiene acceso a la organización.
        - Lanza HTTPException con status 404 si la organización no existe.
        - Lanza HTTPException con status 409 si hay un error de validación.
        - Lanza HTTPException con status 500 para cualquier error inesperado.
    """
    try:
        project = await service.create_project(
            organization_id=org_id,
            name=payload.name,
            description=payload.description,
            profile_id=payload.profile_id,
        )
        return {"id": str(project.id), "name": project.name}
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.patch("/api/v1/projects/{project_id}", status_code=status.HTTP_200_OK)
@handle_internal_errors
async def update_project(
    project_id: UUID,
    payload: ProjectUpdateRequest,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.UPDATE_PROJECT))],
    project_access: Annotated[ProjectAccess, Depends(require_project_access())],
    service: Annotated[IOrganizationService, Depends(get_organization_service)],
):
    """Endpoint para actualizar los datos editables de un proyecto (nombre, descripción y perfil de verificación).

    Atributos:
        - project_id: UUID - El ID del proyecto a actualizar.
        - payload: ProjectUpdateRequest - Campos a actualizar (todos opcionales).
        - current_user: Usuario autenticado con permisos del token JWT.
        - project_access: Acceso validado al proyecto.
        - service: IOrganizationService - El servicio de organizaciones, inyectado mediante dependencias.

    Retorna:
        - Un diccionario con los datos actualizados del proyecto.
        - Lanza HTTPException con status 403 si el usuario no tiene acceso al proyecto.
        - Lanza HTTPException con status 404 si el proyecto no existe.
        - Lanza HTTPException con status 409 si hay un error de validación (e.g., perfil inexistente).
        - Lanza HTTPException con status 500 para cualquier error inesperado.
    """
    try:
        project = await service.update_project(
            project_id=project_id,
            name=payload.name,
            description=payload.description,
            profile_id=payload.profile_id,
        )
        return {
            "id": str(project.id),
            "name": project.name,
            "description": project.description,
            "organization_id": str(project.organization_id),
            "profile_id": str(project.profile_id) if project.profile_id else None,
            "is_archived": project.is_archived,
            "created_at": project.created_at.isoformat() if project.created_at else None,
        }
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/api/v1/organizations/{org_id}/projects/{project_id}/archive", status_code=status.HTTP_200_OK)
async def archive_project(
    org_id: UUID,
    project_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.ARCHIVE_PROJECT))],
    project_access: Annotated[ProjectAccess, Depends(require_project_access())],
    service: Annotated[IOrganizationService, Depends(get_organization_service)],
):
    """Endpoint para archivar un proyecto.

    Atributos:
        - org_id: UUID - El ID de la organización.
        - project_id: UUID - El ID del proyecto a archivar.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: IOrganizationService - El servicio de organizaciones, inyectado mediante dependencias.

    Retorna:
        - Un diccionario con el ID y nombre del proyecto archivado.
        - Lanza HTTPException con status 403 si el usuario no tiene acceso a la organización.
        - Lanza HTTPException con status 404 si la organización o el proyecto no existen.
        - Lanza HTTPException con status 500 para cualquier error inesperado.
    """
    try:
        if project_access.project and project_access.project.organization_id != org_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_PROYECTO_NO_ORGANIZACION)
        project = await service.archive_project(project_id=project_id)
        return {"id": str(project.id), "name": project.name, "is_archived": project.is_archived}
    except HTTPException:
        raise
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


@router.post("/api/v1/organizations/{org_id}/projects/{project_id}/unarchive", status_code=status.HTTP_200_OK)
async def unarchive_project(
    org_id: UUID,
    project_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.ARCHIVE_PROJECT))],
    project_access: Annotated[ProjectAccess, Depends(require_project_access())],
    service: Annotated[IOrganizationService, Depends(get_organization_service)],
):
    """Endpoint para desarchivar un proyecto.

    Atributos:
        - org_id: UUID - El ID de la organización.
        - project_id: UUID - El ID del proyecto a desarchivar.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: IOrganizationService - El servicio de organizaciones, inyectado mediante dependencias.

    Retorna:
        - Un diccionario con el ID, nombre y estado del proyecto desarchivado.
        - Lanza HTTPException con status 403 si el usuario no tiene acceso a la organización.
        - Lanza HTTPException con status 404 si la organización o el proyecto no existen.
        - Lanza HTTPException con status 500 para cualquier error inesperado.
    """
    try:
        if project_access.project and project_access.project.organization_id != org_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_PROYECTO_NO_ORGANIZACION)
        project = await service.unarchive_project(project_id=project_id)
        return {"id": str(project.id), "name": project.name, "is_archived": project.is_archived}
    except HTTPException:
        raise
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)

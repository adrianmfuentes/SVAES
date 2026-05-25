from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, ConfigDict, Field
from typing import Annotated, Optional
from application.ports.input.i_template_service import ITemplateService
from core.dependencies import get_current_user, CurrentUser, require_permission, require_role, get_template_service
from domain.enums import UserRole, Permission
from domain.exceptions import EntityNotFoundError, ValidationError
from . import ERROR_INTERNO

router = APIRouter(tags=["Templates"])


class TemplateCreateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    profile_id: UUID
    project_name_template: Optional[str] = None


class TemplateUpdateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_archived: Optional[bool] = None


class TemplateCloneRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(..., min_length=1, max_length=100)
    target_organization_id: UUID


@router.post("/api/v1/templates", status_code=status.HTTP_201_CREATED)
async def create_template(
    payload: TemplateCreateRequest,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.MANAGE_PROFILES))],
    service: Annotated[ITemplateService, Depends(get_template_service)],
):
    """Crea una nueva plantilla de release.

    Atributos:
        - payload: Datos de la plantilla a crear (nombre, descripción, profile_id).
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: Servicio de plantillas inyectado mediante dependencias.

    Retorna:
        - 201 Created con el ID de la plantilla creada.
        - 403 Forbidden si el usuario no tiene permisos.
        - 500 Internal Server Error para cualquier error inesperado.
    """
    try:
        if current_user.organization_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Se requiere organizacion")
        template = await service.create_template(
            name=payload.name,
            description=payload.description,
            profile_id=payload.profile_id,
            created_by=current_user.user_id,
            organization_id=current_user.organization_id,
            project_name_template=payload.project_name_template,
        )
        return {"id": str(template.id), "name": template.name}
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


@router.get("/api/v1/templates")
async def list_templates(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[ITemplateService, Depends(get_template_service)],
    skip: int = 0,
    limit: int = 50,
    include_archived: bool = False,
):
    """Lista las plantillas de release accesibles por el usuario.

    Atributos:
        - skip: int - Número de registros a omitir para paginación.
        - limit: int - Número máximo de registros a retornar.
        - include_archived: bool - Incluir plantillas archivadas.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: Servicio de plantillas inyectado mediante dependencias.

    Retorna:
        - Lista de plantillas con su información.
        - 500 Internal Server Error para cualquier error inesperado.
    """
    try:
        if current_user.organization_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Se requiere organizacion")
        templates = await service.list_templates(
            organization_id=current_user.organization_id,
            skip=skip,
            limit=limit,
            include_archived=include_archived,
        )
        return templates
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


@router.get("/api/v1/templates/{template_id}")
async def get_template(
    template_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[ITemplateService, Depends(get_template_service)],
):
    """Obtiene los detalles de una plantilla específica.

    Atributos:
        - template_id: UUID - El ID de la plantilla.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: Servicio de plantillas inyectado mediante dependencias.

    Retorna:
        - Detalles de la plantilla.
        - 404 Not Found si la plantilla no existe.
        - 500 Internal Server Error para cualquier error inesperado.
    """
    try:
        template = await service.get_template(template_id=template_id)
        if not template:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plantilla no encontrada")
        return template
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


@router.patch("/api/v1/templates/{template_id}")
async def update_template(
    template_id: UUID,
    payload: TemplateUpdateRequest,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.MANAGE_PROFILES))],
    service: Annotated[ITemplateService, Depends(get_template_service)],
):
    """Actualiza una plantilla de release.

    Atributos:
        - template_id: UUID - El ID de la plantilla a actualizar.
        - payload: Datos actualizados de la plantilla.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: Servicio de plantillas inyectado mediante dependencias.

    Retorna:
        - 200 OK con la plantilla actualizada.
        - 404 Not Found si la plantilla no existe.
        - 500 Internal Server Error para cualquier error inesperado.
    """
    try:
        template = await service.update_template(
            template_id=template_id,
            name=payload.name,
            description=payload.description,
            is_archived=payload.is_archived,
        )
        return template
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


@router.post("/api/v1/templates/{template_id}/archive", status_code=status.HTTP_200_OK)
async def archive_template(
    template_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.MANAGE_PROFILES))],
    service: Annotated[ITemplateService, Depends(get_template_service)],
):
    """Archiva una plantilla de release.

    Atributos:
        - template_id: UUID - El ID de la plantilla a archivar.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: Servicio de plantillas inyectado mediante dependencias.

    Retorna:
        - 200 OK con mensaje de éxito.
        - 404 Not Found si la plantilla no existe.
        - 500 Internal Server Error para cualquier error inesperado.
    """
    try:
        await service.archive_template(template_id=template_id)
        return {"message": "Plantilla archivada con éxito"}
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


@router.post("/api/v1/templates/{template_id}/clone", status_code=status.HTTP_201_CREATED)
async def clone_template(
    template_id: UUID,
    payload: TemplateCloneRequest,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.MANAGE_PROFILES))],
    service: Annotated[ITemplateService, Depends(get_template_service)],
):
    """Clona una plantilla de release a otra organización.

    Atributos:
        - template_id: UUID - El ID de la plantilla a clonar.
        - payload: Datos para la clonación (nombre destino, organización destino).
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: Servicio de plantillas inyectado mediante dependencias.

    Retorna:
        - 201 Created con el ID de la nueva plantilla clonada.
        - 404 Not Found si la plantilla no existe.
        - 500 Internal Server Error para cualquier error inesperado.
    """
    try:
        new_template = await service.clone_template(
            template_id=template_id,
            new_name=payload.name,
            target_organization_id=payload.target_organization_id,
            requested_by=current_user.user_id,
        )
        return {"id": str(new_template.id), "name": new_template.name}
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)
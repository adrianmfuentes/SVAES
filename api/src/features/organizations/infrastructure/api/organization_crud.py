from features.organizations.application.use_cases.create_organization import CreateOrganization
from bootstrap.dependencies import get_create_organization
from uuid import UUID
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from features.organizations.application.ports.i_organization_service import IOrganizationService
from bootstrap.dependencies import (
    get_organization_service,
    get_current_user_or_api_key,
    get_current_user_api_key_only,
    CurrentUser,
)
from shared.infrastructure.rate_limit import rate_limit_api_key
from shared.domain.enums import UserRole
from shared.domain.exceptions import ValidationError, DuplicateEntityError
from shared.infrastructure.api_errors import ERROR_INTERNO, handle_internal_errors


router = APIRouter(tags=["Organizations"])


@router.get("/api/v1/me")
@rate_limit_api_key()
async def get_me(
    request: Request,
    current_user: Annotated[CurrentUser, Depends(get_current_user_api_key_only)],
):
    """Devuelve la identidad del token o API key actual: user_id, organization_id y role.
    Útil para que clientes con API key descubran su propio organization_id sin necesitar acceso de ADMIN.
    """
    return {
        "user_id": str(current_user.user_id),
        "organization_id": str(current_user.organization_id) if current_user.organization_id else None,
        "role": current_user.role.value,
        "auth_via_api_key": current_user.auth_via_api_key,
    }


class OrganizationCreateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=50, pattern=r"^[a-z0-9-]+$")


@router.get("/api/v1/organizations")
@rate_limit_api_key()
@handle_internal_errors
async def list_organizations(
    request: Request,
    current_user: Annotated[CurrentUser, Depends(get_current_user_or_api_key)],
    service: Annotated[IOrganizationService, Depends(get_organization_service)],
    skip: int = 0,
    limit: int = 100,
):
    """ Endpoint para listar las organizaciones. Solo los usuarios con rol ADMIN pueden acceder a esta información.

    Atributos:
        - skip: int - Número de registros a omitir para paginación.
        - limit: int - Número máximo de registros a retornar.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: IOrganizationService - El servicio de organizaciones, inyectado mediante dependencias.

    Retorna:
        - Una lista de diccionarios con la información de cada organización.
        - Lanza HTTPException con status 403 si el usuario no tiene rol ADMIN.
        - Lanza HTTPException con status 500 para cualquier error inesperado.
    """
    if current_user.role != UserRole.U3:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso")
    organizations = await service.list_organizations(skip=skip, limit=limit, active_only=True)
    return organizations


@router.post("/api/v1/organizations", status_code=status.HTTP_201_CREATED)
@rate_limit_api_key()
@handle_internal_errors
async def create_organization(
    request: Request,
    payload: OrganizationCreateRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user_or_api_key)],
    service: Annotated[CreateOrganization, Depends(get_create_organization)],
):
    """ Endpoint para crear una nueva organización. Usuarios OPERATOR y MANAGER pueden crear organizaciones.
        Los usuarios ADMIN deben usar las rutas de administración.

    Atributos:
        - payload: OrganizationCreateRequest - El cuerpo de la solicitud con los datos de la organización a crear.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: IOrganizationService - El servicio de organizaciones, inyectado mediante dependencias.

    Retorna:
        - Un diccionario con la información de la organización creada (id, name, slug).
        - Lanza HTTPException con status 409 si hay un error de validación (e.g., slug ya existe).
        - Lanza HTTPException con status 500 para cualquier error inesperado.
    """
    if current_user.auth_via_api_key and current_user.role == UserRole.U2:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso",
        )
    if current_user.role == UserRole.U3:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Los administradores deben crear organizaciones desde el panel de administración.",
        )
    try:
        org = await service.execute(
            name=payload.name,
            slug=payload.slug,
            owner_id=current_user.user_id,
        )
        return {"id": str(org.id), "name": org.name, "slug": org.slug}
    except DuplicateEntityError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/api/v1/organizations/{org_id}")
@rate_limit_api_key()
async def get_organization(
    request: Request,
    org_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user_or_api_key)],
    service: Annotated[IOrganizationService, Depends(get_organization_service)],
):
    """ Endpoint para obtener los detalles de una organización.

    Atributos:
        - org_id: UUID - El ID de la organización.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: IOrganizationService - El servicio de organizaciones, inyectado mediante dependencias.

    Retorna:
        - Un diccionario con la información de la organización (id, name, slug, owner_id, etc.).
        - Lanza HTTPException con status 403 si el usuario no tiene acceso a la organización.
        - Lanza HTTPException con status 404 si la organización no existe.
        - Lanza HTTPException con status 500 para cualquier error inesperado.
    """
    try:
        org = await service.get_organization(organization_id=org_id)
        if not org:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organización no encontrada")
        api_key_blocked = current_user.auth_via_api_key and current_user.organization_id != org_id
        jwt_blocked = not current_user.auth_via_api_key and current_user.role != UserRole.U3 and current_user.organization_id != org_id and org.owner_id != current_user.user_id
        if api_key_blocked or jwt_blocked:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes acceso a esta organización")
        return {
            "id": str(org.id),
            "name": org.name,
            "slug": org.slug,
            "owner_id": str(org.owner_id) if org.owner_id else None,
            "is_active": org.is_active,
            "created_at": org.created_at.isoformat() if org.created_at else None,
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)

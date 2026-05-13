from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from application.ports.input.i_organization_service import IOrganizationService
from core.dependencies import get_organization_service, get_current_user, CurrentUser, require_permission, require_role
from domain.enums import UserRole, Permission
from domain.exceptions import ValidationError, EntityNotFoundError

router = APIRouter(tags=["Organizations"])

class OrganizationCreateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=50, pattern=r"^[a-z0-9-]+$")
    plan: str = Field(default="default", max_length=50)

class ProjectCreateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    profile_id: UUID


@router.get("/api/v1/organizations")
async def list_organizations(
    skip: int = 0,
    limit: int = 100,
    current_user: CurrentUser = Depends(require_role(UserRole.ADMIN)),
    service: IOrganizationService = Depends(get_organization_service),
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
    try:
        organizations = await service.list_organizations(skip=skip, limit=limit, active_only=True)
        return organizations
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/api/v1/organizations", status_code=status.HTTP_201_CREATED)
async def create_organization(
    payload: OrganizationCreateRequest,
    current_user: CurrentUser = Depends(require_role(UserRole.ADMIN)),
    service: IOrganizationService = Depends(get_organization_service),
):
    """ Endpoint para crear una nueva organización. Solo los usuarios con rol ADMIN pueden crear organizaciones.

    Atributos:
        - payload: OrganizationCreateRequest - El cuerpo de la solicitud con los datos de la organización a crear.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: IOrganizationService - El servicio de organizaciones, inyectado mediante dependencias.

    Retorna:
        - Un diccionario con la información de la organización creada (id, name, slug).
        - Lanza HTTPException con status 403 si el usuario no tiene rol ADMIN.
        - Lanza HTTPException con status 409 si hay un error de validación (e.g., slug ya existe).
        - Lanza HTTPException con status 500 para cualquier error inesperado.
    """
    try:
        org = await service.create_organization(
            name=payload.name,
            slug=payload.slug,
            plan=payload.plan,
        )
        return {"id": str(org.id), "name": org.name, "slug": org.slug}
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/api/v1/organizations/{org_id}/projects")
async def list_projects(
    org_id: UUID,
    skip: int = 0,
    limit: int = 50,
    current_user: CurrentUser = Depends(require_permission(Permission.VIEW_ORG_PROJECTS)),
    service: IOrganizationService = Depends(get_organization_service),
):
    """Endpoint para listar los proyectos de una organización.

    Atributos:
        - org_id: UUID - El ID de la organización.
        - skip: int - Número de registros a omitir para paginación.
        - limit: int - Número máximo de registros a retornar.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: IOrganizationService - El servicio de organizaciones, inyectado mediante dependencias

    Retorna:
        - Una lista de diccionarios con la información de cada proyecto (id, name).
        - Lanza HTTPException con status 403 si el usuario no tiene acceso a la organización.
        - Lanza HTTPException con status 500 para cualquier error inesperado.
    """
    try:
        projects = await service.list_projects(organization_id=org_id, skip=skip, limit=limit)
        return projects
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/api/v1/organizations/{org_id}/projects", status_code=status.HTTP_201_CREATED)
async def create_project(
    org_id: UUID,
    payload: ProjectCreateRequest,
    current_user: CurrentUser = Depends(require_permission(Permission.CREATE_PROJECT)),
    service: IOrganizationService = Depends(get_organization_service),
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
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


class TransferOwnershipRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    new_owner_id: UUID


@router.post("/api/v1/organizations/{org_id}/transfer-ownership", status_code=status.HTTP_200_OK)
async def transfer_ownership(
    org_id: UUID,
    payload: TransferOwnershipRequest,
    current_user: CurrentUser = Depends(require_permission(Permission.TRANSFER_OWNERSHIP)),
    service: IOrganizationService = Depends(get_organization_service),
):
    """Endpoint para transferir la propiedad de una organización a otro usuario.

    Atributos:
        - org_id: UUID - El ID de la organización.
        - payload: TransferOwnershipRequest - El cuerpo de la solicitud con el ID del nuevo propietario.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: IOrganizationService - El servicio de organizaciones, inyectado mediante dependencias.

    Retorna:
        - Un diccionario con la información de la organización actualizada.
        - Lanza HTTPException con status 403 si el usuario no es el propietario actual.
        - Lanza HTTPException con status 404 si la organización no existe.
        - Lanza HTTPException con status 500 para cualquier error inesperado.
    """
    try:
        org = await service.transfer_ownership(
            organization_id=org_id,
            new_owner_id=payload.new_owner_id,
            requested_by=current_user.user_id,
        )
        return {"id": str(org.id), "name": org.name, "owner_id": str(org.owner_id) if org.owner_id else None}
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
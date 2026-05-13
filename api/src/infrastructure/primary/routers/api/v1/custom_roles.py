from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from application.ports.input.i_custom_role_service import ICustomRoleService
from core.dependencies import get_custom_role_service, get_current_user, CurrentUser, require_permission
from domain.enums import Permission
from domain.exceptions import EntityNotFoundError, ValidationError, DuplicateEntityError

router = APIRouter(tags=["Custom Roles"])

class PermissionItem(str):
    pass

class CustomRoleCreateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(..., min_length=1, max_length=100)
    permissions: list[str] = Field(..., min_items=1)

class CustomRoleUpdateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    permissions: Optional[list[str]] = Field(None, min_items=1)
    is_active: Optional[bool] = None


@router.get("/api/v1/organizations/{org_id}/roles")
async def list_custom_roles(
    org_id: UUID,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_ROLES)),
    service: ICustomRoleService = Depends(get_custom_role_service),
):
    """Lista los roles personalizados de una organización.

    Atributos:
        - org_id: UUID - El ID de la organización.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: Servicio de roles personalizado inyectado.

    Retorna:
        - Lista de roles personalizados con sus permisos.
        - 403 Forbidden si el usuario no tiene acceso.
        - 500 Internal Server Error para cualquier error inesperado.
    """
    try:
        roles = await service.list_roles(organization_id=org_id)
        return [
            {
                "id": str(r.id),
                "name": r.name,
                "permissions": [p.value for p in r.permissions],
                "is_active": r.is_active,
            }
            for r in roles
        ]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/api/v1/organizations/{org_id}/roles", status_code=status.HTTP_201_CREATED)
async def create_custom_role(
    org_id: UUID,
    payload: CustomRoleCreateRequest,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_ROLES)),
    service: ICustomRoleService = Depends(get_custom_role_service),
):
    """Crea un rol personalizado dentro de una organización.

    Los roles personalizados permiten definir combinaciones específicas de permisos
    que pueden asignarse a usuarios dentro de una organización.

    Atributos:
        - org_id: UUID - El ID de la organización.
        - payload: Datos del rol a crear (nombre y lista de permisos).
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: Servicio de roles personalizado inyectado.

    Retorna:
        - El rol personalizado creado con sus permisos.
        - 403 Forbidden si el usuario no tiene acceso.
        - 409 Conflict si ya existe un rol con ese nombre.
        - 500 Internal Server Error para cualquier error inesperado.
    """
    try:
        role = await service.create_role(
            organization_id=org_id,
            name=payload.name,
            permissions=[Permission(p) for p in payload.permissions],
        )
        return {
            "id": str(role.id),
            "name": role.name,
            "permissions": [p.value for p in role.permissions],
        }
    except DuplicateEntityError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.patch("/api/v1/roles/{role_id}")
async def update_custom_role(
    role_id: UUID,
    payload: CustomRoleUpdateRequest,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_ROLES)),
    service: ICustomRoleService = Depends(get_custom_role_service),
):
    """Actualiza un rol personalizado existente.

    Atributos:
        - role_id: UUID - El ID del rol a actualizar.
        - payload: Datos actualizados del rol.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: Servicio de roles personalizado inyectado.

    Retorna:
        - El rol personalizado actualizado.
        - 403 Forbidden si el usuario no tiene acceso.
        - 404 Not Found si el rol no existe.
        - 500 Internal Server Error para cualquier error inesperado.
    """
    try:
        role = await service.update_role(
            role_id=role_id,
            name=payload.name,
            permissions=[Permission(p) for p in payload.permissions] if payload.permissions else None,
            is_active=payload.is_active,
        )
        return {
            "id": str(role.id),
            "name": role.name,
            "permissions": [p.value for p in role.permissions],
            "is_active": role.is_active,
        }
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DuplicateEntityError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/api/v1/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_custom_role(
    role_id: UUID,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_ROLES)),
    service: ICustomRoleService = Depends(get_custom_role_service),
):
    """Elimina un rol personalizado.

    Los usuarios que tengan este rol asignado conservarán sus permisos base
    pero perderán los permisos específicos del rol eliminado.

    Atributos:
        - role_id: UUID - El ID del rol a eliminar.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: Servicio de roles personalizado inyectado.

    Retorna:
        - 204 No Content si el rol fue eliminado correctamente.
        - 403 Forbidden si el usuario no tiene acceso.
        - 404 Not Found si el rol no existe.
        - 500 Internal Server Error para cualquier error inesperado.
    """
    try:
        await service.delete_role(role_id=role_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
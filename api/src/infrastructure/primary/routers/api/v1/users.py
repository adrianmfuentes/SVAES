from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from application.ports.input.i_user_service import IUserService
from core.dependencies import get_user_service, get_current_user, CurrentUser, require_permission, require_role
from domain.enums import UserRole, Permission
from domain.exceptions import EntityNotFoundError, ValidationError

router = APIRouter(tags=["Users"])

class UserProfileResponse(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: UUID
    email: str
    display_name: str
    role: UserRole
    organization_id: UUID | None = None

class UserUpdateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    display_name: str | None = Field(None, min_length=1, max_length=100)

class PasswordChangeRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=255)

class UserInviteRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    email: str = Field(..., min_length=1, max_length=255)
    role: UserRole = Field(default=UserRole.OPERATOR)

class UserRoleUpdateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    role: UserRole


@router.get("/api/v1/users/me")
async def get_current_user_profile(
    current_user: CurrentUser = Depends(get_current_user),
    service: IUserService = Depends(get_user_service),
):
    """Obtiene el perfil del usuario autenticado actualmente.

    Atributos:
        - current_user: Usuario autenticado (del token JWT).
        - service: Servicio de usuarios inyectado mediante dependencias.

    Retorna:
        - Perfil del usuario con id, email, display_name, role y organization_id.
        - 401 Unauthorized si el token es inválido.
        - 500 Internal Server Error para cualquier otro error inesperado.
    """
    try:
        user = await service.get_user_by_id(current_user.user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
        return {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "role": user.role.value,
            "organization_id": str(user.organization_id) if user.organization_id else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.patch("/api/v1/users/me")
async def update_current_user_profile(
    payload: UserUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: IUserService = Depends(get_user_service),
):
    """Actualiza el perfil del usuario autenticado (display_name).

    Atributos:
        - payload: Datos a actualizar (display_name).
        - current_user: Usuario autenticado (del token JWT).
        - service: Servicio de usuarios inyectado mediante dependencias.

    Retorna:
        - Perfil actualizado del usuario.
        - 400 Bad Request si los datos son inválidos.
        - 401 Unauthorized si el token es inválido.
        - 500 Internal Server Error para cualquier otro error inesperado.
    """
    try:
        user = await service.update_profile(
            user_id=current_user.user_id,
            display_name=payload.display_name,
        )
        return {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "role": user.role.value,
        }
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/api/v1/users/me/password")
async def change_password(
    payload: PasswordChangeRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: IUserService = Depends(get_user_service),
):
    """Cambia la contraseña del usuario autenticado.

    Atributos:
        - payload: Contraseña actual y nueva contraseña.
        - current_user: Usuario autenticado (del token JWT).
        - service: Servicio de usuarios inyectado mediante dependencias.

    Retorna:
        - Mensaje de éxito si la contraseña se cambió correctamente.
        - 400 Bad Request si la contraseña actual es incorrecta.
        - 401 Unauthorized si el token es inválido.
        - 500 Internal Server Error para cualquier otro error inesperado.
    """
    try:
        success = await service.change_password(
            user_id=current_user.user_id,
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
        if not success:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contraseña actual incorrecta")
        return {"message": "Contraseña cambiada correctamente"}
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/api/v1/organizations/{org_id}/users")
async def list_organization_users(
    org_id: UUID,
    skip: int = 0,
    limit: int = 50,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_ROLES)),
    service: IUserService = Depends(get_user_service),
):
    """Lista los usuarios de una organización.

    Solo accesible por usuarios con rol MANAGER o superior que pertenezcan a la organización.

    Atributos:
        - org_id: UUID - El ID de la organización.
        - skip: int - Número de registros a omitir para paginación.
        - limit: int - Número máximo de registros a retornar.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: Servicio de usuarios inyectado mediante dependencias.

    Retorna:
        - Lista de usuarios con su id, email, display_name y role.
        - 403 Forbidden si el usuario no tiene acceso a la organización.
        - 500 Internal Server Error para cualquier otro error inesperado.
    """
    try:
        users = await service.list_organization_users(organization_id=org_id, skip=skip, limit=limit)
        return [
            {
                "id": str(u.id),
                "email": u.email,
                "display_name": u.display_name,
                "role": u.role.value,
            }
            for u in users
        ]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/api/v1/organizations/{org_id}/users/invite", status_code=status.HTTP_201_CREATED)
async def invite_user(
    org_id: UUID,
    payload: UserInviteRequest,
    current_user: CurrentUser = Depends(require_permission(Permission.INVITE_USERS)),
    service: IUserService = Depends(get_user_service),
):
    """Invita a un usuario a unirse a una organización.

    Solo accesible por usuarios con rol MANAGER o superior. El usuario recibe
    un email con un enlace para completar su registro.

    Atributos:
        - org_id: UUID - El ID de la organización.
        - payload: Datos del usuario a invitar (email y rol).
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: Servicio de usuarios inyectado mediante dependencias.

    Retorna:
        - Mensaje de éxito con el email del usuario invitado.
        - 403 Forbidden si el usuario no tiene permisos.
        - 409 Conflict si el email ya está registrado.
        - 500 Internal Server Error para cualquier otro error inesperado.
    """
    try:
        user = await service.invite_user(
            organization_id=org_id,
            email=payload.email,
            role=payload.role,
            requested_by=current_user.user_id,
        )
        return {
            "id": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "message": f"Usuario invitado correctamente a la organización",
        }
    except DuplicateEntityError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.patch("/api/v1/organizations/{org_id}/users/{user_id}/role")
async def update_user_role(
    org_id: UUID,
    user_id: UUID,
    payload: UserRoleUpdateRequest,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_ROLES)),
    service: IUserService = Depends(get_user_service),
):
    """Actualiza el rol de un usuario dentro de una organización.

    Solo accesible por usuarios con rol MANAGER o superior.

    Atributos:
        - org_id: UUID - El ID de la organización.
        - user_id: UUID - El ID del usuario cuyo rol se actualizará.
        - payload: Nuevo rol para el usuario.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: Servicio de usuarios inyectado mediante dependencias.

    Retorna:
        - Usuario actualizado con su nuevo rol.
        - 403 Forbidden si el usuario no tiene permisos o intenta cambiar el rol del Owner.
        - 404 Not Found si el usuario no existe.
        - 500 Internal Server Error para cualquier otro error inesperado.
    """
    try:
        user = await service.update_user_role(
            user_id=user_id,
            organization_id=org_id,
            new_role=payload.role,
            requested_by=current_user.user_id,
        )
        return {
            "id": str(user.id),
            "email": user.email,
            "role": user.role.value,
        }
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/api/v1/organizations/{org_id}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user_from_org(
    org_id: UUID,
    user_id: UUID,
    current_user: CurrentUser = Depends(require_permission(Permission.MANAGE_ROLES)),
    service: IUserService = Depends(get_user_service),
):
    """Elimina a un usuario de una organización.

    El usuario podrá seguir usando el sistema pero perderá acceso a la organización.
    No es posible eliminar al Owner de la organización.

    Atributos:
        - org_id: UUID - El ID de la organización.
        - user_id: UUID - El ID del usuario a eliminar.
        - current_user: Usuario autenticado con permisos del token JWT.
        - service: Servicio de usuarios inyectado mediante dependencias.

    Retorna:
        - 204 No Content si el usuario fue eliminado correctamente.
        - 403 Forbidden si el usuario no tiene permisos o es el Owner.
        - 404 Not Found si el usuario no existe.
        - 500 Internal Server Error para cualquier otro error inesperado.
    """
    try:
        await service.remove_user_from_organization(
            user_id=user_id,
            organization_id=org_id,
            requested_by=current_user.user_id,
        )
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
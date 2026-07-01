import logging
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, ConfigDict, Field, model_validator
from application.ports.input.i_user_service import IUserService
from application.ports.input.i_organization_service import IOrganizationService
from application.ports.output.i_token_service import ITokenService
from infrastructure.secondary.database.repositories.user_membership_repository import SqlUserMembershipRepository
from core.dependencies import (
    get_user_service,
    get_organization_service,
    get_current_user,
    get_user_membership_repository,
    CurrentUser,
    require_permission,
    require_role,
    get_jwt_handler,
)
from core.audit import AuditEntry, AuditEvent, get_audit_logger
from core.email import email_service
from domain.enums import UserRole, Permission
from domain.exceptions import ValidationError
from . import ERROR_INTERNO

_log = logging.getLogger(__name__)

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
    confirm_password: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def passwords_match(self) -> "PasswordChangeRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("Las contraseñas no coinciden")
        return self

class UserInviteRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    email: str = Field(..., min_length=1, max_length=255)
    role: UserRole = Field(default=UserRole.U2)

class UserRoleUpdateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    role: UserRole

class AdminUserCreateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    email: str = Field(..., min_length=1, max_length=255)
    display_name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8, max_length=255)
    role: UserRole = Field(default=UserRole.U2)

class AdminRoleUpdateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    role: UserRole

class DeleteAccountRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    password: str = Field(..., min_length=1, description="Contraseña actual para confirmar la eliminación")

class SwitchOrganizationRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    organization_id: UUID


@router.get("/api/v1/users/me")
async def get_current_user_profile(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[IUserService, Depends(get_user_service)],
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
    user = await service.get_user_by_id(current_user.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role.value,
        "organization_id": str(user.organization_ids[0]) if user.organization_ids else None,
        "totp_enabled": user.totp_enabled,
    }


@router.patch("/api/v1/users/me")
async def update_current_user_profile(
    payload: UserUpdateRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[IUserService, Depends(get_user_service)],
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


@router.post("/api/v1/users/me/password")
async def change_password(
    payload: PasswordChangeRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[IUserService, Depends(get_user_service)],
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
    success = await service.change_password(
        user_id=current_user.user_id,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contraseña actual incorrecta")
    return {"message": "Contraseña cambiada correctamente"}


@router.delete("/api/v1/users/me/account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_account(
    body: DeleteAccountRequest,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[IUserService, Depends(get_user_service)],
    token_service: Annotated[ITokenService, Depends(get_jwt_handler)],
):
    try:
        await service.delete_user_account(
            user_id=current_user.user_id,
            requested_by=current_user.user_id,
            password=body.password,
        )
        token_service.blacklist_token(credentials.credentials, 0)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/api/v1/users/me/export")
async def export_user_data(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[IUserService, Depends(get_user_service)],
):
    """GDPR Art.20 — Export all personal data for the authenticated user."""
    user = await service.get_user_by_id(current_user.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    audit = get_audit_logger()
    audit.log(AuditEntry(
        event=AuditEvent.DATA_EXPORT_REQUESTED,
        user_id=user.id,
        organization_id=user.organization_id,
        resource_type="user",
        resource_id=user.id,
    ))

    return {
        "schema_version": "1.0",
        "export_format": "GDPR Art.20 Data Portability",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "role": user.role.value,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "terms_accepted_at": user.terms_accepted_at.isoformat() if user.terms_accepted_at else None,
            "privacy_accepted_at": user.privacy_accepted_at.isoformat() if user.privacy_accepted_at else None,
            "organization_ids": [str(oid) for oid in user.organization_ids],
        },
    }


@router.get("/api/v1/users/me/organizations")
async def list_my_organizations(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[IUserService, Depends(get_user_service)],
    org_service: Annotated[IOrganizationService, Depends(get_organization_service)],
):
    """Lista todas las organizaciones a las que pertenece el usuario autenticado, con su rol en cada una.

    Permite a un usuario que pertenece a varias organizaciones (ej. un técnico que
    trabaja para varios clientes) descubrir entre qué organizaciones puede cambiar.

    Retorna:
        - Lista de organizaciones con id, name, slug, role y si es la organización activa.
    """
    memberships = await service.list_user_organizations(current_user.user_id)
    result = []
    for membership in memberships:
        org = await org_service.get_organization(membership.organization_id)
        if not org:
            continue
        result.append({
            "organization_id": str(org.id),
            "name": org.name,
            "slug": org.slug,
            "role": membership.role.value,
            "is_active": org.id == current_user.organization_id,
        })
    return result


@router.post("/api/v1/users/me/switch-organization")
async def switch_organization(
    payload: SwitchOrganizationRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[IUserService, Depends(get_user_service)],
    jwt_handler: Annotated[ITokenService, Depends(get_jwt_handler)],
):
    """Cambia la organización activa del usuario autenticado y reemite los tokens JWT.

    El usuario debe tener una membership existente en la organización destino
    (creada, por ejemplo, mediante una invitación previa). El rol efectivo tras
    el cambio es el rol que el usuario tiene específicamente en esa organización,
    que puede ser distinto al que tenía en la organización anterior.

    Retorna:
        - Nuevos access_token/refresh_token con el organization_id y role actualizados.
        - 400 Bad Request si el usuario no pertenece a la organización solicitada.
    """
    try:
        user = await service.switch_active_organization(
            user_id=current_user.user_id,
            organization_id=payload.organization_id,
        )
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    access_token = jwt_handler.create_access_token(
        user_id=user.id,
        role=user.role.value,
        email=user.email,
        organization_id=user.organization_id,
        expires_in=3600,
    )
    refresh_token = jwt_handler.create_refresh_token(
        user_id=user.id,
        role=user.role.value,
        email=user.email,
        organization_id=user.organization_id,
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "organization_id": str(user.organization_id),
        "role": user.role.value,
    }


@router.get("/api/v1/organizations/{org_id}/users")
async def list_organization_users(
    org_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.MANAGE_ROLES))],
    service: Annotated[IUserService, Depends(get_user_service)],
    membership_repo: Annotated[SqlUserMembershipRepository, Depends(get_user_membership_repository)],
    skip: int = 0,
    limit: int = 50,
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
    if current_user.role != UserRole.U3 and current_user.organization_id != org_id:
        is_member = bool(await membership_repo.get(current_user.user_id, org_id))
        if not is_member:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes acceso a esta organización")
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


@router.post("/api/v1/organizations/{org_id}/users/invite", status_code=status.HTTP_201_CREATED)
async def invite_user(
    org_id: UUID,
    payload: UserInviteRequest,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.INVITE_USERS))],
    service: Annotated[IUserService, Depends(get_user_service)],
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
        # Un usuario ya activo que se une a una organización adicional conserva su
        # cuenta activa y no recibe un nuevo activation_token; solo se envía el
        # correo de activación cuando de verdad hay uno pendiente.
        if user.activation_token is not None:
            try:
                await email_service.send_activation_email(
                    to_email=user.email,
                    to_name=user.display_name,
                    token=user.activation_token,
                )
            except Exception:
                _log.warning("Activation email failed for invited user %s", user.email)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "message": "Usuario invitado correctamente a la organización",
    }


@router.patch("/api/v1/organizations/{org_id}/users/{user_id}/role")
async def update_user_role(
    org_id: UUID,
    user_id: UUID,
    payload: UserRoleUpdateRequest,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.MANAGE_ROLES))],
    service: Annotated[IUserService, Depends(get_user_service)],
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
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role.value,
    }


@router.delete("/api/v1/organizations/{org_id}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user_from_org(
    org_id: UUID,
    user_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.MANAGE_ROLES))],
    service: Annotated[IUserService, Depends(get_user_service)],
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
        - 500 Internal Server Error para cualquier error inesperado.
    """
    try:
        await service.remove_user_from_organization(
            user_id=user_id,
            organization_id=org_id,
            requested_by=current_user.user_id,
        )
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/api/v1/admin/users", status_code=status.HTTP_201_CREATED)
async def admin_create_user(
    payload: AdminUserCreateRequest,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.U3))],
    service: Annotated[IUserService, Depends(get_user_service)],
):
    """Crea un nuevo usuario en el sistema (solo U3).

    Atributos:
        - payload: Datos del usuario a crear.
        - current_user: Usuario autenticado con rol U3.
        - service: Servicio de usuarios inyectado mediante dependencias.

    Retorna:
        - 201 Created con la información del usuario creado.
        - 403 Forbidden si el usuario no es U3.
        - 409 Conflict si el email ya existe.
        - 500 Internal Server Error para cualquier error inesperado.
    """
    try:
        user = await service.create_user(
            email=payload.email,
            display_name=payload.display_name,
            password=payload.password,
            role=payload.role,
        )
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role.value,
    }


@router.patch("/api/v1/admin/users/{user_id}/activate")
async def admin_activate_user(
    user_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.U3))],
    service: Annotated[IUserService, Depends(get_user_service)],
):
    """Activa una cuenta de usuario (solo U3).

    Atributos:
        - user_id: UUID - El ID del usuario a activar.
        - current_user: Usuario autenticado con rol U3.
        - service: Servicio de usuarios inyectado mediante dependencias.

    Retorna:
        - 200 OK con el usuario activado.
        - 403 Forbidden si el usuario no es U3.
        - 404 Not Found si el usuario no existe.
        - 500 Internal Server Error para cualquier error inesperado.
    """
    user = await service.activate_user(user_id=user_id)
    return {
        "id": str(user.id),
        "email": user.email,
        "is_active": user.is_active,
    }


@router.patch("/api/v1/admin/users/{user_id}/deactivate")
async def admin_deactivate_user(
    user_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.U3))],
    service: Annotated[IUserService, Depends(get_user_service)],
):
    """Desactiva una cuenta de usuario (solo U3).

    Atributos:
        - user_id: UUID - El ID del usuario a desactivar.
        - current_user: Usuario autenticado con rol U3.
        - service: Servicio de usuarios inyectado mediante dependencias.

    Retorna:
        - 200 OK con el usuario desactivado.
        - 403 Forbidden si el usuario no es U3 o intenta desactivarse a sí mismo.
        - 404 Not Found si el usuario no existe.
        - 500 Internal Server Error para cualquier error inesperado.
    """
    try:
        user = await service.deactivate_user(user_id=user_id, requested_by=current_user.user_id)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    return {
        "id": str(user.id),
        "email": user.email,
        "is_active": user.is_active,
    }


@router.patch("/api/v1/admin/users/{user_id}/role")
async def admin_update_global_role(
    user_id: UUID,
    payload: AdminRoleUpdateRequest,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.U3))],
    service: Annotated[IUserService, Depends(get_user_service)],
):
    """Actualiza el rol global de un usuario (solo U3).

    Atributos:
        - user_id: UUID - El ID del usuario cuyo rol se actualizará.
        - payload: Nuevo rol global para el usuario.
        - current_user: Usuario autenticado con rol U3.
        - service: Servicio de usuarios inyectado mediante dependencias.

    Retorna:
        - 200 OK con el usuario actualizado.
        - 403 Forbidden si el usuario no es U3 o intenta cambiar su propio rol.
        - 404 Not Found si el usuario no existe.
        - 500 Internal Server Error para cualquier error inesperado.
    """
    try:
        user = await service.update_global_role(
            user_id=user_id,
            new_role=payload.role,
            requested_by=current_user.user_id,
        )
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role.value,
    }


@router.get("/api/v1/admin/users")
async def admin_list_users(
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.U3))],
    service: Annotated[IUserService, Depends(get_user_service)],
    skip: int = 0,
    limit: int = 50,
    is_active: bool | None = None,
    role: UserRole | None = None,
):
    """Lista todos los usuarios del sistema con filtros (solo U3).

    Atributos:
        - skip: int - Número de registros a omitir para paginación.
        - limit: int - Número máximo de registros a retornar.
        - is_active: bool - Filtrar por estado de activación.
        - role: UserRole - Filtrar por rol global.
        - current_user: Usuario autenticado con rol U3.
        - service: Servicio de usuarios inyectado mediante dependencias.

    Retorna:
        - Lista de usuarios con su información.
        - 403 Forbidden si el usuario no es U3.
        - 500 Internal Server Error para cualquier error inesperado.
    """
    users = await service.list_all_users(
        skip=skip,
        limit=limit,
        is_active=is_active,
        role=role,
    )
    return [
        {
            "id": str(u.id),
            "email": u.email,
            "display_name": u.display_name,
            "role": u.role.value,
            "is_active": u.is_active,
        }
        for u in users
    ]

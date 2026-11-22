from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, ConfigDict, Field, model_validator
from features.identity.application.ports.i_user_service import IUserService
from features.organizations.application.ports.i_organization_service import IOrganizationService
from features.identity.application.ports.i_token_service import ITokenService
from bootstrap.dependencies import (
    get_user_service,
    get_organization_service,
    get_current_user,
    CurrentUser,
    get_jwt_handler,
)
from shared.infrastructure.audit import AuditEntry, AuditEvent, get_audit_logger
from shared.domain.exceptions import ValidationError


router = APIRouter(tags=["Users"])


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
        token_version=user.token_version,
    )
    refresh_token = jwt_handler.create_refresh_token(
        user_id=user.id,
        role=user.role.value,
        email=user.email,
        organization_id=user.organization_id,
        token_version=user.token_version,
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "organization_id": str(user.organization_id),
        "role": user.role.value,
    }

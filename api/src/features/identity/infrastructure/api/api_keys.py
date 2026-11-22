from uuid import UUID
from typing import Annotated, Optional
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from features.identity.application.ports.i_api_key_repository import IAPIKeyRepository
from features.identity.application.use_cases.manage_api_keys import ManageApiKeysUseCase
from shared.infrastructure.audit_db import get_audit_logger
from shared.infrastructure.config import get_settings
from bootstrap.dependencies import get_current_user, CurrentUser, get_api_key_repository, get_user_repository
from features.identity.application.ports.i_user_repository import IUserRepository
from shared.domain.exceptions import ValidationError, EntityNotFoundError
from shared.infrastructure.api_errors import ERROR_INTERNO, handle_internal_errors

_log = logging.getLogger(__name__)

router = APIRouter(tags=["API Keys"])


class CreateAPIKeyRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(..., min_length=1, max_length=100)
    expires_in_days: Optional[int] = Field(None, ge=1)


class APIKeyResponse(BaseModel):
    id: str
    user_id: str
    organization_id: str
    name: str
    key: Optional[str] = None
    prefix: str
    is_active: bool
    expires_at: Optional[str] = None
    created_at: str
    last_used_at: Optional[str] = None


@router.post("/api/v1/users/{user_id}/api-keys", status_code=status.HTTP_201_CREATED)
async def create_api_key(
    user_id: UUID,
    payload: CreateAPIKeyRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    api_key_repo: Annotated[IAPIKeyRepository, Depends(get_api_key_repository)],
    user_repo: Annotated[IUserRepository, Depends(get_user_repository)],
):
    """Crea una nueva API key para el usuario autenticado.

    La API key puede tener una fecha de expiración opcional. Solo el propio
    usuario puede crear API keys para su cuenta.

    Atributos:
        - user_id: UUID - El ID del usuario para el que se crea la API key.
        - payload: Datos de la API key (nombre y días de expiración opcionales).
        - current_user: Usuario autenticado con permisos del token JWT.
        - api_key_repo: Repositorio de API keys inyectado mediante dependencias.

    Retorna:
        - 201 Created con los datos de la API key creada (incluyendo la clave completa).
        - 400 Bad Request si el usuario no pertenece a una organización.
        - 403 Forbidden si el usuario intenta crear una API key para otro usuario.
        - 409 Conflict si los datos de la API key no son válidos.
        - 500 Internal Server Error para cualquier error inesperado.
    """
    if current_user.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No puedes crear API keys para otros usuarios")

    organization_id = current_user.organization_id
    if organization_id is None:
        db_user = await user_repo.get_by_id(user_id)
        organization_id = db_user.organization_id if db_user else None

    if organization_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El usuario no pertenece a una organización")

    try:
        use_case = ManageApiKeysUseCase(api_key_repository=api_key_repo, audit_logger=get_audit_logger(), api_key_pepper=get_settings().api_key_pepper)
        result = await use_case.create_api_key(
            user_id=user_id,
            organization_id=organization_id,
            name=payload.name,
            expires_in_days=payload.expires_in_days,
        )
        return APIKeyResponse(**result)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        _log.exception("Error creating API key: user_id=%s, organization_id=%s, error=%s", user_id, organization_id, str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


@router.get("/api/v1/users/{user_id}/api-keys")
@handle_internal_errors
async def list_api_keys(
    user_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    api_key_repo: Annotated[IAPIKeyRepository, Depends(get_api_key_repository)],
):
    """Lista las API keys del usuario autenticado.

    Solo el propio usuario puede ver sus API keys. La clave completa solo se
    muestra en el momento de la creación; este endpoint retorna solo el prefijo.

    Atributos:
        - user_id: UUID - El ID del usuario cuyas API keys se listan.
        - current_user: Usuario autenticado con permisos del token JWT.
        - api_key_repo: Repositorio de API keys inyectado mediante dependencias.

    Retorna:
        - 200 OK con la lista de API keys del usuario.
        - 403 Forbidden si el usuario intenta ver las API keys de otro usuario.
        - 500 Internal Server Error para cualquier error inesperado.
    """
    if current_user.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No puedes ver las API keys de otros usuarios")
    use_case = ManageApiKeysUseCase(api_key_repository=api_key_repo, audit_logger=get_audit_logger(), api_key_pepper=get_settings().api_key_pepper)
    keys = await use_case.list_api_keys(user_id)
    return keys


@router.delete("/api/v1/users/{user_id}/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_internal_errors
async def revoke_api_key(
    user_id: UUID,
    key_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    api_key_repo: Annotated[IAPIKeyRepository, Depends(get_api_key_repository)],
):
    """Revoca (invalida) una API key del usuario autenticado.

    Una vez revocada, la API key ya no podrá usarse para autenticar solicitudes.
    Solo el propio usuario puede revocar sus API keys.

    Atributos:
        - user_id: UUID - El ID del usuario propietario de la API key.
        - key_id: UUID - El ID de la API key a revocar.
        - current_user: Usuario autenticado con permisos del token JWT.
        - api_key_repo: Repositorio de API keys inyectado mediante dependencias.

    Retorna:
        - 204 No Content si la API key fue revocada correctamente.
        - 403 Forbidden si el usuario intenta revocar una API key de otro usuario.
        - 404 Not Found si la API key no existe.
        - 500 Internal Server Error para cualquier error inesperado.
    """
    if current_user.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No puedes revocar API keys de otros usuarios")
    try:
        use_case = ManageApiKeysUseCase(api_key_repository=api_key_repo, audit_logger=get_audit_logger(), api_key_pepper=get_settings().api_key_pepper)
        await use_case.revoke_api_key(key_id, user_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

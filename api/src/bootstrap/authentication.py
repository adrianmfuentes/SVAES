from __future__ import annotations

from dataclasses import dataclass
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from fastapi import status
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security import HTTPBearer
from features.identity.container import get_jwt_handler, get_settings_dependency
from features.identity.infrastructure.persistence.api_key_repository import SqlAPIKeyRepository
from features.identity.infrastructure.persistence.user_repository import SqlUserRepository
from shared.domain.enums import UserRole
from shared.infrastructure.audit_db import get_audit_logger
from shared.infrastructure.config import Settings
from shared.infrastructure.config import get_settings
from typing import Optional
from uuid import UUID


_bearer = HTTPBearer(auto_error=False)


_INVALID_TOKEN = "Token inválido"


_API_KEY_HDR = "X-API-Key"


async def get_current_user_or_api_key(
    request: Request,
    settings: Settings = Depends(get_settings_dependency),
) -> CurrentUser:
    raw_key = request.headers.get(_API_KEY_HDR)
    if raw_key:
        api_key_user = await _validate_api_key(raw_key)
        if api_key_user:
            return api_key_user
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_TOKEN)

    credentials = None
    try:
        credentials = await _bearer(request)
    except Exception:
        pass

    if credentials:
        handler = get_jwt_handler(settings)
        try:
            payload = handler.decode_token(credentials.credentials)
            user_repo = SqlUserRepository()
            db_user = await user_repo.get_by_id(payload.user_id)
            if not db_user or not db_user.is_active:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_TOKEN)
            if (payload.token_version or 0) != db_user.token_version:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_TOKEN)
            return CurrentUser(
                user_id=payload.user_id,
                role=UserRole(payload.role),
                email=payload.email,
                organization_id=payload.organization_id,
            )
        except HTTPException:
            raise
        except ValueError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_TOKEN)

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_TOKEN)


async def get_current_user_api_key_only(
    request: Request,
) -> "CurrentUser":
    raw_key = request.headers.get(_API_KEY_HDR)
    if not raw_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_TOKEN)
    api_key_user = await _validate_api_key(raw_key)
    if not api_key_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_TOKEN)
    return api_key_user


async def _validate_api_key(raw_key: str) -> Optional[CurrentUser]:
    from features.identity.application.use_cases.manage_api_keys import ManageApiKeysUseCase

    try:
        repo = SqlAPIKeyRepository()
        user_repo = SqlUserRepository()
        use_case = ManageApiKeysUseCase(api_key_repository=repo, audit_logger=get_audit_logger(), api_key_pepper=get_settings().api_key_pepper)
        api_key = await use_case.validate_api_key(raw_key)
        if not api_key:
            return None
        db_user = await user_repo.get_by_id(api_key.user_id)
        if not db_user or not db_user.is_active:
            return None
        role = db_user.role
        return CurrentUser(
            user_id=api_key.user_id,
            role=role,
            email=db_user.email if db_user else "api_key_user",
            organization_id=api_key.organization_id,
            auth_via_api_key=True,
        )
    except Exception:
        return None


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    settings: Settings = Depends(get_settings_dependency),
) -> UUID:
    handler = get_jwt_handler(settings)
    try:
        payload = handler.decode_token(credentials.credentials)
        return payload.user_id
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_TOKEN)


def get_current_user_role(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    settings: Settings = Depends(get_settings_dependency),
):
    handler = get_jwt_handler(settings)
    try:
        payload = handler.decode_token(credentials.credentials)
        return UserRole(payload.role)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_TOKEN)


@dataclass
class CurrentUser:
    user_id: UUID
    role: UserRole
    email: str
    organization_id: Optional[UUID] = None
    auth_via_api_key: bool = False


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    settings: Settings = Depends(get_settings_dependency),
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_TOKEN)
    handler = get_jwt_handler(settings)
    try:
        payload = handler.decode_token(credentials.credentials)
        user_repo = SqlUserRepository()
        user = await user_repo.get_by_id(payload.user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_TOKEN)
        if (payload.token_version or 0) != user.token_version:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_TOKEN)
        return CurrentUser(
            user_id=payload.user_id,
            role=UserRole(payload.role),
            email=payload.email,
            organization_id=payload.organization_id,
        )
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_TOKEN)

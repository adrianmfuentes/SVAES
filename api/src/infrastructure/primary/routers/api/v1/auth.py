from typing import Annotated
import hashlib
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from application.ports.input.i_auth_service import IAuthService
from application.ports.input.i_user_service import IUserService
from core.dependencies import get_auth_service, get_user_service, get_current_user, CurrentUser
from core.rate_limit import rate_limit_auth
from domain.exceptions import ValidationError, DuplicateEntityError
from domain.enums import UserRole
from . import ERROR_INTERNO

_log = logging.getLogger(__name__)

router = APIRouter(tags=["Auth"])


def _hash_email(email: str) -> str:
    return hashlib.sha256(email.encode()).hexdigest()[:16]


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=255)


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    refresh_token: str


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=255)
    display_name: str = Field(..., min_length=1, max_length=255)
    accept_terms: bool
    accept_privacy_policy: bool

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("La contraseña debe contener al menos una letra mayúscula")
        if not any(c.islower() for c in v):
            raise ValueError("La contraseña debe contener al menos una letra minúscula")
        if not any(c.isdigit() for c in v):
            raise ValueError("La contraseña debe contener al menos un número")
        return v

    @model_validator(mode="after")
    def check_consent(self) -> "RegisterRequest":
        if not self.accept_terms:
            raise ValueError("Debe aceptar los términos de servicio")
        if not self.accept_privacy_policy:
            raise ValueError("Debe aceptar la política de privacidad")
        return self


class TotpVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    totp_token: str = Field(..., min_length=1)
    code: str = Field(..., min_length=6, max_length=8)


class TotpCodeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(..., min_length=6, max_length=8)


@router.post("/api/v1/auth/login")
@rate_limit_auth()
async def login(
    request: Request,
    payload: LoginRequest,
    service: Annotated[IAuthService, Depends(get_auth_service)],
):
    try:
        result = await service.authenticate(
            email=payload.email,
            password=payload.password,
        )
        if result.requires_2fa:
            return {"requires_2fa": True, "totp_token": result.totp_token}
        return {
            "access_token": str(result.tokens.access_token),
            "refresh_token": str(result.tokens.refresh_token),
            "token_type": str(result.tokens.token_type),
            "user_id": str(result.user_id),
            "role": str(result.role),
        }
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=e.message)
    except Exception as e:
        _log.exception("Login failed for user hash=%s", _hash_email(payload.email))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


@router.post("/api/v1/auth/2fa/verify")
@rate_limit_auth()
async def verify_2fa(
    request: Request,
    payload: TotpVerifyRequest,
    service: Annotated[IAuthService, Depends(get_auth_service)],
):
    try:
        result = await service.verify_totp(payload.totp_token, payload.code)
        return {
            "access_token": str(result.tokens.access_token),
            "refresh_token": str(result.tokens.refresh_token),
            "token_type": str(result.tokens.token_type),
            "user_id": str(result.user_id),
            "role": str(result.role),
        }
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=e.message)
    except Exception:
        _log.exception("2FA verify failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


@router.get("/api/v1/auth/2fa/setup")
async def setup_2fa(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[IAuthService, Depends(get_auth_service)],
):
    try:
        result = await service.setup_totp(current_user.user_id)
        return {
            "totp_uri": result.totp_uri,
            "secret": result.secret,
            "qr_data_url": result.qr_data_url,
        }
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except Exception:
        _log.exception("2FA setup failed for user=%s", current_user.user_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


@router.post("/api/v1/auth/2fa/enable")
async def enable_2fa(
    payload: TotpCodeRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[IAuthService, Depends(get_auth_service)],
):
    try:
        await service.enable_totp(current_user.user_id, payload.code)
        return {"message": "2FA activado correctamente"}
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except Exception:
        _log.exception("2FA enable failed for user=%s", current_user.user_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


@router.post("/api/v1/auth/2fa/disable")
async def disable_2fa(
    payload: TotpCodeRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[IAuthService, Depends(get_auth_service)],
):
    try:
        await service.disable_totp(current_user.user_id, payload.code)
        return {"message": "2FA desactivado correctamente"}
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except Exception:
        _log.exception("2FA disable failed for user=%s", current_user.user_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


@router.post("/api/v1/auth/register", status_code=status.HTTP_201_CREATED)
@rate_limit_auth()
async def register(
    request: Request,
    payload: RegisterRequest,
    user_service: Annotated[IUserService, Depends(get_user_service)],
):
    now = datetime.now(timezone.utc)
    try:
        user = await user_service.create_user(
            email=payload.email,
            display_name=payload.display_name,
            password=payload.password,
            role=UserRole.U2,
            terms_accepted_at=now,
            privacy_accepted_at=now,
        )
        return {
            "user_id": str(user.id),
            "links": {
                "terms": "/legal/terms",
                "privacy": "/legal/privacy",
            },
        }
    except DuplicateEntityError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        _log.exception("Register failed for user hash=%s", _hash_email(payload.email))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


@router.post("/api/v1/auth/refresh")
@rate_limit_auth()
async def refresh(
    request: Request,
    payload: RefreshRequest,
    service: Annotated[IAuthService, Depends(get_auth_service)],
):
    try:
        tokens = await service.refresh_access_token(payload.refresh_token)
        if not tokens:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido o expirado")
        return {
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "token_type": tokens.token_type,
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


class ActivateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    activation_token: str = Field(..., min_length=1)
    password: str = Field(..., min_length=8, max_length=255)
    password_confirm: str = Field(..., min_length=1, max_length=255)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("La contraseña debe contener al menos una letra mayúscula")
        if not any(c.islower() for c in v):
            raise ValueError("La contraseña debe contener al menos una letra minúscula")
        if not any(c.isdigit() for c in v):
            raise ValueError("La contraseña debe contener al menos un número")
        if not any(not c.isalnum() for c in v):
            raise ValueError("La contraseña debe contener al menos un carácter especial")
        return v

    @model_validator(mode="after")
    def passwords_match(self) -> "ActivateRequest":
        if self.password != self.password_confirm:
            raise ValueError("Las contraseñas no coinciden")
        return self


@router.post("/api/v1/auth/activate")
async def activate_account(
    payload: ActivateRequest,
    auth_service: Annotated[IAuthService, Depends(get_auth_service)],
):
    from infrastructure.secondary.database.repositories.user_repository import SqlUserRepository
    from infrastructure.primary.middleware.password_hasher import BcryptPasswordHasher

    user_repo = SqlUserRepository()
    hasher = BcryptPasswordHasher()

    user = await user_repo.get_by_activation_token(payload.activation_token)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token de activación inválido.")

    now = datetime.now(timezone.utc)
    expiry = user.activation_token_expiry
    if expiry and expiry.tzinfo is None:
        from datetime import timezone as tz
        expiry = expiry.replace(tzinfo=tz.utc)
    if expiry and expiry < now:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="El token de activación ha expirado.")

    user.hashed_password = hasher.hash_password(payload.password)
    user.is_active = True
    user.activation_token = None
    user.activation_token_expiry = None
    await user_repo.update(user)

    try:
        result = await auth_service.authenticate(user.email, payload.password)
        if result.tokens is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)
        return {
            "access_token": str(result.tokens.access_token),
            "refresh_token": str(result.tokens.refresh_token),
            "token_type": str(result.tokens.token_type),
        }
    except Exception:
        _log.exception("[activate] authenticate failed for %s", user.email)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)


@router.post("/api/v1/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[IAuthService, Depends(get_auth_service)],
):
    try:
        await service.logout(current_user.user_id, credentials.credentials)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)

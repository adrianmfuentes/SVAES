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
from slowapi import Limiter
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


@router.post("/api/v1/auth/login")
@rate_limit_auth()
async def login(
    request: Request,
    payload: LoginRequest,
    service: Annotated[IAuthService, Depends(get_auth_service)],
):
    try:
        tokens, user_id, role = await service.authenticate(
            email=payload.email,
            password=payload.password,
        )
        return {
            "access_token": str(tokens.access_token),
            "refresh_token": str(tokens.refresh_token),
            "token_type": str(tokens.token_type),
            "user_id": str(user_id),
            "role": str(role),
        }
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=e.message)
    except Exception as e:
        _log.exception("Login failed for user hash=%s", _hash_email(payload.email))
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

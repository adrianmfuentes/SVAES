from typing import Annotated
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, ConfigDict, Field
from application.ports.input.i_auth_service import IAuthService
from application.ports.input.i_user_service import IUserService
from core.dependencies import get_auth_service, get_user_service, get_current_user, CurrentUser
from core.rate_limit import rate_limit_auth
from slowapi import Limiter
from domain.exceptions import ValidationError, DuplicateEntityError
from domain.enums import UserRole

_log = logging.getLogger(__name__)
router = APIRouter(tags=["Auth"])


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
    password: str = Field(..., min_length=1, max_length=255)
    display_name: str = Field(..., min_length=1, max_length=255)
    role: UserRole = Field(default=UserRole.U2)


@router.post("/api/v1/auth/login")
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
        _log.exception("Login failed for %s: %s", payload.email, e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno")


@router.post("/api/v1/auth/register", status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    payload: RegisterRequest,
    user_service: Annotated[IUserService, Depends(get_user_service)],
):
    try:
        user = await user_service.create_user(
            email=payload.email,
            display_name=payload.display_name,
            password=payload.password,
            role=payload.role,
        )
        return {"user_id": str(user.id)}
    except DuplicateEntityError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        _log.exception("Register failed for %s: %s", payload.email, e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


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
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/api/v1/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[IAuthService, Depends(get_auth_service)],
):
    try:
        await service.logout(current_user.user_id, credentials.credentials)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
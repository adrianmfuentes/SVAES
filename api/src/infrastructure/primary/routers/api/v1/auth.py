from typing import Annotated
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from application.ports.input.i_auth_service import IAuthService
from application.ports.input.i_user_service import IUserService
from core.dependencies import get_auth_service, get_user_service
from core.rate_limit import rate_limit_auth
from slowapi import Limiter
from domain.exceptions import ValidationError, DuplicateEntityError
from domain.enums import UserRole

_log = logging.getLogger(__name__)

router = APIRouter(tags=["Auth"])


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    email: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=255)


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    refresh_token: str


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
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
    """Endpoint para autenticar a un usuario. Recibe un email y contraseña, y devuelve tokens de acceso y refresco si las credenciales son válidas.

    Atributos:
        - payload: LoginRequest - El cuerpo de la solicitud, que incluye el email y la contraseña del usuario.
        - service: IAuthService - El servicio de autenticación, inyectado mediante dependencias.

    Retorna:
        - Un diccionario con el access_token, refresh_token, token_type, user_id y role si la autenticación es exitosa.
        - Lanza HTTPException con status 401 si las credenciales son inválidas o el usuario está inactivo.
        - Lanza HTTPException con status 500 para cualquier otro error inesperado.
    """
    try:
        _log.info("Login attempt")
        tokens, user_id, role = await service.authenticate(
            email=payload.email,
            password=payload.password,
        )
        _log.info("Login successful for user_id=%s", user_id)
        return {
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "token_type": tokens.token_type,
            "user_id": str(user_id),
            "role": role.value,
        }
    except ValidationError as e:
        _log.warning("Login validation error: %s", e)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        _log.exception("Login failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/api/v1/auth/register", status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    payload: RegisterRequest,
    user_service: Annotated[IUserService, Depends(get_user_service)],
):
    """Endpoint para registrar un nuevo usuario.

    Atributos:
        - payload: RegisterRequest - El cuerpo de la solicitud, que incluye email, password,
            display_name y role del usuario.
        - user_service: IUserService - El servicio de usuario, inyectado mediante dependencias.

    Retorna:
        - Un diccionario con el user_id si el registro es exitoso.
        - Lanza HTTPException con status 400 si el email ya existe.
        - Lanza HTTPException con status 500 para cualquier otro error inesperado.
    """
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
    """Endpoint para refrescar el token de acceso utilizando un refresh token válido.

    Atributos:
        - payload: RefreshRequest - El cuerpo de la solicitud, que incluye el refresh token.
        - service: IAuthService - El servicio de autenticación, inyectado mediante dependencias.

    Retorna:
        - Un diccionario con el nuevo access_token, refresh_token y token_type si el refresh
            token es válido.
        - Lanza HTTPException con status 401 si el refresh token es inválido o expirado.
        - Lanza HTTPException con status 500 para cualquier otro error inesperado.    
    """
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
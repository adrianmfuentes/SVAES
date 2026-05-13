from typing import Optional, Tuple
from uuid import UUID
from application.ports.input.i_auth_service import IAuthService, AuthTokens
from application.ports.output.i_user_repository import IUserRepository
from application.ports.output.i_token_service import ITokenService, TokenPayload
from application.ports.output.i_password_hasher import IPasswordHasher
from domain.entities.user import User
from domain.enums import UserRole
from domain.exceptions import ValidationError

"""
Este módulo define el servicio de autenticación, que es responsable de gestionar la autenticación de usuarios dentro del sistema. Incluye la lógica de 
negocio para autenticar a los usuarios, generar tokens de acceso y refresco, y validar tokens.
"""
class AuthService(IAuthService):
    def __init__(
        self,
        user_repository: IUserRepository,
        token_service: ITokenService,
        password_hasher: IPasswordHasher,
    ) -> None:
        self._user_repo = user_repository
        self._token_service = token_service
        self._password_hasher = password_hasher


    async def authenticate(
        self,
        email: str,
        password: str,
    ) -> Tuple[AuthTokens, UUID, UserRole]:
        user = await self._user_repo.get_by_email(email)
        if not user:
            raise ValidationError("Credenciales inválidas")

        if not user.is_active:
            raise ValidationError("Usuario inactivo")

        if not self._password_hasher.verify_password(password, user.hashed_password):
            raise ValidationError("Credenciales inválidas")

        access_token = self._token_service.create_access_token(
            user_id=user.id,
            role=user.role,
            email=user.email,
            organization_id=user.organization_id,
            expires_in=3600,
        )
        refresh_token = self._token_service.create_access_token(
            user_id=user.id,
            role=user.role,
            email=user.email,
            organization_id=user.organization_id,
            expires_in=86400,
        )

        tokens = AuthTokens(access_token=access_token, refresh_token=refresh_token)
        return tokens, user.id, user.role


    async def refresh_access_token(self, refresh_token: str) -> Optional[AuthTokens]:
        try:
            payload = self._token_service.decode_token(refresh_token)
        except ValueError:
            return None

        access_token = self._token_service.create_access_token(
            user_id=payload.user_id,
            role=payload.role,
            email=payload.email,
            organization_id=payload.organization_id,
            expires_in=3600,
        )
        new_refresh_token = self._token_service.create_access_token(
            user_id=payload.user_id,
            role=payload.role,
            email=payload.email,
            organization_id=payload.organization_id,
            expires_in=86400,
        )

        return AuthTokens(access_token=access_token, refresh_token=new_refresh_token)
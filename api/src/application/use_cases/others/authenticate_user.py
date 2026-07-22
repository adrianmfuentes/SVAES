from dataclasses import dataclass
from uuid import UUID
from application.ports.output.i_user_repository import IUserRepository
from application.ports.output.i_token_service import ITokenService
from application.ports.output.i_password_hasher import IPasswordHasher
from domain.enums import UserRole

@dataclass
class AuthResult:
    access_token: str
    refresh_token: str
    user_id: UUID
    role: UserRole
    token_type: str = "bearer"

"""
Este módulo define el caso de uso para autenticar a un usuario, que es responsable de validar las credenciales del usuario y generar tokens de acceso y
refresco. Incluye la lógica de negocio para verificar que el usuario existe, que está activo, y que las credenciales son correctas. 

Si la autenticación es exitosa, se generan un token de acceso con una duración corta (por ejemplo, 1 hora) y un token de refresco con una duración más larga 
(por ejemplo, 24 horas).

Si la autenticación falla por cualquier motivo (usuario no encontrado, usuario inactivo, contraseña incorrecta), se lanza una excepción con un mensaje 
de error genérico para evitar revelar información sensible.
"""
class AuthenticateUserUseCase:
    def __init__(
        self,
        user_repository: IUserRepository,
        token_service: ITokenService,
        password_hasher: IPasswordHasher,
    ) -> None:
        self._user_repo = user_repository
        self._token_service = token_service
        self._password_hasher = password_hasher

    async def execute(self, email: str, password: str) -> AuthResult:
        user = await self._user_repo.get_by_email(email)
        if not user:
            raise ValueError("Credenciales inválidas")

        if not user.is_active:
            raise ValueError("Usuario inactivo")

        if not self._password_hasher.verify_password(password, user.hashed_password):
            raise ValueError("Credenciales inválidas")

        access_token = self._token_service.create_access_token(
            user_id=user.id,
            role=user.role.value,
            email=user.email,
            organization_id=user.organization_id,
            expires_in=3600,
            token_version=user.token_version,
        )
        refresh_token = self._token_service.create_refresh_token(
            user_id=user.id,
            role=user.role.value,
            email=user.email,
            organization_id=user.organization_id,
            token_version=user.token_version,
        )

        return AuthResult(
            access_token=access_token,
            refresh_token=refresh_token,
            user_id=user.id,
            role=user.role,
        )
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

        return AuthResult(
            access_token=access_token,
            refresh_token=refresh_token,
            user_id=user.id,
            role=user.role,
        )
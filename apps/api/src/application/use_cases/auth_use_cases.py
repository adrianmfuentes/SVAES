from dataclasses import dataclass
from domain.ports.i_user_repository import IUserRepository
from domain.ports.i_password_hasher import IPasswordHasher
from domain.ports.i_token_service import ITokenService
from infrastructure.logging.logger import get_logger

_log = get_logger(__name__)


@dataclass
class LoginCommand:
    email: str
    password_plain: str


class LoginUseCase:
    """Application service for user authentication. Returns a signed JWT on success.

    Intentionally raises ValueError (not EntityNotFoundError) on bad credentials
    to avoid leaking whether the email exists.
    """

    def __init__(
        self,
        user_repo: IUserRepository,
        password_hasher: IPasswordHasher,
        token_service: ITokenService,
    ) -> None:
        self.user_repo = user_repo
        self.password_hasher = password_hasher
        self.token_service = token_service

    async def execute(self, command: LoginCommand) -> str:
        user = await self.user_repo.get_by_email(command.email)
        if not user or not self.password_hasher.verify(command.password_plain, user.hashed_password):
            _log.warning("Failed login attempt for email=%s", command.email)
            raise ValueError("Credenciales inválidas")

        token = self.token_service.create_access_token(user_id=user.id, role=user.role.value)
        _log.info("User %s authenticated successfully", user.id)
        return token

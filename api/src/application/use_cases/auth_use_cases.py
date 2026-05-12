from dataclasses import dataclass
from domain.ports.i_user_repository import IUserRepository
from domain.ports.i_password_hasher import IPasswordHasher
from domain.ports.i_token_service import ITokenService
from infrastructure.logging.logger import get_logger

_log = get_logger(__name__)

@dataclass
class LoginCommand:
    """Command object for login use case."""
    email: str
    password_plain: str

class LoginUseCase:
    """Use case for user login. Validates credentials and returns an access token if successful.

    Attributes:
        user_repo (IUserRepository): Repository for accessing user data.
        password_hasher (IPasswordHasher): Service for hashing and verifying passwords.
        token_service (ITokenService): Service for creating access tokens.

    Raises:
        ValueError: If the credentials are invalid.
    
    Logs:
        - Warning: Failed login attempt with email.
        - Info: Successful authentication of user.
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
            raise ValueError("Invalid credentials")

        token = self.token_service.create_access_token(user_id=user.id, role=user.role.value)
        _log.info("User %s authenticated successfully", user.id)
        return token

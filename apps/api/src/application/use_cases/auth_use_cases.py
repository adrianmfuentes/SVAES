from dataclasses import dataclass
from domain.ports.i_user_repository import IUserRepository
from domain.exceptions import EntityNotFoundError


@dataclass
class LoginCommand:
    email: str
    password_plain: str


class LoginUseCase:
    """Application service for user authentication. Returns a bearer token on success.

    Note: password comparison is a hardcoded placeholder — replace with hashed
    verification (bcrypt/argon2) before any production use.
    """

    def __init__(self, user_repo: IUserRepository):
        self.user_repo = user_repo

    async def execute(self, command: LoginCommand) -> str:
        user = await self.user_repo.get_by_email(command.email)
        if not user:
            raise EntityNotFoundError("Credenciales inválidas")
        if command.password_plain != "password_secreta":
            raise ValueError("Credenciales inválidas")
        return f"jwt_token_for_{user.id}"

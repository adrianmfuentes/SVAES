import uuid
from dataclasses import dataclass
from typing import List, Optional

from domain.entities.user import User
from domain.entities.enums import UserRole
from domain.exceptions import EntityNotFoundError, DuplicateEntityError
from domain.ports.i_user_repository import IUserRepository
from domain.ports.i_password_hasher import IPasswordHasher
from domain.ports.i_token_service import ITokenService


@dataclass
class RegisterUserCommand:
    email: str
    password_plain: str
    role: UserRole = UserRole.OPERATOR


@dataclass
class CreateUserCommand:
    email: str
    password_plain: str
    role: UserRole


@dataclass
class UpdateUserCommand:
    user_id: uuid.UUID
    email: str | None = None
    role: UserRole | None = None


class RegisterUserUseCase:
    def __init__(
        self,
        user_repo: IUserRepository,
        password_hasher: IPasswordHasher,
        token_service: ITokenService,
    ) -> None:
        self.user_repo = user_repo
        self.password_hasher = password_hasher
        self.token_service = token_service

    async def execute(self, command: RegisterUserCommand) -> str:
        existing = await self.user_repo.get_by_email(command.email)
        if existing:
            raise DuplicateEntityError(f"Email {command.email} is already registered")

        user = User(
            id=uuid.uuid4(),
            email=command.email,
            hashed_password=self.password_hasher.hash(command.password_plain),
            role=command.role,
            organization_id=None,
        )
        await self.user_repo.create(user)
        return self.token_service.create_access_token(user_id=user.id, role=user.role.value)


class CreateUserUseCase:
    def __init__(
        self,
        user_repo: IUserRepository,
        password_hasher: IPasswordHasher,
    ) -> None:
        self.user_repo = user_repo
        self.password_hasher = password_hasher

    async def execute(self, command: CreateUserCommand) -> User:
        existing = await self.user_repo.get_by_email(command.email)
        if existing:
            raise DuplicateEntityError(f"Email {command.email} is already registered")

        user = User(
            id=uuid.uuid4(),
            email=command.email,
            hashed_password=self.password_hasher.hash(command.password_plain),
            role=command.role,
            organization_id=None,
        )
        return await self.user_repo.create(user)


class GetUserUseCase:
    def __init__(self, user_repo: IUserRepository) -> None:
        self.user_repo = user_repo

    async def execute(self, user_id: uuid.UUID) -> User:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise EntityNotFoundError(f"User {user_id} not found")
        return user


class ListUsersUseCase:
    def __init__(self, user_repo: IUserRepository) -> None:
        self.user_repo = user_repo

    async def execute(self, active_only: bool = True) -> List[User]:
        return await self.user_repo.list_all(active_only=active_only)


class UpdateUserUseCase:
    def __init__(self, user_repo: IUserRepository) -> None:
        self.user_repo = user_repo

    async def execute(self, command: UpdateUserCommand) -> User:
        user = await self.user_repo.get_by_id(command.user_id)
        if not user:
            raise EntityNotFoundError(f"User {command.user_id} not found")

        if command.email is not None:
            user.email = command.email
        if command.role is not None:
            user.role = command.role

        return await self.user_repo.update(user)


class DeleteUserUseCase:
    def __init__(self, user_repo: IUserRepository) -> None:
        self.user_repo = user_repo

    async def execute(self, user_id: uuid.UUID) -> None:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise EntityNotFoundError(f"User {user_id} not found")
        await self.user_repo.delete(user_id)

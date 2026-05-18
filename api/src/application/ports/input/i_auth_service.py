from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from uuid import UUID
from domain.enums import UserRole


@dataclass
class AuthTokens:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class IAuthService(ABC):
    @abstractmethod
    async def authenticate(
        self,
        email: str,
        password: str,
    ) -> tuple[AuthTokens, UUID, UserRole]:
        pass

    @abstractmethod
    async def refresh_access_token(self, refresh_token: str) -> Optional[AuthTokens]:
        pass

    @abstractmethod
    async def logout(self, user_id: UUID, token: str) -> None:
        pass
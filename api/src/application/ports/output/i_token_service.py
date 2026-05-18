from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any
from uuid import UUID

from domain.enums import UserRole


@dataclass
class TokenPayload:
    user_id: UUID
    role: UserRole
    email: str
    organization_id: Optional[UUID] = None
    exp: Optional[int] = None
    iat: Optional[int] = None


class ITokenService(ABC):
    @abstractmethod
    def create_access_token(
        self,
        user_id: UUID,
        role: UserRole,
        email: str,
        organization_id: Optional[UUID] = None,
        expires_in: int = 3600,
    ) -> str:
        pass

    @abstractmethod
    def decode_token(self, token: str) -> TokenPayload:
        pass

    @abstractmethod
    def verify_token(self, token: str) -> bool:
        pass

    @abstractmethod
    def refresh_token(self, token: str) -> Optional[str]:
        pass

    @abstractmethod
    def blacklist_token(self, token: str, expires_in_seconds: int) -> None:
        pass

    @abstractmethod
    def is_token_blacklisted(self, token: str) -> bool:
        pass
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
    token_version: Optional[int] = None


class ITokenService(ABC):
    @abstractmethod
    def create_access_token(
        self,
        user_id: UUID,
        role: str,
        email: Optional[str] = None,
        organization_id: Optional[UUID] = None,
        expires_in: Optional[int] = None,
        token_version: int = 0,
    ) -> str:
        pass

    @abstractmethod
    def create_refresh_token(
        self,
        user_id: UUID,
        role: str,
        email: Optional[str] = None,
        organization_id: Optional[UUID] = None,
        token_version: int = 0,
    ) -> str:
        pass

    @abstractmethod
    def decode_token(self, token: str) -> TokenPayload:
        pass

    @abstractmethod
    def decode_refresh_token(self, token: str) -> TokenPayload:
        pass

    @abstractmethod
    def verify_token(self, token: str) -> bool:
        pass

    @abstractmethod
    def refresh_token(self, token: str) -> Optional[str]:
        pass

    @abstractmethod
    def is_refresh_token(self, token: str) -> bool:
        pass

    @abstractmethod
    def blacklist_token(self, token: str, expires_in_seconds: int) -> None:
        pass

    @abstractmethod
    def is_token_blacklisted(self, token: str) -> bool:
        pass

    @abstractmethod
    def create_totp_pending_token(self, user_id: UUID) -> str:
        pass

    @abstractmethod
    def verify_totp_pending_token(self, token: str) -> Optional[UUID]:
        pass
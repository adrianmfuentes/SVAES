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


@dataclass
class LoginResult:
    requires_2fa: bool = False
    totp_token: Optional[str] = None
    tokens: Optional[AuthTokens] = None
    user_id: Optional[UUID] = None
    role: Optional[str] = None


@dataclass
class TotpSetupResult:
    totp_uri: str
    secret: str
    qr_data_url: str


class IAuthService(ABC):
    @abstractmethod
    async def authenticate(
        self,
        email: str,
        password: str,
    ) -> LoginResult:
        pass

    @abstractmethod
    async def verify_totp(
        self,
        totp_token: str,
        code: str,
    ) -> LoginResult:
        pass

    @abstractmethod
    async def setup_totp(self, user_id: UUID) -> TotpSetupResult:
        pass

    @abstractmethod
    async def enable_totp(self, user_id: UUID, code: str) -> None:
        pass

    @abstractmethod
    async def disable_totp(self, user_id: UUID, code: str) -> None:
        pass

    @abstractmethod
    async def refresh_access_token(self, refresh_token: str) -> Optional[AuthTokens]:
        pass

    @abstractmethod
    async def logout(self, user_id: UUID, token: str) -> None:
        pass

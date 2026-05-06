from datetime import datetime, timedelta, timezone
from uuid import UUID
import jwt
from jwt.exceptions import InvalidTokenError
from domain.ports.i_token_service import ITokenService

class JwtHandler(ITokenService):
    """HS256 JWT implementation of ITokenService.

    Tokens embed 'sub' (user UUID), 'role', 'iat', and 'exp' claims.
    """

    def __init__(self, secret: str, algorithm: str = "HS256", expire_minutes: int = 60) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._expire_minutes = expire_minutes

    def create_access_token(self, user_id: UUID, role: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),
            "role": role,
            "iat": now,
            "exp": now + timedelta(minutes=self._expire_minutes),
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def decode_token(self, token: str) -> dict:
        """Decodes and validates the JWT signature and expiry.

        Raises:
            jwt.InvalidTokenError: if the token is expired, tampered, or malformed.
        """
        return jwt.decode(token, self._secret, algorithms=[self._algorithm])

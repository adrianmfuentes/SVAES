from datetime import datetime, timedelta, timezone
from uuid import UUID
import jwt
from jwt.exceptions import InvalidTokenError
from domain.ports.i_token_service import ITokenService

class JwtHandler(ITokenService):
    """Implementation of ITokenService using JSON Web Tokens (JWT). 
    This class provides methods to create and decode JWTs for user authentication and authorization.

    Methods:
        create_access_token(user_id: UUID, role: str) -> str: Creates a JWT access token containing the user's ID and role, with an expiration time.
        decode_token(token: str) -> dict: Decodes and validates the JWT, returning the payload if valid or raising an Invalid
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
        return jwt.decode(token, self._secret, algorithms=[self._algorithm])

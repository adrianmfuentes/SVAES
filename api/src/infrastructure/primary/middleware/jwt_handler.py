from datetime import datetime, timedelta, timezone
from typing import Optional, cast, Set
from uuid import UUID
import jwt
from jwt.exceptions import InvalidTokenError
from application.ports.output.i_token_service import ITokenService, TokenPayload

class JwtHandler(ITokenService):
    _blacklisted_tokens: Set[str] = set()

    def __init__(self, secret: str, algorithm: str = "HS256", access_token_expire_minutes: int = 15, refresh_token_expire_days: int = 30, redis_url: Optional[str] = None) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._access_token_expire_minutes = access_token_expire_minutes
        self._refresh_token_expire_days = refresh_token_expire_days
        self._redis = None
        if redis_url:
            import redis as redis_lib
            self._redis = redis_lib.from_url(redis_url, decode_responses=True)


    def create_access_token(
            self,
            user_id: UUID,
            role: str,
            email: Optional[str] = None,
            organization_id: Optional[UUID] = None,
            expires_in: Optional[int] = None
        ) -> str:
        """
        El token se genera a partir de la información del usuario, incluyendo su ID, rol, correo electrónico y organización (si aplica).
        El token también incluye una fecha de emisión y una fecha de expiración calculada a partir del tiempo actual y el tiempo de expiración configurado.
        """
        now = datetime.now(timezone.utc)
        expire_minutes = expires_in if expires_in is not None else self._access_token_expire_minutes

        payload = {
            "sub": str(user_id),
            "role": role,
            "email": email,
            "organization_id": str(organization_id) if organization_id else None,
            "iat": now,
            "exp": now + timedelta(minutes=expire_minutes),
        }

        return jwt.encode(payload, self._secret, algorithm=self._algorithm)


    def create_refresh_token(
            self,
            user_id: UUID,
            role: str,
            email: Optional[str] = None,
            organization_id: Optional[UUID] = None,
        ) -> str:
        """
        Genera un refresh token con expiración de 30 días.
        """
        now = datetime.now(timezone.utc)

        payload = {
            "sub": str(user_id),
            "role": role,
            "email": email,
            "organization_id": str(organization_id) if organization_id else None,
            "iat": now,
            "exp": now + timedelta(days=self._refresh_token_expire_days),
            "type": "refresh",
        }

        return jwt.encode(payload, self._secret, algorithm=self._algorithm)


    def decode_token(self, token: str) -> TokenPayload:
        if self.is_token_blacklisted(token):
            raise ValueError("Token ha sido revocado")
        try:
            decoded = jwt.decode(token, self._secret, algorithms=[self._algorithm])

            return TokenPayload(
                user_id=UUID(decoded["sub"]),
                role=decoded["role"],
                email=str(decoded.get("email")),
                organization_id=UUID(decoded["organization_id"]) if decoded.get("organization_id") else None,
            )

        except InvalidTokenError as e:
            raise ValueError("Token inválido") from e

    def verify_token(self, token: str) -> bool:
        if self.is_token_blacklisted(token):
            return False
        try:
            jwt.decode(token, self._secret, algorithms=[self._algorithm])
            return True
        except InvalidTokenError:
            return False

    def refresh_token(self, token: str) -> Optional[str]:
        try:
            decoded = jwt.decode(token, self._secret, algorithms=[self._algorithm])
            if decoded.get("type") != "refresh":
                return None
            return self.create_access_token(
                user_id=UUID(decoded["sub"]),
                role=decoded["role"],
                email=decoded.get("email"),
                organization_id=UUID(decoded["organization_id"]) if decoded.get("organization_id") else None,
            )
        except InvalidTokenError:
            return None

    def is_refresh_token(self, token: str) -> bool:
        try:
            decoded = jwt.decode(token, self._secret, algorithms=[self._algorithm])
            return decoded.get("type") == "refresh"
        except InvalidTokenError:
            return False

    def blacklist_token(self, token: str, expires_in_seconds: int) -> None:
        if expires_in_seconds <= 0:
            try:
                decoded = jwt.decode(token, self._secret, algorithms=[self._algorithm], options={"verify_exp": False})
                exp = decoded.get("exp")
                if exp:
                    remaining = int(exp - datetime.now(timezone.utc).timestamp())
                    expires_in_seconds = max(1, remaining)
                else:
                    expires_in_seconds = 3600
            except Exception:
                expires_in_seconds = 3600

        if self._redis is not None:
            try:
                self._redis.setex(f"bl:{token}", expires_in_seconds, "1")
                return
            except Exception:
                pass
        self._blacklisted_tokens.add(token)

    def is_token_blacklisted(self, token: str) -> bool:
        if self._redis is not None:
            try:
                return bool(self._redis.exists(f"bl:{token}"))
            except Exception:
                pass
        return token in self._blacklisted_tokens

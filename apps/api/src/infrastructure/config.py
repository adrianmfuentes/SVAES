import logging
from cryptography.fernet import Fernet
from pydantic import model_validator
from pydantic_settings import BaseSettings

_log = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Centralised application settings loaded from environment variables / .env file."""

    # JWT
    jwt_secret_key: str = "insecure-dev-secret-change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # Encryption — generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    encryption_key: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}

    @model_validator(mode="after")
    def _ensure_encryption_key(self) -> "Settings":
        """Auto-generates an ephemeral Fernet key if none is supplied.

        In production, always set ENCRYPTION_KEY — without it, encrypted connector
        credentials are lost on every restart.
        """
        if not self.encryption_key:
            self.encryption_key = Fernet.generate_key().decode()
            _log.warning(
                "ENCRYPTION_KEY not set — using an ephemeral key. "
                "Connector credentials will not survive a server restart."
            )
        return self


settings = Settings()

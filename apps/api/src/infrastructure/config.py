import logging
from cryptography.fernet import Fernet
from pydantic import model_validator
from pydantic_settings import BaseSettings

_log = logging.getLogger(__name__)

"""
This module defines the Settings class, which centralizes application configuration loaded from environment variables or a .env file.

Contains:
    - Settings: A Pydantic model that encapsulates configuration parameters such as JWT settings and encryption key management. 
        It includes validation logic to ensure necessary settings are provided, with defaults for development convenience. 
"""

class Settings(BaseSettings):
    jwt_secret_key: str = "insecure-dev-secret-change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    encryption_key: str = ""
    model_config = {"env_file": ".env", "extra": "ignore"}

    @model_validator(mode="after")
    def _ensure_encryption_key(self) -> "Settings":
        if not self.encryption_key:
            self.encryption_key = Fernet.generate_key().decode()
            _log.warning(
                "ENCRYPTION_KEY not set — using an ephemeral key. "
                "Connector credentials will not survive a server restart."
            )
        return self


settings = Settings()

import logging
from functools import lru_cache

from cryptography.fernet import Fernet
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings

_log = logging.getLogger(__name__)

class Settings(BaseSettings):
    # Database
    database_url: str

    # Auth
    jwt_secret_key: str
    jwt_algorithm: str
    jwt_expire_minutes: int

    # Encryption — None triggers ephemeral key generation (see validator below)
    encryption_key: str | None = None

    # CORS — comma-separated list of allowed origins
    allowed_origins: str

    # Environment
    environment: str

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    # Verification Engine
    engine_url: str = "http://localhost:8080"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v: object) -> str:
        if isinstance(v, str):
            return v.strip()
        return str(v)  # type: ignore[return-value]

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def _ensure_encryption_key(self) -> "Settings":
        if not self.encryption_key:
            self.encryption_key = Fernet.generate_key().decode()
            _log.warning(
                "ENCRYPTION_KEY not set — using an ephemeral key. "
                "Connector credentials will not survive a server restart."
            )
        return self

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]


settings = get_settings()

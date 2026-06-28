import logging
from functools import lru_cache
from pathlib import Path

from cryptography.fernet import Fernet
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings

_ROOT_ENV = str(Path(__file__).resolve().parent.parent.parent.parent / ".env")

_log = logging.getLogger(__name__)


class Settings(BaseSettings):
    # Database
    database_url: str

    # Auth
    jwt_secret_key: str
    jwt_algorithm: str
    jwt_expire_minutes: int

    # API Key pepper (salt for hashing)
    api_key_pepper: str

    # Encryption — None triggers ephemeral key generation (see validator below)
    encryption_key: str | None = None

    # CORS — comma-separated list of allowed origins
    allowed_origins: str

    # Environment
    environment: str

    # Redis
    redis_url: str

    # Celery
    celery_broker_url: str
    celery_result_backend: str

    # Verification Engine
    engine_url: str
    engine_api_key: str

    # Admin bootstrap
    admin_email: str
    admin_password: str

    # SMTP / email
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@svaes.local"
    app_base_url: str = "http://localhost:4200"

    model_config = {"env_file": _ROOT_ENV, "env_file_encoding": "utf-8", "extra": "ignore"}

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
        else:
            try:
                Fernet(self.encryption_key.encode())
            except Exception as exc:
                raise ValueError(
                    f"ENCRYPTION_KEY is not a valid Fernet key (must be 44-char URL-safe base64): {exc}"
                ) from exc
        return self

    @model_validator(mode="after")
    def _reject_unsafe_production_config(self) -> "Settings":
        if not self.is_production:
            return self

        errors: list[str] = []

        _UNSAFE_ADMIN_EMAILS = {"admin@example.com", "admin@svaes.local", "admin@test.local"}
        if self.admin_email.lower() in _UNSAFE_ADMIN_EMAILS:
            errors.append(f"ADMIN_EMAIL is set to a placeholder value ({self.admin_email!r}). Use a real address.")

        if len(self.admin_password) < 16:
            errors.append("ADMIN_PASSWORD must be at least 16 characters in production.")

        _UNSAFE_SMTP = {"localhost", "mailhog", "127.0.0.1", ""}
        if self.smtp_host.lower() in _UNSAFE_SMTP:
            errors.append(f"SMTP_HOST ({self.smtp_host!r}) is not a real SMTP relay. Emails will not be delivered.")

        if not self.smtp_from or self.smtp_from.endswith("@svaes.local"):
            errors.append(f"SMTP_FROM ({self.smtp_from!r}) must be a real sender address.")

        _UNSAFE_ORIGINS = {"http://localhost", "http://localhost:4200", "http://localhost:3000"}
        origins = self.allowed_origins_list
        if not origins or any(o in _UNSAFE_ORIGINS for o in origins):
            errors.append(f"ALLOWED_ORIGINS ({self.allowed_origins!r}) contains localhost — set to the production domain.")

        if self.app_base_url.startswith("http://localhost"):
            errors.append(f"APP_BASE_URL ({self.app_base_url!r}) must be set to the production HTTPS URL.")

        _KNOWN_TEST_KEYS = {"ci-test-secret-key-not-used-in-production"}
        if self.jwt_secret_key in _KNOWN_TEST_KEYS or len(self.jwt_secret_key) < 32:
            errors.append("JWT_SECRET_KEY is too short or is a known test value. Generate a secure random key.")

        if errors:
            bullet_list = "\n  - ".join(errors)
            raise ValueError(
                f"Production boot refused — fix the following configuration errors:\n  - {bullet_list}"
            )

        return self

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]


settings = get_settings()

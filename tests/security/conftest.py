import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Dict, List, Optional
from uuid import UUID, uuid4
import pytest
import pytest_asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
_log = logging.getLogger(__name__)

# Shared test Redis URL
TEST_REDIS_URL = "redis://localhost:6379/0"


def _read_env_password():
    env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    try:
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("POSTGRES_PASSWORD="):
                    return line.split("=", 1)[1]
    except FileNotFoundError:
        pass
    return "svaes"


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
def _test_env():
    postgres_password = os.environ.get("POSTGRES_PASSWORD", _read_env_password())
    os.environ.update({
        "DATABASE_URL": f"postgresql+asyncpg://svaes:{postgres_password}@localhost:5432/svaes_test",
        "ENVIRONMENT": "test",
        "JWT_SECRET_KEY": "security-test-secret-key-not-for-production",
        "JWT_ALGORITHM": "HS256",
        "JWT_EXPIRE_MINUTES": "60",
        "ALLOWED_ORIGINS": "*",
        "ENCRYPTION_KEY": "HnVk8Q2xLm9pR4sT6wYzA1bC3dF5gJ7kN=",
        "REDIS_URL": TEST_REDIS_URL,
        "CELERY_BROKER_URL": TEST_REDIS_URL,
        "CELERY_RESULT_BACKEND": TEST_REDIS_URL,
        "ENGINE_URL": "http://localhost:8081",
        "ENGINE_API_KEY": "test-engine-api-key",
        "ADMIN_EMAIL": "admin@test.local",
        "ADMIN_PASSWORD": "AdminPass1",
    })
    import core.config as _cfg
    _cfg.get_settings.cache_clear()
    _cfg.settings = _cfg.get_settings()
    yield


@pytest_asyncio.fixture(scope="session")
async def _test_db(_test_env):
    from sqlalchemy.ext.asyncio import create_async_engine
    from infrastructure.secondary.database.models import Base

    engine = create_async_engine(os.environ["DATABASE_URL"], echo=False)

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        _db_available = True
    except Exception:
        _log.exception("Schema creation (Base.metadata.create_all) failed")
        _db_available = False

    yield _db_available

    if _db_available:
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
        except Exception:
            _log.exception("Schema teardown (Base.metadata.drop_all) failed")
        try:
            await engine.dispose()
        except Exception:
            _log.exception("Test engine dispose failed")


class InMemoryUserRepository:
    """In-memory user repository used when PostgreSQL is unavailable."""

    def __init__(self) -> None:
        self._by_email: Dict[str, object] = {}
        self._by_id: Dict[UUID, object] = {}
        self._by_activation: Dict[str, object] = {}

    async def create(self, user: object) -> object:
        self._by_email[user.email] = user
        self._by_id[user.id] = user
        if user.activation_token:
            self._by_activation[user.activation_token] = user
        return user

    async def get_by_id(self, user_id: UUID) -> Optional[object]:
        return self._by_id.get(user_id)

    async def get_by_email(self, email: str) -> Optional[object]:
        return self._by_email.get(email)

    async def list_all(
        self,
        organization_id: Optional[UUID] = None,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> List[object]:
        users = list(self._by_email.values())
        if active_only:
            users = [u for u in users if u.is_active]
        return users[skip : skip + limit]

    async def update(self, user: object) -> object:
        self._by_email[user.email] = user
        self._by_id[user.id] = user
        return user

    async def get_by_activation_token(self, token: str) -> Optional[object]:
        return self._by_activation.get(token)

    async def delete(self, user_id: UUID) -> None:
        user = self._by_id.pop(user_id, None)
        if user and user.email in self._by_email:
            del self._by_email[user.email]


@pytest_asyncio.fixture
async def client(_test_db):
    from main import app
    from httpx import AsyncClient, ASGITransport

    @asynccontextmanager
    async def _test_lifespan(app):
        yield

    app.router.lifespan_context = _test_lifespan

    if _test_db:
        from infrastructure.secondary.database.models import Base
        from infrastructure.secondary.database.get_async_session import engine

        try:
            async with engine.begin() as conn:
                for table in reversed(Base.metadata.sorted_tables):
                    await conn.execute(table.delete())
        except Exception:
            pass

    db_overrides = []
    if not _test_db:
        from core.dependencies import get_user_repository

        mock_repo = InMemoryUserRepository()
        app.dependency_overrides[get_user_repository] = lambda: mock_repo
        db_overrides.append(get_user_repository)

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=True),
        base_url="http://test", # NOSONAR
    ) as ac:
        yield ac

    if _test_db:
        from infrastructure.secondary.database.get_async_session import engine
        try:
            await engine.dispose()
        except Exception:
            pass

    for dep in db_overrides:
        app.dependency_overrides.pop(dep, None)


@pytest.fixture
def test_user_id():
    return uuid4()


@pytest.fixture
def auth_token():
    from domain.enums import UserRole
    from infrastructure.primary.middleware.jwt_handler import JwtHandler

    handler = JwtHandler(
        secret=os.environ["JWT_SECRET_KEY"],
        algorithm=os.environ["JWT_ALGORITHM"],
        access_token_expire_minutes=60,
        refresh_token_expire_days=30,
        redis_url=os.environ["REDIS_URL"],
    )
    token = handler.create_access_token(
        user_id=uuid4(),
        email="test@example.com",
        role=UserRole.U3,
        organization_id=uuid4(),
    )
    return token


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def unauth_headers():
    return {"Authorization": "Bearer invalid-token"}


@pytest.fixture
def basic_user_token():
    from domain.enums import UserRole
    from infrastructure.primary.middleware.jwt_handler import JwtHandler

    handler = JwtHandler(
        secret=os.environ["JWT_SECRET_KEY"],
        algorithm=os.environ["JWT_ALGORITHM"],
        access_token_expire_minutes=60,
        refresh_token_expire_days=30,
        redis_url=os.environ["REDIS_URL"],
    )
    token = handler.create_access_token(
        user_id=uuid4(),
        email="basic@example.com",
        role=UserRole.U1,
        organization_id=uuid4(),
    )
    return token


@pytest.fixture
def malicious_payloads():
    return [
        "' OR '1'='1",
        "<script>alert('xss')</script>",
        "'; DROP TABLE users; --",
        "${7*7}",
        "../etc/passwd",
        "__proto__",
        "constructor",
        "{{7*7}}",
    ]

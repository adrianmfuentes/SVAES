import os
import sys
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import pytest
import pytest_asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


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
        "REDIS_URL": "redis://localhost:6379/0",
        "CELERY_BROKER_URL": "redis://localhost:6379/0",
        "CELERY_RESULT_BACKEND": "redis://localhost:6379/0",
        "ENGINE_URL": "http://localhost:8081",
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
        _db_available = False

    yield _db_available

    if _db_available:
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
        except Exception:
            pass
        try:
            await engine.dispose()
        except Exception:
            pass


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

    db_patch = None
    if not _test_db:
        async def _instant_connect_fail(*args, **kwargs):
            raise ConnectionRefusedError("DB not available in test environment")

        db_patch = patch("asyncpg.connect", new=_instant_connect_fail)
        db_patch.start()

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=bool(_test_db)),
        base_url="http://test",
    ) as ac:
        yield ac

    if _test_db:
        from infrastructure.secondary.database.get_async_session import engine
        try:
            await engine.dispose()
        except Exception:
            pass

    if db_patch is not None:
        db_patch.stop()


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

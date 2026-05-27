import os
import sys
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import pytest
import pytest_asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
def _test_env():
    os.environ.update({
        "DATABASE_URL": "postgresql+asyncpg://svaes:svaes@localhost:5432/svaes_test",
        "ENVIRONMENT": "test",
        "JWT_SECRET_KEY": "security-test-secret-key-not-for-production",
        "JWT_ALGORITHM": "HS256",
        "JWT_EXPIRE_MINUTES": "60",
        "ALLOWED_ORIGINS": "*",
        "ENCRYPTION_KEY": "HnVk8Q2xLm9pR4sT6wYzA1bC3dF5gJ7kN=",
        "REDIS_URL": "redis://localhost:6379/0",
    })
    import core.config as _cfg
    _cfg.get_settings.cache_clear()
    _cfg.settings = _cfg.get_settings()
    yield


@pytest_asyncio.fixture(scope="session")
async def _test_db(_test_env):
    from sqlalchemy.ext.asyncio import create_async_engine
    from api.src.infrastructure.secondary.database.models import Base

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
    await engine.dispose()


@pytest_asyncio.fixture
async def client(_test_db):
    from api.src.main import app
    from httpx import AsyncClient, ASGITransport

    @asynccontextmanager
    async def _test_lifespan(app):
        yield

    app.router.lifespan_context = _test_lifespan

    if _test_db:
        from api.src.infrastructure.secondary.database.models import Base
        from api.src.infrastructure.secondary.database.get_async_session import engine

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
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    if db_patch is not None:
        db_patch.stop()


@pytest.fixture
def test_user_id():
    return uuid4()


@pytest.fixture
def auth_token():
    from api.src.domain.enums import UserRole
    from api.src.infrastructure.primary.middleware.jwt_handler import JwtHandler

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
    from api.src.domain.enums import UserRole
    from api.src.infrastructure.primary.middleware.jwt_handler import JwtHandler

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

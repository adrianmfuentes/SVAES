import os
import sys
from contextlib import asynccontextmanager
from uuid import uuid4
import pytest
import pytest_asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api"))

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="session")
def _test_env():
    os.environ.update({
        "DATABASE_URL": "postgresql+asyncpg://svaes:svaes@localhost:5432/svaes_test",
        "ENVIRONMENT": "test",
        "JWT_SECRET_KEY": "integration-test-secret-key-not-for-production",
        "JWT_ALGORITHM": "HS256",
        "JWT_EXPIRE_MINUTES": "60",
        "ALLOWED_ORIGINS": "*",
        "ENCRYPTION_KEY": "HnVk8Q2xLm9pR4sT6wYzA1bC3dF5gJ7kN=",
        "REDIS_URL": "redis://localhost:6379/0",
    })
    yield

@pytest_asyncio.fixture(scope="session")
async def _test_db(_test_env):
    from sqlalchemy.ext.asyncio import create_async_engine
    from api.src.infrastructure.secondary.database.models import Base

    engine = create_async_engine(os.environ["DATABASE_URL"], echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    try:
        await engine.dispose()
    except Exception:
        pass


@pytest_asyncio.fixture
async def client(_test_db):
    from api.src.main import app
    from api.src.infrastructure.secondary.database.models import Base
    from api.src.infrastructure.secondary.database.get_async_session import engine
    from httpx import AsyncClient, ASGITransport

    @asynccontextmanager
    async def _test_lifespan(app):
        yield

    app.router.lifespan_context = _test_lifespan

    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

@pytest.fixture
def test_user_id():
    return uuid4()

@pytest.fixture
def test_org_id():
    return uuid4()

@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-token"}

import logging
import os
import sys
from contextlib import asynccontextmanager
from uuid import uuid4
import pytest
import pytest_asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

pytestmark = pytest.mark.integration
_log = logging.getLogger(__name__)


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
    postgres_user = os.environ.get("TEST_POSTGRES_USER", "svaes")
    postgres_password = os.environ.get("TEST_POSTGRES_PASSWORD", _read_env_password())
    postgres_host = os.environ.get("TEST_POSTGRES_HOST", "localhost")
    postgres_port = os.environ.get("TEST_POSTGRES_PORT", "5432")
    postgres_db = os.environ.get("TEST_POSTGRES_DB", "svaes_test")
    redis_url = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/0")
    engine_url = os.environ.get("TEST_ENGINE_URL", "http://localhost:8081")
    os.environ.update({
        "DATABASE_URL": f"postgresql+asyncpg://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}",
        "ENVIRONMENT": "test",
        "JWT_SECRET_KEY": "integration-test-secret-key-not-for-production",
        "JWT_ALGORITHM": "HS256",
        "JWT_EXPIRE_MINUTES": "60",
        "ALLOWED_ORIGINS": "*",
        "ENCRYPTION_KEY": "HnVk8Q2xLm9pR4sT6wYzA1bC3dF5gJ7kN=",
        "REDIS_URL": redis_url,
        "CELERY_BROKER_URL": redis_url,
        "CELERY_RESULT_BACKEND": redis_url,
        "ENGINE_URL": engine_url,
    })
    import core.config as _cfg
    _cfg.get_settings.cache_clear()
    _cfg.settings = _cfg.get_settings()
    yield


@pytest_asyncio.fixture(scope="session")
async def _test_db(_test_env):
    from sqlalchemy.ext.asyncio import create_async_engine
    from infrastructure.secondary.database.models import Base

    test_engine = create_async_engine(os.environ["DATABASE_URL"], echo=False)

    try:
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        _db_available = True
    except Exception:
        _log.exception("Schema creation (Base.metadata.create_all) failed")
        _db_available = False

    yield _db_available

    if _db_available:
        try:
            async with test_engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
        except Exception:
            _log.exception("Schema teardown (Base.metadata.drop_all) failed")
        try:
            await test_engine.dispose()
        except Exception:
            _log.exception("Test engine dispose failed")


@pytest_asyncio.fixture
async def client(_test_db):
    if not _test_db:
        pytest.skip("PostgreSQL test database not available — start PostgreSQL and create 'svaes_test' database")

    from main import app
    from infrastructure.secondary.database.models import Base
    from infrastructure.secondary.database.get_async_session import engine
    from httpx import AsyncClient, ASGITransport

    @asynccontextmanager
    async def _test_lifespan(app):
        yield

    app.router.lifespan_context = _test_lifespan

    app.state.limiter.reset()

    try:
        async with engine.begin() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                await conn.execute(table.delete())
    except Exception:
        pass

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test", # NOSONAR
    ) as ac:
        yield ac

    try:
        await engine.dispose()
    except Exception:
        pass


@pytest_asyncio.fixture
async def db(_test_db):
    if not _test_db:
        pytest.skip("PostgreSQL test database not available — start PostgreSQL and create 'svaes_test' database")
    yield


# ---------------------------------------------------------------------------
# Token fixtures
# ---------------------------------------------------------------------------

def _make_token(user_id, email, role, organization_id=None):
    from domain.enums import UserRole
    from infrastructure.primary.middleware.jwt_handler import JwtHandler

    handler = JwtHandler(
        secret=os.environ["JWT_SECRET_KEY"],
        algorithm=os.environ["JWT_ALGORITHM"],
        access_token_expire_minutes=60,
        refresh_token_expire_days=30,
        redis_url=os.environ.get("REDIS_URL"),
    )
    return handler.create_access_token(
        user_id=user_id,
        email=email,
        role=role.value if isinstance(role, UserRole) else role,
        organization_id=organization_id,
    )


@pytest.fixture
def test_user_id():
    return uuid4()


@pytest.fixture
def test_org_id():
    return uuid4()


@pytest.fixture
def admin_token(test_user_id, test_org_id):
    from domain.enums import UserRole
    return _make_token(test_user_id, "admin@integration.test", UserRole.U3, test_org_id)


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def manager_token(test_user_id, test_org_id):
    from domain.enums import UserRole
    return _make_token(test_user_id, "manager@integration.test", UserRole.U4, test_org_id)


@pytest.fixture
def manager_headers(manager_token):
    return {"Authorization": f"Bearer {manager_token}"}


@pytest.fixture
def operator_token(test_user_id, test_org_id):
    from domain.enums import UserRole
    return _make_token(test_user_id, "operator@integration.test", UserRole.U2, test_org_id)


@pytest.fixture
def operator_headers(operator_token):
    return {"Authorization": f"Bearer {operator_token}"}


@pytest.fixture
def viewer_token(test_user_id, test_org_id):
    from domain.enums import UserRole
    return _make_token(test_user_id, "viewer@integration.test", UserRole.U1, test_org_id)


@pytest.fixture
def viewer_headers(viewer_token):
    return {"Authorization": f"Bearer {viewer_token}"}


@pytest.fixture
def auth_headers(admin_headers):
    return admin_headers

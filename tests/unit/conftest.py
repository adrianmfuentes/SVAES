import os
import sys
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

REDIS_URL = "redis://localhost:6379/0"

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET_KEY", "base-choice-test-secret-key-32-ch!")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXPIRE_MINUTES", "60")
os.environ.setdefault("ALLOWED_ORIGINS", "*")
os.environ.setdefault("ENCRYPTION_KEY", "dMs9Bu4qV9bunZU511boUnNpC0jYXubAfB8a5VPynsE=")
os.environ.setdefault("REDIS_URL", REDIS_URL)
os.environ.setdefault("CELERY_BROKER_URL", REDIS_URL)
os.environ.setdefault("CELERY_RESULT_BACKEND", REDIS_URL)
os.environ.setdefault("ENGINE_URL", "http://localhost:8081")
os.environ.setdefault("ENGINE_API_KEY", "test-engine-api-key")
os.environ.setdefault("ADMIN_EMAIL", "admin@test.local")
os.environ.setdefault("ADMIN_PASSWORD", "test-admin-password")
os.environ.setdefault("API_KEY_PEPPER", "test-api-key-pepper")


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "api", "src"))


def pytest_configure(config):
    import sqlalchemy.ext.asyncio

    mock_engine = MagicMock()
    mock_connection = MagicMock()
    mock_result = MagicMock()
    mock_result._is_cursor = False
    mock_result.raw = None
    mock_connection.execute = MagicMock(return_value=mock_result)
    mock_connection.__enter__ = MagicMock(return_value=mock_connection)
    mock_connection.__exit__ = MagicMock(return_value=None)
    mock_engine.sync_engine = MagicMock()
    mock_engine.sync_engine.dialect = MagicMock()
    mock_engine.sync_engine.dialect.is_async = True
    mock_engine.sync_engine.connect = MagicMock(return_value=mock_connection)
    mock_engine.begin = MagicMock(return_value=MagicMock())

    sqlalchemy.ext.asyncio.create_async_engine = lambda *args, **kwargs: mock_engine


@pytest.fixture(autouse=True)
def _mock_sql_user_active(request):
    """Patch SqlUserRepository.get_by_id to return an active user.

    get_current_user instantiates SqlUserRepository directly and checks is_active.
    Without this patch every JWT-authenticated test gets 401 because no real DB row exists.
    Skipped for test_repositories.py which tests the method itself.
    """
    if request.node.fspath.basename == "test_repositories.py":
        yield
        return
    mock_user = MagicMock()
    mock_user.is_active = True
    mock_user.token_version = 0
    with patch(
        "infrastructure.secondary.database.repositories.user_repository.SqlUserRepository.get_by_id",
        new=AsyncMock(return_value=mock_user),
    ):
        yield

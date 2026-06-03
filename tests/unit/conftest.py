import os
import sys
from unittest.mock import MagicMock

REDIS_URL = "redis://localhost:6379/0"

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET_KEY", "base-choice-test-secret-key-32-ch!")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXPIRE_MINUTES", "60")
os.environ.setdefault("ALLOWED_ORIGINS", "*")
os.environ.setdefault("ENCRYPTION_KEY", "HnVk8Q2xLm9pR4sT6wYzA1bC3dF5gJ7kN=")
os.environ.setdefault("REDIS_URL", REDIS_URL)
os.environ.setdefault("CELERY_BROKER_URL", REDIS_URL)
os.environ.setdefault("CELERY_RESULT_BACKEND", REDIS_URL)
os.environ.setdefault("ENGINE_URL", "http://localhost:8081")


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "api", "src"))


def pytest_configure(config):
    import sqlalchemy.ext.asyncio

    mock_engine = MagicMock()
    mock_engine.sync_engine = MagicMock()
    mock_engine.sync_engine.dialect = MagicMock()
    mock_engine.sync_engine.dialect.is_async = True
    mock_engine.begin = MagicMock()

    sqlalchemy.ext.asyncio.create_async_engine = lambda *args, **kwargs: mock_engine

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "api"))

pytestmark = pytest.mark.unit

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/db")


_create_async_engine_patcher = None


def pytest_configure():
    global _create_async_engine_patcher
    _create_async_engine_patcher = patch(
        "sqlalchemy.ext.asyncio.create_async_engine", return_value=MagicMock()
    )
    _create_async_engine_patcher.start()


def pytest_unconfigure():
    global _create_async_engine_patcher
    if _create_async_engine_patcher is not None:
        _create_async_engine_patcher.stop()
        _create_async_engine_patcher = None


@pytest.fixture
def mock_model():
    def _make_mock():
        model = MagicMock()
        model.__class__ = MagicMock()
        return model
    return _make_mock


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    session.get = AsyncMock(return_value=None)
    return session


def _mock_async_session_local(mock_session):
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_session)
    ctx.__aexit__ = AsyncMock(return_value=None)
    return ctx


@pytest.fixture
def mock_async_session(mock_session):
    with patch(
        "infrastructure.secondary.database.get_async_session.AsyncSessionLocal",
        return_value=_mock_async_session_local(mock_session),
    ):
        yield mock_session


def _scope_gen(mock_session):
    async def _scope():
        yield mock_session
    return _scope()


@pytest.fixture
def mock_session_scope(mock_session):
    with patch(
        "infrastructure.secondary.database.repositories.base_sql_repository._session_scope",
        return_value=_scope_gen(mock_session),
    ):
        yield mock_session

"""
Integration test fixtures.

These tests require a real PostgreSQL database and optionally Redis.
Set TEST_DATABASE_URL in your environment (defaults to a local test DB).

Run with:
    cd apps/api
    TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/svaes_test \
    uv run pytest ../../tests/api/integration -v
"""
import asyncio
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from infrastructure.database.base import Base
import infrastructure.database.models  # ensure all models are registered

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/svaes_test",
)

_engine = create_async_engine(TEST_DB_URL, echo=False, future=True)
_SessionFactory = async_sessionmaker(_engine, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _setup_db():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with _SessionFactory() as session:
        async with session.begin():
            yield session
            await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """FastAPI test client with DB session overridden to use the test transaction."""
    from main import app
    from api.dependencies import get_current_user
    from infrastructure.database.session import get_db_session
    from domain.entities.user import User
    from domain.entities.enums import UserRole
    import uuid
    from datetime import datetime, timezone

    _admin = User(
        id=uuid.uuid4(),
        email="admin@test.local",
        hashed_password="$2b$12$unused",
        role=UserRole.ADMIN,
        organization_id=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    async def _override_session():
        yield db_session

    app.dependency_overrides[get_db_session] = _override_session
    app.dependency_overrides[get_current_user] = lambda: _admin

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()

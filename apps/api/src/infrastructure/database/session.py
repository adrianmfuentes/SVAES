import os
from contextvars import ContextVar
from uuid import UUID
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

_current_org_id_var: ContextVar[UUID | None] = ContextVar("current_org_id", default=None)

_engine = None
_AsyncSessionLocal = None

def set_current_organization_id(org_id: UUID | None) -> None:
    _current_org_id_var.set(org_id)

def get_current_organization_id() -> UUID | None:
    return _current_org_id_var.get()

def _get_engine():
    global _engine, _AsyncSessionLocal
    # Ensure both engine and sessionmaker are initialized. It's possible the
    # engine exists but the sessionmaker was not created, so check both.
    if _engine is None or _AsyncSessionLocal is None:
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL not set in environment.")

        environment = os.environ.get("ENVIRONMENT", "development").lower()
        pool_size = 5 if environment == "production" else 2
        max_overflow = 10 if environment == "production" else 2

        _engine = create_async_engine(
            database_url,
            echo=False,
            future=True,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        _AsyncSessionLocal = async_sessionmaker(
            _engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _AsyncSessionLocal


async def get_db_session():
    """FastAPI dependency that provides a transactional AsyncSession.

    On transaction start the session executes ``SET LOCAL app.current_organization_id``
    so that RLS policies see the correct tenant context for every query inside the
    request. ``SET LOCAL`` only affects the current transaction and is rolled back
    automatically, so this is safe for connection pooling.
    """
    session_factory = _get_engine()
    async with session_factory() as session:
        async with session.begin():
            org_id = _current_org_id_var.get()
            if org_id is not None:
                await session.execute(
                    text("SET LOCAL app.current_organization_id = :org_id"),
                    {"org_id": str(org_id)},
                )
            yield session

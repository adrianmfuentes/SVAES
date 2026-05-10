import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from dotenv import load_dotenv

load_dotenv()
_engine = None
_AsyncSessionLocal = None

def _get_engine():
    global _engine, _AsyncSessionLocal
    # Ensure both engine and sessionmaker are initialized. It's possible the
    # engine exists but the sessionmaker was not created (e.g. after reloads),
    # so check both.
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
    """FastAPI dependency that provides a transactional AsyncSession."""
    session_factory = _get_engine()
    async with session_factory() as session:
        async with session.begin():
            yield session

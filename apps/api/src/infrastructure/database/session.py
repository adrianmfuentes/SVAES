import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from dotenv import load_dotenv

load_dotenv()

_engine = None
_AsyncSessionLocal = None


def _get_engine():
    global _engine, _AsyncSessionLocal
    if _engine is None:
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL no configurada en el entorno.")
        _engine = create_async_engine(database_url, echo=False, future=True)
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

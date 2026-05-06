import os
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL no configurada en el entorno.")

engine = create_async_engine(DATABASE_URL, echo=False, future=True)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session():
    """FastAPI dependency that provides a transactional AsyncSession.

    Opens a transaction on entry and automatically commits on clean exit
    or rolls back if an exception propagates — guaranteeing atomicity per request.
    """
    async with AsyncSessionLocal() as session:
        async with session.begin():
            yield session

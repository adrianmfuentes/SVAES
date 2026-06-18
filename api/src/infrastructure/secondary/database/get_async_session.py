from pathlib import Path
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
import dotenv
import os

dotenv.load_dotenv(str(Path(__file__).resolve().parents[5] / ".env"))
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL is None:
    raise ValueError("DATABASE_URL is not set")  # pragma: no cover — guard clause a nivel módulo, no testeable sin manipular env antes del import

# Crear el motor asíncrono
_sql_echo = os.getenv("ENVIRONMENT", "production") == "development"
engine = create_async_engine(DATABASE_URL, echo=_sql_echo, pool_pre_ping=True)

# Crear un sessionmaker asíncrono
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
        

    
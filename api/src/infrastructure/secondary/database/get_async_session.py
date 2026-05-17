from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
import dotenv
import os

"""
Este módulo define una función para obtener una sesión asíncrona de la base de datos utilizando SQLAlchemy. 
La función `get_async_session` es un generador que crea una nueva sesión, la cede al contexto del consumidor y luego se asegura de cerrarla después de su uso. 
"""

dotenv.load_dotenv()

possible_env_paths = [
    ".env",
    os.path.join(os.path.dirname(__file__), ".env"),
    os.path.join(os.path.dirname(__file__), "..", "..", ".env"),
    os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"),
]
for env_path in possible_env_paths:
    if os.path.exists(env_path):
        dotenv.load_dotenv(env_path)
        break
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL is None:
    raise ValueError("DATABASE_URL is not set")

# Crear el motor asíncrono
_sql_echo = os.getenv("ENVIRONMENT", "production") == "development"
engine = create_async_engine(DATABASE_URL, echo=_sql_echo)

# Crear un sessionmaker asíncrono
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session # yield permite que el consumidor use la sesión y luego se asegura de cerrarla después de su uso.
        

    
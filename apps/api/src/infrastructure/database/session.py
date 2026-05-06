import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from dotenv import load_dotenv

load_dotenv()
# Para async, el driver debe ser asyncpg, ej: postgresql+asyncpg://user:pass@localhost:5432/db
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL no configurada en el entorno.")

# Creamos el motor asíncrono
engine = create_async_engine(
    DATABASE_URL,
    echo=False, # True si quieres ver el SQL en la terminal
    future=True
)

# Creamos la factoría de sesiones
AsyncSessionLocal = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

async def get_db_session():
    """
    Dependencia para FastAPI que inyecta la sesión de base de datos.
    Garantiza que la conexión se cierra después de cada petición.
    """
    async with AsyncSessionLocal() as session:
        yield session
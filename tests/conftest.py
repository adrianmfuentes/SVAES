import pytest
from typing import AsyncGenerator, Any
from uuid import UUID, uuid4
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from api.src.main import app
from api.src.domain.entities.user import User
from api.src.domain.enums import UserRole
from api.src.application.ports.output.i_user_repository import IUserRepository
from api.src.application.ports.output.i_token_service import ITokenService, TokenPayload
from api.src.application.ports.output.i_password_hasher import IPasswordHasher
from api.src.core.config import settings

"""
Fichero de configuración de pytest para pruebas unitarias, de integración, rendimiento y aceptación. Define fixtures (una fixture es un objeto 
que se puede usar en varias pruebas) comunes para la creación de usuarios, repositorios, servicios y clientes HTTP asíncronos. También configura 
marcadores personalizados para categorizar las pruebas.
"""

def pytest_configure(config):
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "performance: marks tests as performance tests")
    config.addinivalue_line("markers", "acceptance: marks tests as acceptance tests")


@pytest.fixture
def anyio_backend(): # Fix para pytest-anyio, indica que se usará el backend asyncio para las pruebas asíncronas
    return "asyncio"


@pytest.fixture
def user_entity() -> User: # Fixture que crea una instancia de User con datos de prueba
    return User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYUVe7kR7uau", # NOSONAR: Hardcoded hashed password for testing
        display_name="Test User",
        role=UserRole.U1,
        is_active=True,
        failed_login_attempts=0,
        locked_until=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        organization_ids=[],
    )


@pytest.fixture
def mock_user_repository(user_entity: User) -> AsyncMock:
    repo = AsyncMock(spec=IUserRepository)
    repo.get_by_email = AsyncMock(return_value=user_entity)
    repo.get_by_id = AsyncMock(return_value=user_entity)
    repo.update = AsyncMock(return_value=user_entity)
    repo.create = AsyncMock(return_value=user_entity)
    return repo


@pytest.fixture
def mock_token_service() -> AsyncMock:
    service = AsyncMock(spec=ITokenService)
    service.create_access_token = MagicMock(return_value="fake.jwt.token")
    service.decode_token = MagicMock(return_value=TokenPayload(
        user_id=uuid4(),
        role=UserRole.U1,
        email="test@example.com",
        organization_id=None,
        exp=9999999999,
    ))
    return service


@pytest.fixture
def mock_password_hasher() -> AsyncMock:
    hasher = AsyncMock(spec=IPasswordHasher)
    hasher.verify_password = MagicMock(return_value=True)
    hasher.hash_password = MagicMock(return_value="$2b$12$hashed")
    return hasher


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def auth_headers(user_entity: User, mock_token_service: AsyncMock) -> dict[str, str]:
    return {"Authorization": f"Bearer {mock_token_service.create_access_token()}"}


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(settings.database_url, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    async_session = async_sessionmaker(db_engine, expire_on_commit=False)
    async with async_session() as session:
        yield session
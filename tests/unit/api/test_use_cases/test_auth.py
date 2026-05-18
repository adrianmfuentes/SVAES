import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timezone
from application.use_cases.main.auth_service import AuthService
from application.ports.input.i_auth_service import AuthTokens
from application.ports.output.i_user_repository import IUserRepository
from application.ports.output.i_token_service import ITokenService, TokenPayload
from application.ports.output.i_password_hasher import IPasswordHasher
from domain.entities.user import User
from domain.enums import UserRole
from domain.exceptions import ValidationError

"""
Clase de pruebas unitarias para AuthService, enfocándose en la autenticación y renovación de tokens. Se utilizan fixtures para configurar el entorno 
de pruebas, incluyendo un usuario de prueba, repositorio de usuarios simulado, servicio de tokens simulado y hasher de contraseñas simulado.

Casos testeados:
    - Autenticación exitosa con credenciales válidas.
    - Error al autenticar con un email no registrado.
    - Error al autenticar con un usuario inactivo.
    - Error al autenticar con una contraseña incorrecta.
    - Renovación de token exitosa con un token de refresco válido.
    - Retorno de None al intentar renovar con un token de refresco inválido.
"""
class TestAuthService:

    @pytest.fixture
    def user_entity(self) -> User:
        return User(
            id=uuid4(),
            email="test@example.com",
            hashed_password="$2b$12$hashedpasswordhash", # NOSONAR: Hardcoded hashed password for testing
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
    def mock_user_repository(self, user_entity: User) -> AsyncMock:
        repo = AsyncMock(spec=IUserRepository)
        repo.get_by_email = AsyncMock(return_value=user_entity)
        repo.get_by_id = AsyncMock(return_value=user_entity)
        repo.update = AsyncMock(return_value=user_entity)
        return repo

    @pytest.fixture
    def mock_token_service(self, user_entity: User) -> AsyncMock:
        service = AsyncMock(spec=ITokenService)
        service.create_access_token = MagicMock(return_value="access.token.here")
        service.create_refresh_token = MagicMock(return_value="access.token.here")
        service.is_refresh_token = MagicMock(return_value=True)
        service.decode_token = MagicMock(return_value=TokenPayload(
            user_id=user_entity.id,
            role=user_entity.role,
            email=user_entity.email,
            organization_id=None,
            exp=9999999999,
        ))
        return service

    @pytest.fixture
    def mock_password_hasher(self) -> AsyncMock:
        hasher = AsyncMock(spec=IPasswordHasher)
        hasher.verify_password = MagicMock(return_value=True)
        return hasher

    @pytest.fixture
    def auth_service(
        self,
        mock_user_repository: AsyncMock,
        mock_token_service: AsyncMock,
        mock_password_hasher: AsyncMock,
    ) -> AuthService:
        return AuthService(
            user_repository=mock_user_repository,
            token_service=mock_token_service,
            password_hasher=mock_password_hasher,
        )

    @pytest.mark.asyncio
    async def test_authenticate_returns_tokens_on_valid_credentials(
        self,
        auth_service: AuthService,
        mock_user_repository: AsyncMock,
        mock_token_service: AsyncMock,
        user_entity: User,
    ):
        tokens, user_id, role = await auth_service.authenticate(
            "test@example.com", "password123" # NOSONAR: Hardcoded password for testing
        )

        assert tokens.access_token == "access.token.here"
        assert tokens.refresh_token == "access.token.here"
        assert user_id == user_entity.id
        assert role == UserRole.U1
        mock_user_repository.get_by_email.assert_called_once_with("test@example.com")

    @pytest.mark.asyncio
    async def test_authenticate_raises_on_invalid_email(
        self,
        auth_service: AuthService,
        mock_user_repository: AsyncMock,
    ):
        mock_user_repository.get_by_email = AsyncMock(return_value=None)

        with pytest.raises(ValidationError, match="Credenciales inválidas"):
            await auth_service.authenticate("wrong@example.com", "password123") # NOSONAR: Hardcoded password for testing

    @pytest.mark.asyncio
    async def test_authenticate_raises_on_inactive_user(
        self,
        auth_service: AuthService,
        mock_user_repository: AsyncMock,
        user_entity: User,
    ):
        user_entity.is_active = False
        mock_user_repository.get_by_email = AsyncMock(return_value=user_entity)

        with pytest.raises(ValidationError, match="Usuario inactivo"):
            await auth_service.authenticate("test@example.com", "password123") # NOSONAR: Hardcoded password for testing

    @pytest.mark.asyncio
    async def test_authenticate_raises_on_wrong_password(
        self,
        auth_service: AuthService,
        mock_password_hasher: AsyncMock,
    ):
        mock_password_hasher.verify_password = MagicMock(return_value=False)

        with pytest.raises(ValidationError, match="Credenciales inválidas"):
            await auth_service.authenticate("test@example.com", "wrongpassword") # NOSONAR: Hardcoded password for testing

    @pytest.mark.asyncio
    async def test_refresh_access_token_returns_new_tokens(
        self,
        auth_service: AuthService,
        mock_token_service: AsyncMock,
        user_entity: User,
    ):
        result = await auth_service.refresh_access_token("some.refresh.token")

        assert result is not None
        assert result.access_token == "access.token.here"
        assert result.refresh_token == "access.token.here"
        mock_token_service.decode_token.assert_called_once_with("some.refresh.token")

    @pytest.mark.asyncio
    async def test_refresh_access_token_returns_none_on_invalid_token(
        self,
        auth_service: AuthService,
        mock_token_service: AsyncMock,
    ):
        mock_token_service.decode_token = MagicMock(side_effect=ValueError("Invalid token"))

        result = await auth_service.refresh_access_token("bad.token")

        assert result is None
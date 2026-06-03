import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timedelta, timezone

from application.use_cases.main.auth_service import AuthService
from application.ports.input.i_auth_service import AuthTokens, LoginResult
from domain.entities.user import User
from domain.enums import UserRole
from domain.exceptions import ValidationError

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_audit_logger():
    logger = MagicMock()
    logger.log = MagicMock()
    return logger


@pytest.fixture
def user_repo():
    repo = AsyncMock()
    repo.get_by_email = AsyncMock(return_value=None)
    repo.get_by_id = AsyncMock(return_value=None)
    repo.update = AsyncMock()
    return repo


@pytest.fixture
def token_service():
    svc = MagicMock()
    svc.create_access_token = MagicMock(return_value="access-token")
    svc.create_refresh_token = MagicMock(return_value="refresh-token")
    svc.is_refresh_token = MagicMock(return_value=False)
    svc.decode_token = MagicMock()
    svc.blacklist_token = MagicMock()
    return svc


@pytest.fixture
def password_hasher():
    hasher = MagicMock()
    hasher.verify_password = MagicMock(return_value=True)
    return hasher


@pytest.fixture
def service(user_repo, token_service, password_hasher, mock_audit_logger):
    with patch(
        "application.use_cases.main.auth_service.get_audit_logger",
        return_value=mock_audit_logger,
    ):
        yield AuthService(user_repo, token_service, password_hasher)


@pytest.fixture
def sample_user():
    return User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed-password",
        display_name="Test User",
        role=UserRole.U2,
        is_active=True,
        failed_login_attempts=0,
        locked_until=None,
        organization_ids=[uuid4()],
    )


class TestAuthenticateSuccess:
    async def test_returns_tokens_and_user_info(self, service, user_repo, sample_user):
        """Verifica la autenticación exitosa y retorno de tokens."""
        user_repo.get_by_email.return_value = sample_user

        result = await service.authenticate("test@example.com", "password")

        assert isinstance(result, LoginResult)
        assert result.tokens is not None
        assert result.tokens.access_token == "access-token"
        assert result.tokens.refresh_token == "refresh-token"
        assert result.tokens.token_type == "bearer"
        assert result.user_id == sample_user.id
        assert result.role == UserRole.U2.value

    async def test_authenticate_resets_failed_attempts(self, service, user_repo, sample_user):
        """Verifica que se reseteen los intentos fallidos tras un login exitoso."""
        sample_user.failed_login_attempts = 3
        user_repo.get_by_email.return_value = sample_user

        await service.authenticate("test@example.com", "password")

        assert sample_user.failed_login_attempts == 0
        assert sample_user.locked_until is None
        assert user_repo.update.called

    async def test_authenticate_with_existing_lockout(self, service, user_repo, sample_user):
        """Verifica que un usuario bloqueado no pueda autenticarse."""
        sample_user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=5)
        user_repo.get_by_email.return_value = sample_user

        with pytest.raises(ValidationError, match="Cuenta bloqueada"):
            await service.authenticate("test@example.com", "password")


class TestAuthenticateFailure:
    async def test_user_not_found(self, service, user_repo):
        """Verifica que se lance ValidationError cuando el usuario no existe."""
        user_repo.get_by_email.return_value = None

        with pytest.raises(ValidationError, match="Credenciales inválidas"):
            await service.authenticate("unknown@test.com", "password")

    async def test_user_inactive(self, service, user_repo, sample_user):
        """Verifica que se lance ValidationError cuando el usuario está inactivo."""
        sample_user.is_active = False
        user_repo.get_by_email.return_value = sample_user

        with pytest.raises(ValidationError, match="Usuario inactivo"):
            await service.authenticate("test@example.com", "password")

    async def test_wrong_password(self, service, user_repo, password_hasher, sample_user):
        """Verifica que se incremente el contador de intentos fallidos."""
        password_hasher.verify_password.return_value = False
        user_repo.get_by_email.return_value = sample_user

        with pytest.raises(ValidationError, match="Credenciales inválidas"):
            await service.authenticate("test@example.com", "wrong-password")

        assert sample_user.failed_login_attempts == 1
        user_repo.update.assert_called()

    async def test_wrong_password_shows_remaining_attempts(self, service, user_repo, password_hasher, sample_user):
        """Verifica que el mensaje muestre intentos restantes."""
        password_hasher.verify_password.return_value = False
        sample_user.failed_login_attempts = 2
        user_repo.get_by_email.return_value = sample_user

        with pytest.raises(ValidationError, match="Intentos restantes: 2"):
            await service.authenticate("test@example.com", "wrong-password")

    async def test_max_failed_attempts_locks_account(self, service, user_repo, password_hasher, sample_user):
        """Verifica que se bloquee la cuenta tras superar el máximo de intentos."""
        password_hasher.verify_password.return_value = False
        sample_user.failed_login_attempts = 5
        user_repo.get_by_email.return_value = sample_user

        with pytest.raises(ValidationError, match="Demasiados intentos"):
            await service.authenticate("test@example.com", "password")

        assert sample_user.locked_until is not None
        assert sample_user.failed_login_attempts == 0

    async def test_locked_account_shows_remaining_time(self, service, user_repo, sample_user):
        """Verifica que se muestre el tiempo restante de bloqueo."""
        sample_user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=10)
        sample_user.failed_login_attempts = 0
        user_repo.get_by_email.return_value = sample_user

        with pytest.raises(ValidationError, match="Cuenta bloqueada"):
            await service.authenticate("test@example.com", "password")

    async def test_max_failed_attempts_at_boundary(self, service, user_repo, password_hasher, sample_user):
        """Verifica el bloqueo al alcanzar exactamente MAX_LOGIN_ATTEMPTS después de fallo."""
        password_hasher.verify_password.return_value = False
        sample_user.failed_login_attempts = 4
        user_repo.get_by_email.return_value = sample_user

        with pytest.raises(ValidationError, match="Credenciales inválidas"):
            await service.authenticate("test@example.com", "password")

        assert sample_user.failed_login_attempts == 5


class TestRefreshToken:
    async def test_refresh_success(self, service, user_repo, token_service):
        """Verifica el refresco exitoso de tokens."""
        from application.ports.output.i_token_service import TokenPayload
        token_service.is_refresh_token.return_value = True
        user_id = uuid4()
        token_service.decode_token.return_value = TokenPayload(
            user_id=user_id,
            role=UserRole.U2,
            email="test@example.com",
            organization_id=None,
            exp=0,
        )
        sample_user = User(
            id=user_id,
            email="test@example.com",
            hashed_password="hashed", # NOSONAR
            display_name="Test",
            role=UserRole.U2,
            organization_ids=[uuid4()],
        )
        user_repo.get_by_id.return_value = sample_user

        result = await service.refresh_access_token("refresh-token-123")

        assert isinstance(result, AuthTokens)
        assert result.access_token == "access-token"
        assert result.refresh_token == "refresh-token"
        token_service.create_access_token.assert_called_once()
        token_service.create_refresh_token.assert_called_once()

    async def test_refresh_not_a_refresh_token(self, service, token_service):
        """Verifica que se retorne None si el token no es de refresco."""
        token_service.is_refresh_token.return_value = False

        result = await service.refresh_access_token("some-token")

        assert result is None

    async def test_refresh_decode_error(self, service, token_service):
        """Verifica que se retorne None si falla el decode."""
        token_service.is_refresh_token.return_value = True
        token_service.decode_token.side_effect = ValueError("invalid")

        result = await service.refresh_access_token("bad-token")

        assert result is None

    async def test_refresh_user_not_found(self, service, user_repo, token_service):
        """Verifica que se retorne None si el usuario no existe."""
        from application.ports.output.i_token_service import TokenPayload
        token_service.is_refresh_token.return_value = True
        token_service.decode_token.return_value = TokenPayload(
            user_id=uuid4(),
            role=UserRole.U2,
            email="test@example.com",
            organization_id=None,
            exp=0,
        )
        user_repo.get_by_id.return_value = None

        result = await service.refresh_access_token("refresh-token")

        assert result is None


class TestLogout:
    async def test_logout_blacklists_token(self, service, token_service):
        """Verifica que se blacklistee el token y se registre auditoría."""
        user_id = uuid4()

        await service.logout(user_id, "token-to-blacklist")

        token_service.blacklist_token.assert_called_once_with("token-to-blacklist", 0)

    async def test_logout_audit_logged(self, service, token_service, mock_audit_logger):
        """Verifica que se registre la auditoría de logout."""
        user_id = uuid4()

        await service.logout(user_id, "token-123")

        assert mock_audit_logger.log.called
        call_args = mock_audit_logger.log.call_args[0][0]
        assert call_args.resource_type == "user"
        assert call_args.resource_id == user_id

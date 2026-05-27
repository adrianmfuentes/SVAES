import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from application.use_cases.others.authenticate_user import (
    AuthenticateUserUseCase,
    AuthResult,
)
from domain.enums import UserRole

pytestmark = pytest.mark.unit


@pytest.fixture
def user_repo():
    repo = AsyncMock()
    repo.get_by_email = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def token_service():
    svc = MagicMock()
    svc.create_access_token = MagicMock(return_value="mock-token")
    return svc


@pytest.fixture
def password_hasher():
    hasher = MagicMock()
    hasher.verify_password = MagicMock(return_value=True)
    return hasher


@pytest.fixture
def use_case(user_repo, token_service, password_hasher):
    return AuthenticateUserUseCase(user_repo, token_service, password_hasher)


@pytest.fixture
def sample_user():
    user = MagicMock()
    user.id = uuid4()
    user.email = "test@example.com"
    user.hashed_password = "hashed-password"
    user.is_active = True
    user.role = UserRole.U1
    user.organization_id = uuid4()
    return user


class TestAuthenticateSuccess:
    async def test_returns_auth_result(self, use_case, user_repo, sample_user):
        user_repo.get_by_email.return_value = sample_user

        result = await use_case.execute("test@example.com", "password")

        assert isinstance(result, AuthResult)
        assert result.access_token == "mock-token"
        assert result.refresh_token == "mock-token"
        assert result.user_id == sample_user.id
        assert result.role == UserRole.U1
        assert result.token_type == "bearer"

    async def test_queries_user_by_email(self, use_case, user_repo, sample_user):
        user_repo.get_by_email.return_value = sample_user

        await use_case.execute("test@example.com", "password")

        user_repo.get_by_email.assert_called_once_with("test@example.com")

    async def test_verifies_password(self, use_case, user_repo, password_hasher, sample_user):
        user_repo.get_by_email.return_value = sample_user

        await use_case.execute("test@example.com", "secret123")

        password_hasher.verify_password.assert_called_once_with(
            "secret123", sample_user.hashed_password
        )

    async def test_creates_access_token_short_expiry(self, use_case, user_repo, token_service, sample_user):
        user_repo.get_by_email.return_value = sample_user

        await use_case.execute("test@example.com", "secret123")

        token_service.create_access_token.assert_any_call(
            user_id=sample_user.id,
            role=sample_user.role.value,
            email=sample_user.email,
            organization_id=sample_user.organization_id,
            expires_in=3600,
        )

    async def test_creates_refresh_token_long_expiry(self, use_case, user_repo, token_service, sample_user):
        user_repo.get_by_email.return_value = sample_user

        await use_case.execute("test@example.com", "secret123")

        token_service.create_access_token.assert_any_call(
            user_id=sample_user.id,
            role=sample_user.role.value,
            email=sample_user.email,
            organization_id=sample_user.organization_id,
            expires_in=86400,
        )


class TestAuthenticateFailure:
    async def test_user_not_found(self, use_case, user_repo):
        user_repo.get_by_email.return_value = None

        with pytest.raises(ValueError, match="Credenciales inválidas"):
            await use_case.execute("unknown@test.com", "password")

    async def test_user_inactive(self, use_case, user_repo, sample_user):
        sample_user.is_active = False
        user_repo.get_by_email.return_value = sample_user

        with pytest.raises(ValueError, match="Usuario inactivo"):
            await use_case.execute("test@example.com", "password")

    async def test_wrong_password(self, use_case, user_repo, password_hasher, sample_user):
        password_hasher.verify_password.return_value = False
        user_repo.get_by_email.return_value = sample_user

        with pytest.raises(ValueError, match="Credenciales inválidas"):
            await use_case.execute("test@example.com", "wrong-password")

    async def test_generic_error_message_does_not_leak_info(self, use_case, user_repo):
        user_repo.get_by_email.return_value = None

        with pytest.raises(ValueError, match="Credenciales inválidas"):
            await use_case.execute("nonexistent@test.com", "anything")

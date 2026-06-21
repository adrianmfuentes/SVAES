"""
Unit tests for service layer — branch coverage across all use cases.
Técnica: Branch Coverage (ISO 29119-4)
"""

import os
import sys
import pytest
import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call
from uuid import UUID, uuid4
from domain.entities.user import User

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET_KEY", "base-choice-test-secret-key-32-ch!")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXPIRE_MINUTES", "60")
os.environ.setdefault("ALLOWED_ORIGINS", "*")
os.environ.setdefault("ENCRYPTION_KEY", "g7vylajG0IOM0hvMbCNcVWN7G9l1oIF_pHFIj5uO5m8=") # NOSONAR
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
os.environ.setdefault("ENGINE_URL", "http://localhost:8081")
os.environ.setdefault("ENGINE_API_KEY", "test-key")
os.environ.setdefault("ADMIN_EMAIL", "admin@test.local")
os.environ.setdefault("ADMIN_PASSWORD", "admin-test-pass")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api", "src"))

pytestmark = pytest.mark.unit

_VALID_FERNET_KEY = "g7vylajG0IOM0hvMbCNcVWN7G9l1oIF_pHFIj5uO5m8=" # NOSONAR


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_user(
    *,
    is_active: bool = True,
    failed_attempts: int = 0,
    locked_until: datetime | None = None,
    totp_enabled: bool = False,
    totp_secret: str | None = None,
    role=None,
    organization_id: UUID | None = None,
) -> User:
    from domain.enums import UserRole
    return User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        display_name="Test User",
        role=role or UserRole.U2,
        is_active=is_active,
        failed_login_attempts=failed_attempts,
        locked_until=locked_until,
        totp_enabled=totp_enabled,
        totp_secret=totp_secret,
        organization_ids=[organization_id] if organization_id else [],
    )


def _make_release(status=None):
    from domain.entities.release import Release
    from domain.enums import ReleaseStatus
    return Release(
        id=uuid4(),
        name="v1.0.0",
        version="1.0.0",
        project_id=uuid4(),
        profile_id=uuid4(),
        created_by=uuid4(),
        status=status or ReleaseStatus.BORRADOR,
        artifacts=[],
    )


# ── AuthService ───────────────────────────────────────────────────────────────

class TestAuthService:
    @pytest.fixture
    def repos(self):
        return AsyncMock(), MagicMock(), MagicMock()

    @pytest.fixture
    def svc(self, repos):
        from application.use_cases.main.auth_service import AuthService
        user_repo, token_svc, pw_hasher = repos
        return AuthService(user_repo, token_svc, pw_hasher), user_repo, token_svc, pw_hasher

    async def test_authenticate_user_not_found_raises(self, svc):
        """Branch: user_repo returns None → ValidationError"""
        service, user_repo, *_ = svc
        user_repo.get_by_email = AsyncMock(return_value=None)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="Credenciales inválidas"):
            await service.authenticate("bad@x.com", "pw")

    async def test_authenticate_inactive_user_raises(self, svc):
        """Branch: user.is_active is False → ValidationError"""
        service, user_repo, *_ = svc
        user = _make_user(is_active=False)
        user_repo.get_by_email = AsyncMock(return_value=user)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="inactivo"):
            await service.authenticate("x@x.com", "pw")

    async def test_authenticate_account_locked_raises(self, svc):
        """Branch: locked_until in future → ValidationError"""
        service, user_repo, *_ = svc
        user = _make_user(locked_until=datetime.now(timezone.utc) + timedelta(minutes=10))
        user_repo.get_by_email = AsyncMock(return_value=user)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="bloqueada"):
            await service.authenticate("x@x.com", "pw")

    async def test_authenticate_max_attempts_exceeded_locks_account(self, svc):
        """Branch: failed_login_attempts >= MAX_LOGIN_ATTEMPTS → lockout + ValidationError"""
        service, user_repo, *_ = svc
        user = _make_user(failed_attempts=5)
        user_repo.get_by_email = AsyncMock(return_value=user)
        user_repo.update = AsyncMock(return_value=user)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="bloqueada"):
            await service.authenticate("x@x.com", "pw")
        user_repo.update.assert_awaited()
        assert user.failed_login_attempts == 0
        assert user.locked_until is not None

    async def test_authenticate_wrong_password_increments_counter(self, svc):
        """Branch: password hash mismatch → increment failed_attempts + ValidationError"""
        service, user_repo, _, pw_hasher = svc
        user = _make_user(failed_attempts=0)
        user_repo.get_by_email = AsyncMock(return_value=user)
        user_repo.update = AsyncMock(return_value=user)
        pw_hasher.verify_password = MagicMock(return_value=False)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="inválidas"):
            await service.authenticate("x@x.com", "wrong")
        assert user.failed_login_attempts == 1

    async def test_authenticate_success_resets_counter(self, svc):
        """Branch: success with prior failed attempts → reset counter"""
        service, user_repo, token_svc, pw_hasher = svc
        user = _make_user(failed_attempts=2)
        user_repo.get_by_email = AsyncMock(return_value=user)
        user_repo.update = AsyncMock(return_value=user)
        pw_hasher.verify_password = MagicMock(return_value=True)
        token_svc.create_access_token = MagicMock(return_value="access")
        token_svc.create_refresh_token = MagicMock(return_value="refresh")
        result = await service.authenticate("x@x.com", "right")
        assert user.failed_login_attempts == 0
        assert result.tokens is not None

    async def test_authenticate_success_no_totp_returns_tokens(self, svc):
        """Branch: success, totp_enabled=False → tokens returned directly"""
        service, user_repo, token_svc, pw_hasher = svc
        user = _make_user()
        user_repo.get_by_email = AsyncMock(return_value=user)
        user_repo.update = AsyncMock(return_value=user)
        pw_hasher.verify_password = MagicMock(return_value=True)
        token_svc.create_access_token = MagicMock(return_value="access")
        token_svc.create_refresh_token = MagicMock(return_value="refresh")
        result = await service.authenticate("x@x.com", "right")
        assert result.requires_2fa is False
        assert result.tokens is not None

    async def test_authenticate_totp_enabled_returns_pending(self, svc):
        """Branch: totp_enabled=True → requires_2fa=True + totp_token"""
        service, user_repo, token_svc, pw_hasher = svc
        import pyotp
        secret = pyotp.random_base32()
        user = _make_user(totp_enabled=True, totp_secret=secret)
        user_repo.get_by_email = AsyncMock(return_value=user)
        user_repo.update = AsyncMock(return_value=user)
        pw_hasher.verify_password = MagicMock(return_value=True)
        token_svc.create_totp_pending_token = MagicMock(return_value="pending-token")
        result = await service.authenticate("x@x.com", "right")
        assert result.requires_2fa is True
        assert result.totp_token == "pending-token"

    async def test_verify_totp_invalid_token_raises(self, svc):
        """Branch: verify_totp_pending_token returns None → ValidationError"""
        service, _, token_svc, _ = svc
        token_svc.verify_totp_pending_token = MagicMock(return_value=None)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="inválido"):
            await service.verify_totp("bad-token", "000000")

    async def test_verify_totp_user_not_found_raises(self, svc):
        """Branch: user not found after valid token → ValidationError"""
        service, user_repo, token_svc, _ = svc
        token_svc.verify_totp_pending_token = MagicMock(return_value=uuid4())
        user_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="fallida"):
            await service.verify_totp("tok", "000000")

    async def test_verify_totp_wrong_code_raises(self, svc):
        """Branch: totp.verify returns False → ValidationError + increment"""
        import pyotp
        service, user_repo, token_svc, _ = svc
        secret = pyotp.random_base32()
        user = _make_user(totp_enabled=True, totp_secret=secret)
        user_repo.get_by_id = AsyncMock(return_value=user)
        user_repo.update = AsyncMock(return_value=user)
        token_svc.verify_totp_pending_token = MagicMock(return_value=user.id)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="Código 2FA inválido"):
            await service.verify_totp("tok", "000000")
        assert user.failed_login_attempts == 1

    async def test_verify_totp_valid_code_returns_tokens(self, svc):
        """Branch: valid TOTP code → tokens returned"""
        import pyotp
        service, user_repo, token_svc, _ = svc
        secret = pyotp.random_base32()
        code = pyotp.TOTP(secret).now()
        user = _make_user(totp_enabled=True, totp_secret=secret, failed_attempts=1)
        user_repo.get_by_id = AsyncMock(return_value=user)
        user_repo.update = AsyncMock(return_value=user)
        token_svc.verify_totp_pending_token = MagicMock(return_value=user.id)
        token_svc.create_access_token = MagicMock(return_value="a")
        token_svc.create_refresh_token = MagicMock(return_value="r")
        result = await service.verify_totp("tok", code)
        assert result.tokens is not None
        assert user.failed_login_attempts == 0

    async def test_setup_totp_user_not_found_raises(self, svc):
        """Branch: user not found → ValidationError"""
        service, user_repo, *_ = svc
        user_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="no encontrado"):
            await service.setup_totp(uuid4())

    async def test_setup_totp_existing_secret_not_enabled_reuses(self, svc):
        """Branch: user has secret but not enabled → reuse existing secret"""
        import pyotp
        service, user_repo, *_ = svc
        existing_secret = pyotp.random_base32()
        user = _make_user(totp_secret=existing_secret, totp_enabled=False)
        user_repo.get_by_id = AsyncMock(return_value=user)
        user_repo.update = AsyncMock(return_value=user)
        mock_qr = MagicMock()
        mock_qr.save = MagicMock(side_effect=lambda buf, **kw: buf.write(b"<svg/>"))
        with patch("segno.make_qr", return_value=mock_qr):
            result = await service.setup_totp(user.id)
        assert result.secret == existing_secret

    async def test_setup_totp_no_secret_generates_new(self, svc):
        """Branch: user has no secret → generate new"""
        service, user_repo, *_ = svc
        user = _make_user(totp_secret=None, totp_enabled=False)
        user_repo.get_by_id = AsyncMock(return_value=user)
        user_repo.update = AsyncMock(return_value=user)
        mock_qr = MagicMock()
        mock_qr.save = MagicMock(side_effect=lambda buf, **kw: buf.write(b"<svg/>"))
        with patch("segno.make_qr", return_value=mock_qr):
            result = await service.setup_totp(user.id)
        assert result.secret is not None
        assert result.qr_data_url.startswith("data:image/svg+xml")

    async def test_enable_totp_user_not_found_raises(self, svc):
        """Branch: user not found → ValidationError"""
        service, user_repo, *_ = svc
        user_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError):
            await service.enable_totp(uuid4(), "000000")

    async def test_enable_totp_already_enabled_raises(self, svc):
        """Branch: user.totp_enabled is True → ValidationError"""
        import pyotp
        service, user_repo, *_ = svc
        user = _make_user(totp_enabled=True, totp_secret=pyotp.random_base32())
        user_repo.get_by_id = AsyncMock(return_value=user)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="ya está activado"):
            await service.enable_totp(user.id, "000000")

    async def test_enable_totp_invalid_code_raises(self, svc):
        """Branch: totp.verify returns False → ValidationError"""
        import pyotp
        service, user_repo, *_ = svc
        user = _make_user(totp_enabled=False, totp_secret=pyotp.random_base32())
        user_repo.get_by_id = AsyncMock(return_value=user)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="Código inválido"):
            await service.enable_totp(user.id, "000000")

    async def test_enable_totp_valid_code_enables(self, svc):
        """Branch: valid code → totp_enabled set to True"""
        import pyotp
        service, user_repo, *_ = svc
        secret = pyotp.random_base32()
        code = pyotp.TOTP(secret).now()
        user = _make_user(totp_enabled=False, totp_secret=secret)
        user_repo.get_by_id = AsyncMock(return_value=user)
        user_repo.update = AsyncMock(return_value=user)
        await service.enable_totp(user.id, code)
        assert user.totp_enabled is True

    async def test_disable_totp_not_enabled_raises(self, svc):
        """Branch: totp not enabled → ValidationError"""
        service, user_repo, *_ = svc
        user = _make_user(totp_enabled=False)
        user_repo.get_by_id = AsyncMock(return_value=user)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError):
            await service.disable_totp(user.id, "000000")

    async def test_disable_totp_valid_code_disables(self, svc):
        """Branch: valid code → totp_enabled=False, totp_secret=None"""
        import pyotp
        service, user_repo, *_ = svc
        secret = pyotp.random_base32()
        code = pyotp.TOTP(secret).now()
        user = _make_user(totp_enabled=True, totp_secret=secret)
        user_repo.get_by_id = AsyncMock(return_value=user)
        user_repo.update = AsyncMock(return_value=user)
        await service.disable_totp(user.id, code)
        assert user.totp_enabled is False
        assert user.totp_secret is None

    async def test_refresh_access_token_not_refresh_returns_none(self, svc):
        """Branch: token is not a refresh token → None"""
        service, _, token_svc, _ = svc
        token_svc.is_refresh_token = MagicMock(return_value=False)
        result = await service.refresh_access_token("some-token")
        assert result is None

    async def test_refresh_access_token_decode_error_returns_none(self, svc):
        """Branch: decode raises ValueError → None"""
        service, _, token_svc, _ = svc
        token_svc.is_refresh_token = MagicMock(return_value=True)
        token_svc.decode_token = MagicMock(side_effect=ValueError("bad token"))
        result = await service.refresh_access_token("bad")
        assert result is None

    async def test_refresh_access_token_user_not_found_returns_none(self, svc):
        """Branch: user not found after decode → None"""
        service, user_repo, token_svc, _ = svc
        token_svc.is_refresh_token = MagicMock(return_value=True)
        payload = MagicMock()
        payload.user_id = uuid4()
        payload.role = "U2"
        payload.email = "x@x.com"
        token_svc.decode_token = MagicMock(return_value=payload)
        user_repo.get_by_id = AsyncMock(return_value=None)
        result = await service.refresh_access_token("tok")
        assert result is None

    async def test_refresh_access_token_valid_returns_new_tokens(self, svc):
        """Branch: valid refresh token → new AuthTokens"""
        service, user_repo, token_svc, _ = svc
        token_svc.is_refresh_token = MagicMock(return_value=True)
        user = _make_user()
        payload = MagicMock()
        payload.user_id = user.id
        payload.role = "U2"
        payload.email = user.email
        token_svc.decode_token = MagicMock(return_value=payload)
        user_repo.get_by_id = AsyncMock(return_value=user)
        token_svc.create_access_token = MagicMock(return_value="new-access")
        token_svc.create_refresh_token = MagicMock(return_value="new-refresh")
        result = await service.refresh_access_token("tok")
        assert result is not None
        assert result.access_token == "new-access"

    async def test_logout_blacklists_token(self, svc):
        """Branch: logout calls blacklist_token"""
        service, _, token_svc, _ = svc
        token_svc.blacklist_token = MagicMock()
        await service.logout(uuid4(), "tok")
        token_svc.blacklist_token.assert_called_once()


# ── UserService ───────────────────────────────────────────────────────────────

class TestUserService:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.user_service import UserService
        user_repo = AsyncMock()
        org_repo = AsyncMock()
        pw_hasher = MagicMock()
        return UserService(user_repo, org_repo, pw_hasher), user_repo, org_repo, pw_hasher

    async def test_get_user_by_id_returns_user(self, svc):
        """Branch: get_by_id returns user"""
        service, user_repo, *_ = svc
        user = _make_user()
        user_repo.get_by_id = AsyncMock(return_value=user)
        result = await service.get_user_by_id(user.id)
        assert result == user

    async def test_update_profile_user_not_found_raises(self, svc):
        """Branch: get_by_id returns None → EntityNotFoundError"""
        service, user_repo, *_ = svc
        user_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import EntityNotFoundError
        with pytest.raises(EntityNotFoundError):
            await service.update_profile(uuid4(), "new name")

    async def test_update_profile_updates_display_name(self, svc):
        """Branch: display_name is not None → update"""
        service, user_repo, *_ = svc
        user = _make_user()
        user_repo.get_by_id = AsyncMock(return_value=user)
        user_repo.update = AsyncMock(return_value=user)
        await service.update_profile(user.id, "New Name")
        assert user.display_name == "New Name"

    async def test_update_profile_no_display_name_skips_update(self, svc):
        """Branch: display_name is None → no change"""
        service, user_repo, *_ = svc
        user = _make_user()
        original_name = user.display_name
        user_repo.get_by_id = AsyncMock(return_value=user)
        user_repo.update = AsyncMock(return_value=user)
        await service.update_profile(user.id, None)
        assert user.display_name == original_name

    async def test_change_password_user_not_found_raises(self, svc):
        """Branch: user not found → EntityNotFoundError"""
        service, user_repo, *_ = svc
        user_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import EntityNotFoundError
        with pytest.raises(EntityNotFoundError):
            await service.change_password(uuid4(), "old", "new")

    async def test_change_password_wrong_current_returns_false(self, svc):
        """Branch: verify_password returns False → return False"""
        service, user_repo, _, pw_hasher = svc
        user = _make_user()
        user_repo.get_by_id = AsyncMock(return_value=user)
        pw_hasher.verify_password = MagicMock(return_value=False)
        result = await service.change_password(user.id, "wrong", "new")
        assert result is False

    async def test_change_password_success_returns_true(self, svc):
        """Branch: valid current password → update and return True"""
        service, user_repo, _, pw_hasher = svc
        user = _make_user()
        user_repo.get_by_id = AsyncMock(return_value=user)
        user_repo.update = AsyncMock(return_value=user)
        pw_hasher.verify_password = MagicMock(return_value=True)
        pw_hasher.hash_password = MagicMock(return_value="new-hash")
        result = await service.change_password(user.id, "correct", "new")
        assert result is True

    async def test_invite_user_org_not_found_raises(self, svc):
        """Branch: org not found → EntityNotFoundError"""
        service, _, org_repo, _ = svc
        org_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import EntityNotFoundError
        from domain.enums import UserRole
        with pytest.raises(EntityNotFoundError):
            await service.invite_user(uuid4(), "e@x.com", UserRole.U2, uuid4())

    async def test_invite_user_already_in_org_raises(self, svc):
        """Branch: existing user already belongs to org → DuplicateEntityError"""
        service, user_repo, org_repo, _ = svc
        org_id = uuid4()
        org = MagicMock()
        org_repo.get_by_id = AsyncMock(return_value=org)
        existing = _make_user(organization_id=org_id)
        user_repo.get_by_email = AsyncMock(return_value=existing)
        from domain.exceptions import DuplicateEntityError
        from domain.enums import UserRole
        with pytest.raises(DuplicateEntityError):
            await service.invite_user(org_id, existing.email, UserRole.U2, uuid4())

    async def test_invite_user_existing_without_org_joins(self, svc):
        """Branch: existing user has no org → assign to org"""
        service, user_repo, org_repo, _ = svc
        org = MagicMock()
        org_repo.get_by_id = AsyncMock(return_value=org)
        existing = _make_user()
        user_repo.get_by_email = AsyncMock(return_value=existing)
        user_repo.update = AsyncMock(return_value=existing)
        from domain.enums import UserRole
        result = await service.invite_user(uuid4(), existing.email, UserRole.U2, uuid4())
        assert result == existing

    async def test_invite_user_new_user_creates(self, svc):
        """Branch: no existing user → create new"""
        service, user_repo, org_repo, pw_hasher = svc
        org = MagicMock()
        org_repo.get_by_id = AsyncMock(return_value=org)
        user_repo.get_by_email = AsyncMock(return_value=None)
        new_user = _make_user()
        user_repo.create = AsyncMock(return_value=new_user)
        pw_hasher.hash_password = MagicMock(return_value="hashed")
        from domain.enums import UserRole
        result = await service.invite_user(uuid4(), "new@x.com", UserRole.U2, uuid4())
        assert result is not None

    async def test_update_user_role_owner_raises(self, svc):
        """Branch: target is org owner → ValidationError"""
        service, user_repo, org_repo, _ = svc
        org_id = uuid4()
        user = _make_user(organization_id=org_id)
        org = MagicMock()
        org.owner_id = user.id
        user_repo.get_by_id = AsyncMock(return_value=user)
        org_repo.get_by_id = AsyncMock(return_value=org)
        from domain.exceptions import ValidationError
        from domain.enums import UserRole
        with pytest.raises(ValidationError, match="Owner"):
            await service.update_user_role(user.id, org_id, UserRole.U1, uuid4())

    async def test_update_user_role_success(self, svc):
        """Branch: valid non-owner user → role updated"""
        service, user_repo, org_repo, _ = svc
        org_id = uuid4()
        user = _make_user(organization_id=org_id)
        org = MagicMock()
        org.owner_id = uuid4()
        user_repo.get_by_id = AsyncMock(return_value=user)
        org_repo.get_by_id = AsyncMock(return_value=org)
        user_repo.update = AsyncMock(return_value=user)
        from domain.enums import UserRole
        result = await service.update_user_role(user.id, org_id, UserRole.U1, uuid4())
        assert result == user

    async def test_remove_user_not_in_org_raises(self, svc):
        """Branch: user not in org → EntityNotFoundError"""
        service, user_repo, *_ = svc
        user = _make_user()
        user_repo.get_by_id = AsyncMock(return_value=user)
        from domain.exceptions import EntityNotFoundError
        with pytest.raises(EntityNotFoundError):
            await service.remove_user_from_organization(user.id, uuid4(), uuid4())

    async def test_remove_user_owner_raises(self, svc):
        """Branch: user is org owner → ValidationError"""
        service, user_repo, org_repo, _ = svc
        org_id = uuid4()
        user = _make_user(organization_id=org_id)
        org = MagicMock()
        org.owner_id = user.id
        user_repo.get_by_id = AsyncMock(return_value=user)
        org_repo.get_by_id = AsyncMock(return_value=org)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="Owner"):
            await service.remove_user_from_organization(user.id, org_id, uuid4())

    async def test_remove_user_success_clears_org(self, svc):
        """Branch: valid removal → organization_id cleared"""
        service, user_repo, org_repo, _ = svc
        org_id = uuid4()
        user = _make_user(organization_id=org_id)
        org = MagicMock()
        org.owner_id = uuid4()
        user_repo.get_by_id = AsyncMock(return_value=user)
        org_repo.get_by_id = AsyncMock(return_value=org)
        user_repo.update = AsyncMock(return_value=user)
        await service.remove_user_from_organization(user.id, org_id, uuid4())
        assert user.organization_id is None

    async def test_create_user_duplicate_raises(self, svc):
        """Branch: email already exists → DuplicateEntityError"""
        service, user_repo, *_ = svc
        user_repo.get_by_email = AsyncMock(return_value=_make_user())
        from domain.exceptions import DuplicateEntityError
        from domain.enums import UserRole
        with pytest.raises(DuplicateEntityError):
            await service.create_user("dup@x.com", "n", "p", UserRole.U2)

    async def test_create_user_success(self, svc):
        """Branch: no existing user → create and return"""
        service, user_repo, _, pw_hasher = svc
        user_repo.get_by_email = AsyncMock(return_value=None)
        new_user = _make_user()
        user_repo.create = AsyncMock(return_value=new_user)
        pw_hasher.hash_password = MagicMock(return_value="h")
        from domain.enums import UserRole
        result = await service.create_user("new@x.com", "name", "pass", UserRole.U2)
        assert result is not None

    async def test_activate_user_not_found_raises(self, svc):
        """Branch: user not found → EntityNotFoundError"""
        service, user_repo, *_ = svc
        user_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import EntityNotFoundError
        with pytest.raises(EntityNotFoundError):
            await service.activate_user(uuid4())

    async def test_activate_user_sets_active(self, svc):
        """Branch: user found → is_active=True"""
        service, user_repo, *_ = svc
        user = _make_user(is_active=False)
        user_repo.get_by_id = AsyncMock(return_value=user)
        user_repo.update = AsyncMock(return_value=user)
        result = await service.activate_user(user.id)
        assert user.is_active is True

    async def test_deactivate_user_sets_inactive(self, svc):
        """Branch: user found → is_active=False"""
        service, user_repo, *_ = svc
        user = _make_user()
        user_repo.get_by_id = AsyncMock(return_value=user)
        user_repo.update = AsyncMock(return_value=user)
        await service.deactivate_user(user.id, uuid4())
        assert user.is_active is False

    async def test_list_all_users_with_role_filter(self, svc):
        """Branch: role is not None → filter by role"""
        service, user_repo, *_ = svc
        from domain.enums import UserRole
        users = [_make_user(role=UserRole.U2), _make_user(role=UserRole.U1)]
        user_repo.list_all = AsyncMock(return_value=users)
        result = await service.list_all_users(role=UserRole.U2)
        assert all(u.role == UserRole.U2 for u in result)

    async def test_list_all_users_no_filter_returns_all(self, svc):
        """Branch: role is None → return all users"""
        service, user_repo, *_ = svc
        from domain.enums import UserRole
        users = [_make_user(role=UserRole.U2), _make_user(role=UserRole.U1)]
        user_repo.list_all = AsyncMock(return_value=users)
        result = await service.list_all_users()
        assert len(result) == 2

    async def test_delete_user_account_wrong_password_raises(self, svc):
        """Branch: verify_password returns False → AuthenticationError"""
        service, user_repo, _, pw_hasher = svc
        user = _make_user()
        user_repo.get_by_id = AsyncMock(return_value=user)
        pw_hasher.verify_password = MagicMock(return_value=False)
        from domain.exceptions import AuthenticationError
        with pytest.raises(AuthenticationError):
            await service.delete_user_account(user.id, user.id, "wrong")

    async def test_delete_user_account_owner_of_org_raises(self, svc):
        """Branch: user owns an org → ValidationError"""
        service, user_repo, org_repo, pw_hasher = svc
        org_id = uuid4()
        user = _make_user(organization_id=org_id)
        user_repo.get_by_id = AsyncMock(return_value=user)
        pw_hasher.verify_password = MagicMock(return_value=True)
        org = MagicMock()
        org.owner_id = user.id
        org_repo.get_by_id = AsyncMock(return_value=org)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="propietario"):
            await service.delete_user_account(user.id, user.id, "right")

    async def test_delete_user_account_success(self, svc):
        """Branch: no org ownership → delete called"""
        service, user_repo, org_repo, pw_hasher = svc
        user = _make_user()
        user_repo.get_by_id = AsyncMock(return_value=user)
        pw_hasher.verify_password = MagicMock(return_value=True)
        user_repo.delete = AsyncMock()
        await service.delete_user_account(user.id, user.id, "right")
        user_repo.delete.assert_awaited_once_with(user.id)


# ── CreateReleaseUseCase ──────────────────────────────────────────────────────

class TestReleaseServiceUnit:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.release_service import CreateReleaseUseCase
        rel_repo = AsyncMock()
        proj_repo = AsyncMock()
        prof_repo = AsyncMock()
        return CreateReleaseUseCase(rel_repo, proj_repo, prof_repo), rel_repo, proj_repo, prof_repo

    async def test_create_release_invalid_semver_raises(self, svc):
        """Branch: invalid semver → ValidationError"""
        service, *_ = svc
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="SemVer"):
            await service.create_release("name", "not-semver", uuid4(), uuid4())

    async def test_create_release_project_not_found_raises(self, svc):
        """Branch: project not found → ValidationError"""
        service, _, proj_repo, _ = svc
        proj_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="proyecto"):
            await service.create_release("name", "1.0.0", uuid4(), uuid4())

    async def test_create_release_profile_not_found_raises(self, svc):
        """Branch: resolved profile_id not found → ValidationError"""
        service, rel_repo, proj_repo, prof_repo = svc
        project = MagicMock()
        project.organization_id = uuid4()
        project.profile_id = uuid4()
        proj_repo.get_by_id = AsyncMock(return_value=project)
        prof_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="perfil"):
            await service.create_release("name", "1.0.0", uuid4(), uuid4())

    async def test_create_release_no_profile_id_success(self, svc):
        """Branch: no profile_id (None) → skip profile check"""
        service, rel_repo, proj_repo, prof_repo = svc
        project = MagicMock()
        project.organization_id = uuid4()
        project.profile_id = None
        proj_repo.get_by_id = AsyncMock(return_value=project)
        rel_repo.create = AsyncMock()
        result = await service.create_release("name", "1.0.0", uuid4(), uuid4())
        assert result.version == "1.0.0"

    async def test_create_release_with_valid_profile_success(self, svc):
        """Branch: project has profile_id + profile exists → success"""
        service, rel_repo, proj_repo, prof_repo = svc
        profile = MagicMock()
        project = MagicMock()
        project.organization_id = uuid4()
        project.profile_id = uuid4()
        proj_repo.get_by_id = AsyncMock(return_value=project)
        prof_repo.get_by_id = AsyncMock(return_value=profile)
        rel_repo.create = AsyncMock()
        result = await service.create_release("name", "1.0.0", uuid4(), uuid4())
        assert result.name == "name"

    async def test_get_release_returns_value(self, svc):
        service, rel_repo, *_ = svc
        rel = _make_release()
        rel_repo.get_by_id = AsyncMock(return_value=rel)
        result = await service.get_release(rel.id)
        assert result == rel

    async def test_update_release_not_found_raises(self, svc):
        """Branch: release not found → ValidationError"""
        service, rel_repo, *_ = svc
        rel_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError):
            await service.update_release(uuid4(), name="new")

    async def test_update_release_invalid_semver_raises(self, svc):
        """Branch: version provided but invalid → ValidationError"""
        service, rel_repo, *_ = svc
        rel = _make_release()
        rel_repo.get_by_id = AsyncMock(return_value=rel)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="SemVer"):
            await service.update_release(rel.id, version="bad-ver")

    async def test_update_release_partial_fields(self, svc):
        """Branch: only name and description provided → update"""
        service, rel_repo, *_ = svc
        rel = _make_release()
        rel_repo.get_by_id = AsyncMock(return_value=rel)
        rel_repo.update = AsyncMock(return_value=rel)
        result = await service.update_release(rel.id, name="new", description="desc")
        assert result.name == "new"

    async def test_add_artifact_release_not_found_raises(self, svc):
        """Branch: release not found → ValidationError"""
        service, rel_repo, *_ = svc
        rel_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError):
            await service.add_artifact(uuid4(), uuid4(), "JIRA", "TICKET", "J-1")

    async def test_add_artifact_appends_and_updates(self, svc):
        """Branch: release found → artifact appended"""
        service, rel_repo, *_ = svc
        rel = _make_release()
        rel_repo.get_by_id = AsyncMock(return_value=rel)
        rel_repo.update = AsyncMock(return_value=rel)
        artifact = await service.add_artifact(rel.id, uuid4(), "JIRA", "TICKET", "J-1")
        assert len(rel.artifacts) == 1
        assert artifact.external_ref == "J-1"

    async def test_remove_artifact_not_found_raises(self, svc):
        """Branch: artifact not found → ValidationError"""
        service, rel_repo, *_ = svc
        rel_repo.get_artifact_by_id = AsyncMock(return_value=None)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError):
            await service.remove_artifact(uuid4())

    async def test_delete_release_not_found_raises(self, svc):
        """Branch: release not found → ValidationError"""
        service, rel_repo, *_ = svc
        rel_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError):
            await service.delete_release(uuid4())

    async def test_delete_release_success(self, svc):
        """Branch: release found → delete called"""
        service, rel_repo, *_ = svc
        rel = _make_release()
        rel_repo.get_by_id = AsyncMock(return_value=rel)
        rel_repo.delete = AsyncMock()
        await service.delete_release(rel.id)
        rel_repo.delete.assert_awaited_once()

    async def test_restore_release_not_found_raises(self, svc):
        """Branch: release not found → ValidationError"""
        service, rel_repo, *_ = svc
        rel_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError):
            await service.restore_release(uuid4())

    async def test_restore_release_not_archived_raises(self, svc):
        """Branch: release not ARCHIVADA → ValidationError"""
        service, rel_repo, *_ = svc
        from domain.enums import ReleaseStatus
        rel = _make_release(status=ReleaseStatus.BORRADOR)
        rel_repo.get_by_id = AsyncMock(return_value=rel)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="archivadas"):
            await service.restore_release(rel.id)

    async def test_restore_release_archived_succeeds(self, svc):
        """Branch: ARCHIVADA → status set to BORRADOR"""
        service, rel_repo, *_ = svc
        from domain.enums import ReleaseStatus
        rel = _make_release(status=ReleaseStatus.ARCHIVADA)
        rel_repo.get_by_id = AsyncMock(return_value=rel)
        rel_repo.update = AsyncMock(return_value=rel)
        await service.restore_release(rel.id)
        assert rel.status == ReleaseStatus.BORRADOR

    async def test_update_status_not_found_raises(self, svc):
        """Branch: update_status returns None → ValidationError"""
        service, rel_repo, *_ = svc
        rel_repo.update_status = AsyncMock(return_value=None)
        from domain.exceptions import ValidationError
        from domain.enums import ReleaseStatus
        with pytest.raises(ValidationError):
            await service.update_status(uuid4(), ReleaseStatus.VALIDA)

    async def test_list_artifacts_release_not_found_raises(self, svc):
        """Branch: release not found → ValidationError"""
        service, rel_repo, *_ = svc
        rel_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError):
            await service.list_artifacts(uuid4())

    def test_is_valid_semver_valid(self, svc):
        """Branch: valid semver → True"""
        service, *_ = svc
        assert service._is_valid_semver("1.0.0") is True
        assert service._is_valid_semver("1.0.0-alpha.1") is True
        assert service._is_valid_semver("1.0.0+build.1") is True

    def test_is_valid_semver_invalid(self, svc):
        """Branch: invalid semver → False"""
        service, *_ = svc
        assert service._is_valid_semver("not-semver") is False
        assert service._is_valid_semver("1.0") is False


# ── OrganizationService ───────────────────────────────────────────────────────

class TestOrganizationService:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.organization_service import OrganizationService
        org_repo = AsyncMock()
        proj_repo = AsyncMock()
        user_repo = AsyncMock()
        return OrganizationService(org_repo, proj_repo, user_repo), org_repo, proj_repo, user_repo

    async def test_create_org_duplicate_slug_raises(self, svc):
        """Branch: existing org with same slug → DuplicateEntityError"""
        service, org_repo, *_ = svc
        org_repo.get_by_slug = AsyncMock(return_value=MagicMock())
        from domain.exceptions import DuplicateEntityError
        with pytest.raises(DuplicateEntityError):
            await service.create_organization("name", "existing-slug")

    async def test_create_org_owner_is_admin_raises(self, svc):
        """Branch: owner has U3 role → ValidationError"""
        service, org_repo, _, user_repo = svc
        org_repo.get_by_slug = AsyncMock(return_value=None)
        from domain.enums import UserRole
        admin = _make_user(role=UserRole.U3)
        user_repo.get_by_id = AsyncMock(return_value=admin)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="administrador"):
            await service.create_organization("name", "slug", owner_id=admin.id)

    async def test_create_org_success(self, svc):
        """Branch: no slug conflict, valid owner → org created"""
        service, org_repo, _, user_repo = svc
        org_repo.get_by_slug = AsyncMock(return_value=None)
        from domain.enums import UserRole
        owner = _make_user(role=UserRole.U2)
        user_repo.get_by_id = AsyncMock(return_value=owner)
        created_org = MagicMock()
        created_org.id = uuid4()
        org_repo.create = AsyncMock(return_value=created_org)
        user_repo.update = AsyncMock(return_value=owner)
        result = await service.create_organization("name", "slug", owner_id=owner.id)
        assert result == created_org

    async def test_create_project_org_not_found_raises(self, svc):
        """Branch: org not found → EntityNotFoundError"""
        service, org_repo, *_ = svc
        org_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import EntityNotFoundError
        with pytest.raises(EntityNotFoundError):
            await service.create_project(uuid4(), "name", "desc", uuid4())

    async def test_create_project_success(self, svc):
        """Branch: org found → project created"""
        service, org_repo, proj_repo, _ = svc
        org_repo.get_by_id = AsyncMock(return_value=MagicMock())
        project = MagicMock()
        proj_repo.create = AsyncMock(return_value=project)
        result = await service.create_project(uuid4(), "name", "desc", uuid4())
        assert result == project

    async def test_archive_project_not_found_raises(self, svc):
        """Branch: project not found → EntityNotFoundError"""
        service, _, proj_repo, _ = svc
        proj_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import EntityNotFoundError
        with pytest.raises(EntityNotFoundError):
            await service.archive_project(uuid4())

    async def test_archive_project_success(self, svc):
        """Branch: project found → is_archived=True"""
        service, _, proj_repo, _ = svc
        project = MagicMock()
        project.organization_id = uuid4()
        project.name = "test"
        proj_repo.get_by_id = AsyncMock(return_value=project)
        proj_repo.update = AsyncMock(return_value=project)
        await service.archive_project(uuid4())
        assert project.is_archived is True

    async def test_transfer_ownership_org_not_found_raises(self, svc):
        """Branch: org not found → EntityNotFoundError"""
        service, org_repo, *_ = svc
        org_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import EntityNotFoundError
        with pytest.raises(EntityNotFoundError):
            await service.transfer_ownership(uuid4(), uuid4(), uuid4())

    async def test_transfer_ownership_new_owner_admin_raises(self, svc):
        """Branch: new owner is admin (U3) → ValidationError"""
        service, org_repo, _, user_repo = svc
        org = MagicMock()
        org.owner_id = uuid4()
        org_repo.get_by_id = AsyncMock(return_value=org)
        from domain.enums import UserRole
        admin = _make_user(role=UserRole.U3)
        user_repo.get_by_id = AsyncMock(return_value=admin)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError):
            await service.transfer_ownership(uuid4(), admin.id, uuid4())

    async def test_transfer_ownership_success(self, svc):
        """Branch: valid new owner → org updated"""
        service, org_repo, _, user_repo = svc
        org = MagicMock()
        org.owner_id = uuid4()
        org_repo.get_by_id = AsyncMock(return_value=org)
        from domain.enums import UserRole
        new_owner = _make_user(role=UserRole.U2)
        user_repo.get_by_id = AsyncMock(return_value=new_owner)
        org_repo.update = AsyncMock(return_value=org)
        result = await service.transfer_ownership(uuid4(), new_owner.id, uuid4())
        assert result == org

    async def test_restore_organization_not_found_raises(self, svc):
        """Branch: org not found → EntityNotFoundError"""
        service, org_repo, *_ = svc
        org_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import EntityNotFoundError
        with pytest.raises(EntityNotFoundError):
            await service.restore_organization(uuid4())

    async def test_restore_organization_success(self, svc):
        """Branch: org found → is_active=True"""
        service, org_repo, *_ = svc
        org = MagicMock()
        org_repo.get_by_id = AsyncMock(return_value=org)
        org_repo.update = AsyncMock(return_value=org)
        result = await service.restore_organization(uuid4())
        assert org.is_active is True


# ── NotificationService ───────────────────────────────────────────────────────

class TestNotificationService:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.notification_service import NotificationService
        repo = AsyncMock()
        return NotificationService(repo), repo

    async def test_list_channels_returns_all_types(self, svc):
        """Branch: some channels configured, some not → result has all 3 types"""
        service, repo = svc
        from domain.entities.notification_channel import NotificationChannel
        ch = NotificationChannel(
            organization_id=uuid4(),
            channel_type="EMAIL",
            enabled=True,
            config_data={"to": "x@x.com"},
        )
        repo.list_channels = AsyncMock(return_value=[ch])
        result = await service.list_channels(uuid4())
        assert len(result) == 3
        configured = [r for r in result if r["configured"]]
        assert len(configured) == 1

    async def test_configure_channel_unsupported_type_raises(self, svc):
        """Branch: channel_type not in SUPPORTED_CHANNEL_TYPES → ValidationError"""
        service, _ = svc
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="no soportado"):
            await service.configure_channel(uuid4(), "WEBHOOK", True, {})

    async def test_configure_channel_success(self, svc):
        """Branch: valid channel_type → channel created"""
        service, repo = svc
        from domain.entities.notification_channel import NotificationChannel
        ch = NotificationChannel(organization_id=uuid4(), channel_type="EMAIL", enabled=True)
        repo.create_channel = AsyncMock(return_value=ch)
        result = await service.configure_channel(uuid4(), "EMAIL", True, {"x": 1})
        assert result.channel_type == "EMAIL"

    async def test_update_channel_not_found_raises(self, svc):
        """Branch: channel not found → EntityNotFoundError"""
        service, repo = svc
        repo.get_channel_by_id = AsyncMock(return_value=None)
        from domain.exceptions import EntityNotFoundError
        with pytest.raises(EntityNotFoundError):
            await service.update_channel(uuid4(), enabled=True)

    async def test_update_channel_updates_fields(self, svc):
        """Branch: both enabled and config_data provided → both updated"""
        service, repo = svc
        from domain.entities.notification_channel import NotificationChannel
        ch = NotificationChannel(organization_id=uuid4(), channel_type="SLACK", enabled=False)
        repo.get_channel_by_id = AsyncMock(return_value=ch)
        repo.update_channel = AsyncMock(return_value=ch)
        await service.update_channel(ch.id, enabled=True, config_data={"url": "x"})
        assert ch.enabled is True
        assert ch.config_data == {"url": "x"}

    async def test_delete_channel_not_found_raises(self, svc):
        """Branch: channel not found → EntityNotFoundError"""
        service, repo = svc
        repo.get_channel_by_id = AsyncMock(return_value=None)
        from domain.exceptions import EntityNotFoundError
        with pytest.raises(EntityNotFoundError):
            await service.delete_channel(uuid4())

    async def test_delete_channel_success(self, svc):
        """Branch: channel found → deleted"""
        service, repo = svc
        from domain.entities.notification_channel import NotificationChannel
        ch = NotificationChannel(organization_id=uuid4(), channel_type="EMAIL", enabled=True)
        repo.get_channel_by_id = AsyncMock(return_value=ch)
        repo.delete_channel = AsyncMock()
        await service.delete_channel(ch.id)
        repo.delete_channel.assert_awaited_once()

    async def test_get_user_preferences_no_subscriptions(self, svc):
        """Branch: no subscriptions → default prefs"""
        service, repo = svc
        repo.list_subscriptions = AsyncMock(return_value=[])
        prefs = await service.get_user_preferences(uuid4())
        assert prefs["release_validated"] is True
        assert prefs["release_pending_reminder"] is False

    async def test_get_user_preferences_with_subscriptions(self, svc):
        """Branch: subscriptions override defaults"""
        service, repo = svc
        sub = MagicMock()
        sub.event_type = "RELEASE_VALIDATED"
        sub.enabled = False
        repo.list_subscriptions = AsyncMock(return_value=[sub])
        prefs = await service.get_user_preferences(uuid4())
        assert prefs["release_validated"] is False

    async def test_subscribe_invalid_event_raises(self, svc):
        """Branch: event_type not supported → ValidationError"""
        service, _ = svc
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="no soportado"):
            await service.subscribe(uuid4(), "INVALID_EVENT")

    async def test_subscribe_valid_event_returns_dict(self, svc):
        """Branch: valid event → subscription created"""
        service, repo = svc
        from domain.entities.notification_subscription import NotificationSubscription
        sub = NotificationSubscription(user_id=uuid4(), event_type="RELEASE_VALIDATED", enabled=True)
        repo.upsert_subscription = AsyncMock(return_value=sub)
        result = await service.subscribe(uuid4(), "RELEASE_VALIDATED")
        assert result["event_type"] == "RELEASE_VALIDATED"

    async def test_update_user_preferences_none_values_skipped(self, svc):
        """Branch: None values → upsert not called for that event"""
        service, repo = svc
        repo.upsert_subscription = AsyncMock()
        repo.list_subscriptions = AsyncMock(return_value=[])
        await service.update_user_preferences(uuid4(), release_validated=True, weekly_digest=None)
        assert repo.upsert_subscription.await_count == 1

    async def test_unsubscribe_calls_delete(self, svc):
        """Branch: unsubscribe → delete_subscription called"""
        service, repo = svc
        repo.delete_subscription = AsyncMock()
        await service.unsubscribe(uuid4(), "RELEASE_VALIDATED")
        repo.delete_subscription.assert_awaited_once()


# ── ManageApiKeysUseCase ──────────────────────────────────────────────────────

class TestManageApiKeys:
    @pytest.fixture
    def svc(self):
        from application.use_cases.others.manage_api_keys import ManageApiKeysUseCase
        repo = AsyncMock()
        return ManageApiKeysUseCase(repo), repo

    async def test_create_empty_name_raises(self, svc):
        """Branch: name is empty → ValidationError"""
        service, _ = svc
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="requerido"):
            await service.create_api_key(uuid4(), uuid4(), "")

    async def test_create_limit_exceeded_raises(self, svc):
        """Branch: 5 active keys → ValidationError"""
        service, repo = svc
        keys = [MagicMock(is_active=True) for _ in range(5)]
        repo.list_by_user = AsyncMock(return_value=keys)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="límite"):
            await service.create_api_key(uuid4(), uuid4(), "my-key")

    async def test_create_with_expiry_success(self, svc):
        """Branch: expires_in_days provided → expires_at set"""
        service, repo = svc
        repo.list_by_user = AsyncMock(return_value=[])
        from domain.entities.api_key import APIKey
        saved = MagicMock()
        saved.id = uuid4()
        saved.user_id = uuid4()
        saved.organization_id = uuid4()
        saved.name = "key"
        saved.prefix = "svk_123456"
        saved.expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        saved.is_active = True
        saved.created_at = datetime.now(timezone.utc)
        repo.save = AsyncMock(return_value=saved)
        result = await service.create_api_key(uuid4(), uuid4(), "key", expires_in_days=30)
        assert result["expires_at"] is not None

    async def test_create_without_expiry_success(self, svc):
        """Branch: expires_in_days is None → expires_at is None"""
        service, repo = svc
        repo.list_by_user = AsyncMock(return_value=[])
        saved = MagicMock()
        saved.id = uuid4()
        saved.user_id = uuid4()
        saved.organization_id = uuid4()
        saved.name = "key"
        saved.prefix = "svk_123456"
        saved.expires_at = None
        saved.is_active = True
        saved.created_at = datetime.now(timezone.utc)
        repo.save = AsyncMock(return_value=saved)
        result = await service.create_api_key(uuid4(), uuid4(), "key")
        assert result["expires_at"] is None

    async def test_list_api_keys_with_last_used(self, svc):
        """Branch: last_used_at is not None → isoformat called"""
        service, repo = svc
        k = MagicMock()
        k.id = uuid4()
        k.name = "k"
        k.prefix = "svk_"
        k.is_active = True
        k.expires_at = None
        k.created_at = datetime.now(timezone.utc)
        k.last_used_at = datetime.now(timezone.utc)
        repo.list_by_user = AsyncMock(return_value=[k])
        result = await service.list_api_keys(uuid4())
        assert result[0]["last_used_at"] is not None

    async def test_revoke_not_found_raises(self, svc):
        """Branch: key not found → EntityNotFoundError"""
        service, repo = svc
        repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import EntityNotFoundError
        with pytest.raises(EntityNotFoundError):
            await service.revoke_api_key(uuid4(), uuid4())

    async def test_revoke_wrong_user_raises(self, svc):
        """Branch: key belongs to different user → EntityNotFoundError"""
        service, repo = svc
        k = MagicMock()
        k.user_id = uuid4()
        repo.get_by_id = AsyncMock(return_value=k)
        from domain.exceptions import EntityNotFoundError
        with pytest.raises(EntityNotFoundError):
            await service.revoke_api_key(uuid4(), uuid4())

    async def test_revoke_success(self, svc):
        """Branch: key belongs to user → is_active=False"""
        service, repo = svc
        user_id = uuid4()
        k = MagicMock()
        k.user_id = user_id
        k.organization_id = uuid4()
        k.name = "k"
        updated = MagicMock()
        updated.id = uuid4()
        updated.is_active = False
        repo.get_by_id = AsyncMock(return_value=k)
        repo.update = AsyncMock(return_value=updated)
        result = await service.revoke_api_key(k.id or uuid4(), user_id)
        assert result["is_active"] is False

    async def test_validate_key_not_found_returns_none(self, svc):
        """Branch: hash not found → None"""
        service, repo = svc
        repo.get_by_hash = AsyncMock(return_value=None)
        result = await service.validate_api_key("svk_test-key")
        assert result is None

    async def test_validate_key_inactive_returns_none(self, svc):
        """Branch: key found but not active → None"""
        service, repo = svc
        k = MagicMock(is_active=False)
        repo.get_by_hash = AsyncMock(return_value=k)
        result = await service.validate_api_key("svk_test-key")
        assert result is None

    async def test_validate_key_expired_returns_none(self, svc):
        """Branch: key found, active, but expired → None"""
        service, repo = svc
        k = MagicMock(is_active=True)
        k.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        repo.get_by_hash = AsyncMock(return_value=k)
        result = await service.validate_api_key("svk_test-key")
        assert result is None

    async def test_validate_key_valid_updates_last_used(self, svc):
        """Branch: active, not expired → update last_used_at"""
        service, repo = svc
        k = MagicMock(is_active=True)
        k.expires_at = None
        repo.get_by_hash = AsyncMock(return_value=k)
        repo.update = AsyncMock(return_value=k)
        result = await service.validate_api_key("svk_test-key")
        assert result is not None
        repo.update.assert_awaited_once()


# ── ConnectorService ──────────────────────────────────────────────────────────

class TestConnectorService:
    @pytest.fixture(autouse=True)
    def patch_settings_key(self, monkeypatch):
        from core import config as cfg
        monkeypatch.setattr(cfg.settings, "encryption_key", _VALID_FERNET_KEY)

    @pytest.fixture
    def svc(self):
        from application.use_cases.main.connector_service import ConnectorService
        conn_repo = AsyncMock()
        registry = MagicMock()
        return ConnectorService(conn_repo, registry), conn_repo, registry

    async def test_register_duplicate_raises(self, svc):
        """Branch: same implementation already registered → DuplicateEntityError"""
        service, conn_repo, _ = svc
        existing = MagicMock()
        existing.connector_implementation = "JIRA"
        conn_repo.list_by_organization = AsyncMock(return_value=[existing])
        from domain.exceptions import DuplicateEntityError
        with pytest.raises(DuplicateEntityError):
            await service.register_connector(uuid4(), "TASK", "JIRA", "Jira", {}, uuid4())

    async def test_register_success(self, svc):
        """Branch: no duplicate → connector created"""
        service, conn_repo, _ = svc
        conn_repo.list_by_organization = AsyncMock(return_value=[])
        saved = MagicMock()
        conn_repo.save = AsyncMock(return_value=saved)
        result = await service.register_connector(
            uuid4(), "TASK", "JIRA", "My Jira", {"token": "x"}, uuid4()
        )
        assert result == saved

    async def test_update_connector_not_found_raises(self, svc):
        """Branch: connector not found → EntityNotFoundError"""
        service, conn_repo, _ = svc
        conn_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import EntityNotFoundError
        with pytest.raises(EntityNotFoundError):
            await service.update_connector(uuid4(), name="new")

    async def test_update_connector_name_only(self, svc):
        """Branch: only name provided → name updated, no re-encrypt"""
        service, conn_repo, _ = svc
        connector = MagicMock()
        connector.organization_id = uuid4()
        conn_repo.get_by_id = AsyncMock(return_value=connector)
        conn_repo.update = AsyncMock(return_value=connector)
        await service.update_connector(uuid4(), name="New Name")
        assert connector.name == "New Name"

    async def test_update_connector_config_re_encrypts(self, svc):
        """Branch: config provided → encrypted_credentials updated"""
        service, conn_repo, _ = svc
        connector = MagicMock()
        connector.organization_id = uuid4()
        conn_repo.get_by_id = AsyncMock(return_value=connector)
        conn_repo.update = AsyncMock(return_value=connector)
        await service.update_connector(uuid4(), config={"new_token": "y"})
        assert connector.encrypted_credentials is not None

    async def test_list_connectors_returns_list(self, svc):
        service, conn_repo, _ = svc
        conn_repo.list_by_organization = AsyncMock(return_value=[])
        result = await service.list_connectors(uuid4())
        assert result == []

    async def test_delete_connector_not_found_raises(self, svc):
        """Branch: connector not found → EntityNotFoundError"""
        service, conn_repo, _ = svc
        conn_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import EntityNotFoundError
        with pytest.raises(EntityNotFoundError):
            await service.delete_connector(uuid4(), uuid4())

    async def test_delete_connector_success(self, svc):
        """Branch: connector found → delete called"""
        service, conn_repo, _ = svc
        conn = MagicMock()
        conn.organization_id = uuid4()
        conn.name = "x"
        conn_repo.get_by_id = AsyncMock(return_value=conn)
        conn_repo.delete = AsyncMock()
        await service.delete_connector(uuid4(), uuid4())
        conn_repo.delete.assert_awaited_once()

    async def test_toggle_connector_not_found_raises(self, svc):
        """Branch: connector not found → EntityNotFoundError"""
        service, conn_repo, _ = svc
        conn_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import EntityNotFoundError
        from domain.enums import ConnectorStatus
        with pytest.raises(EntityNotFoundError):
            await service.toggle_connector_status(uuid4(), ConnectorStatus.INACTIVO, uuid4())

    async def test_toggle_connector_updates_status(self, svc):
        """Branch: connector found → status updated"""
        service, conn_repo, _ = svc
        conn = MagicMock()
        updated = MagicMock()
        conn_repo.get_by_id = AsyncMock(return_value=conn)
        conn_repo.update = AsyncMock(return_value=updated)
        from domain.enums import ConnectorStatus
        result = await service.toggle_connector_status(uuid4(), ConnectorStatus.INACTIVO, uuid4())
        assert conn.status == ConnectorStatus.INACTIVO


# ── TemplateService ───────────────────────────────────────────────────────────

class TestTemplateService:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.template_service import TemplateService
        tmpl_repo = AsyncMock()
        prof_repo = AsyncMock()
        return TemplateService(tmpl_repo, prof_repo), tmpl_repo, prof_repo

    async def test_create_duplicate_name_raises(self, svc):
        """Branch: same name (not archived) exists → DuplicateEntityError"""
        service, tmpl_repo, _ = svc
        existing = MagicMock()
        existing.name = "My Template"
        existing.is_archived = False
        tmpl_repo.list_by_organization = AsyncMock(return_value=[existing])
        from domain.exceptions import DuplicateEntityError
        with pytest.raises(DuplicateEntityError):
            await service.create_template("My Template", "desc", uuid4(), uuid4(), uuid4())

    async def test_create_profile_not_found_raises(self, svc):
        """Branch: profile not found → EntityNotFoundError"""
        service, tmpl_repo, prof_repo = svc
        tmpl_repo.list_by_organization = AsyncMock(return_value=[])
        prof_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import EntityNotFoundError
        with pytest.raises(EntityNotFoundError):
            await service.create_template("name", "desc", uuid4(), uuid4(), uuid4())

    async def test_create_success(self, svc):
        """Branch: no duplicate, profile exists → template created"""
        service, tmpl_repo, prof_repo = svc
        tmpl_repo.list_by_organization = AsyncMock(return_value=[])
        prof_repo.get_by_id = AsyncMock(return_value=MagicMock())
        from domain.entities.template import Template
        t = Template(organization_id=uuid4(), name="n", description="d", profile_id=uuid4(), created_by=uuid4())
        tmpl_repo.create = AsyncMock(return_value=t)
        result = await service.create_template("n", "d", uuid4(), uuid4(), uuid4())
        assert result.name == "n"

    async def test_update_not_found_raises(self, svc):
        """Branch: template not found → EntityNotFoundError"""
        service, tmpl_repo, _ = svc
        tmpl_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import EntityNotFoundError
        with pytest.raises(EntityNotFoundError):
            await service.update_template(uuid4(), name="new")

    async def test_update_partial_fields(self, svc):
        """Branch: name, description, is_archived provided → all updated"""
        service, tmpl_repo, _ = svc
        from domain.entities.template import Template
        t = Template(organization_id=uuid4(), name="old", description="old", profile_id=uuid4(), created_by=uuid4())
        tmpl_repo.get_by_id = AsyncMock(return_value=t)
        tmpl_repo.update = AsyncMock(return_value=t)
        await service.update_template(t.id, name="new", description="new", is_archived=True)
        assert t.name == "new"
        assert t.is_archived is True

    async def test_archive_not_found_raises(self, svc):
        """Branch: template not found → EntityNotFoundError"""
        service, tmpl_repo, _ = svc
        tmpl_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import EntityNotFoundError
        with pytest.raises(EntityNotFoundError):
            await service.archive_template(uuid4())

    async def test_archive_success(self, svc):
        """Branch: template found → is_archived=True"""
        service, tmpl_repo, _ = svc
        from domain.entities.template import Template
        t = Template(organization_id=uuid4(), name="n", description="d", profile_id=uuid4(), created_by=uuid4())
        tmpl_repo.get_by_id = AsyncMock(return_value=t)
        tmpl_repo.update = AsyncMock(return_value=t)
        await service.archive_template(t.id)
        assert t.is_archived is True

    async def test_clone_not_found_raises(self, svc):
        """Branch: original not found → EntityNotFoundError"""
        service, tmpl_repo, _ = svc
        tmpl_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import EntityNotFoundError
        with pytest.raises(EntityNotFoundError):
            await service.clone_template(uuid4(), "new", uuid4(), uuid4())

    async def test_clone_duplicate_target_name_raises(self, svc):
        """Branch: target org already has same name → DuplicateEntityError"""
        service, tmpl_repo, _ = svc
        from domain.entities.template import Template
        original = Template(organization_id=uuid4(), name="n", description="d", profile_id=uuid4(), created_by=uuid4())
        duplicate = Template(organization_id=uuid4(), name="new", description="d", profile_id=uuid4(), created_by=uuid4())
        tmpl_repo.get_by_id = AsyncMock(return_value=original)
        tmpl_repo.list_by_organization = AsyncMock(return_value=[duplicate])
        from domain.exceptions import DuplicateEntityError
        with pytest.raises(DuplicateEntityError):
            await service.clone_template(original.id, "new", uuid4(), uuid4())

    async def test_clone_success(self, svc):
        """Branch: valid clone → new template created"""
        service, tmpl_repo, _ = svc
        from domain.entities.template import Template
        original = Template(organization_id=uuid4(), name="n", description="d", profile_id=uuid4(), created_by=uuid4())
        cloned = Template(organization_id=uuid4(), name="new", description="d", profile_id=uuid4(), created_by=uuid4())
        tmpl_repo.get_by_id = AsyncMock(return_value=original)
        tmpl_repo.list_by_organization = AsyncMock(return_value=[])
        tmpl_repo.create = AsyncMock(return_value=cloned)
        result = await service.clone_template(original.id, "new", uuid4(), uuid4())
        assert result.name == "new"


# ── GetDashboardMetricsUseCase ────────────────────────────────────────────────

class TestDashboardMetrics:
    @pytest.fixture
    def svc(self):
        from application.use_cases.others.get_dashboard_metrics import GetDashboardMetricsUseCase
        rel_repo = AsyncMock()
        ver_repo = AsyncMock()
        return GetDashboardMetricsUseCase(rel_repo, ver_repo), rel_repo, ver_repo

    async def test_no_releases_returns_zero_metrics(self, svc):
        """Branch: no releases → all zeros, pass_rate=0"""
        service, rel_repo, ver_repo = svc
        rel_repo.list_by_organization = AsyncMock(return_value=[])
        result = await service.execute(uuid4())
        assert result.total_releases == 0
        assert result.pass_rate == 0.0

    async def test_mixed_statuses_counted_correctly(self, svc):
        """Branch: VALIDA, NO_VALIDA, PENDIENTE, BORRADOR statuses"""
        service, rel_repo, ver_repo = svc
        from domain.enums import ReleaseStatus, VerdictType
        r1 = _make_release(status=ReleaseStatus.VALIDA)
        r2 = _make_release(status=ReleaseStatus.NO_VALIDA)
        r3 = _make_release(status=ReleaseStatus.PENDIENTE)
        r4 = _make_release(status=ReleaseStatus.BORRADOR)
        rel_repo.list_by_organization = AsyncMock(return_value=[r1, r2, r3, r4])
        result_mock = MagicMock()
        result_mock.verdict = VerdictType.VALID
        ver_repo.find_by_release = AsyncMock(return_value=[result_mock])
        result = await service.execute(uuid4())
        assert result.valid_releases == 1
        assert result.invalid_releases == 1
        assert result.pending_releases == 2
        assert result.total_verifications == 4
        assert result.pass_rate == 100.0

    async def test_pass_rate_calculated_correctly(self, svc):
        """Branch: mixed verdicts → pass_rate < 100"""
        service, rel_repo, ver_repo = svc
        from domain.enums import ReleaseStatus, VerdictType
        rel = _make_release(status=ReleaseStatus.VALIDA)
        rel_repo.list_by_organization = AsyncMock(return_value=[rel])
        valid_r = MagicMock(verdict=VerdictType.VALID)
        invalid_r = MagicMock(verdict=VerdictType.INVALID)
        ver_repo.find_by_release = AsyncMock(return_value=[valid_r, invalid_r])
        result = await service.execute(uuid4())
        assert result.pass_rate == 50.0


# ── RulesService ──────────────────────────────────────────────────────────────

class TestRulesService:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.rules_service import RulesService
        repo = AsyncMock()
        return RulesService(repo), repo

    async def test_reload_rules_success(self, svc):
        """Branch: list_all succeeds → success=True"""
        service, repo = svc
        repo.list_all = AsyncMock(return_value=[MagicMock(), MagicMock()])
        result = await service.reload_custom_rules()
        assert result["success"] is True
        assert result["rules_loaded"] == 2

    async def test_reload_rules_exception_returns_failure(self, svc):
        """Branch: list_all raises → success=False"""
        service, repo = svc
        repo.list_all = AsyncMock(side_effect=Exception("DB error"))
        result = await service.reload_custom_rules()
        assert result["success"] is False
        assert "error" in result["message"].lower() or "Error" in result["message"]


# ── ManageProfileUseCase ──────────────────────────────────────────────────────

class TestManageProfile:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.manage_profile import ManageProfileUseCase
        profile_repo = AsyncMock()
        rule_repo = AsyncMock()
        return ManageProfileUseCase(profile_repo, rule_repo), profile_repo, rule_repo

    async def test_create_profile_not_default(self, svc):
        """Branch: is_default=False → no default check"""
        service, profile_repo, _ = svc
        from domain.entities.verification_profile import VerificationProfile
        p = VerificationProfile(id=uuid4(), organization_id=uuid4(), name="p")
        profile_repo.create = AsyncMock(return_value=p)
        result = await service.create_profile(uuid4(), "name")
        assert result is not None

    async def test_create_profile_default_unsets_existing(self, svc):
        """Branch: is_default=True + existing default → existing unset"""
        service, profile_repo, _ = svc
        from domain.entities.verification_profile import VerificationProfile
        existing = VerificationProfile(id=uuid4(), organization_id=uuid4(), name="old", is_default=True)
        new_p = VerificationProfile(id=uuid4(), organization_id=uuid4(), name="new", is_default=True)
        profile_repo.get_default_for_organization = AsyncMock(return_value=existing)
        profile_repo.update = AsyncMock(return_value=existing)
        profile_repo.create = AsyncMock(return_value=new_p)
        result = await service.create_profile(uuid4(), "new", is_default=True)
        assert existing.is_default is False

    async def test_update_profile_not_found_raises(self, svc):
        """Branch: profile not found → EntityNotFoundError"""
        service, profile_repo, _ = svc
        profile_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import EntityNotFoundError
        with pytest.raises(EntityNotFoundError):
            await service.update_profile(uuid4(), name="new")

    async def test_update_profile_set_default_unsets_existing(self, svc):
        """Branch: is_default=True, current not default → unset existing"""
        service, profile_repo, _ = svc
        from domain.entities.verification_profile import VerificationProfile
        p = VerificationProfile(id=uuid4(), organization_id=uuid4(), name="p", is_default=False)
        existing_default = VerificationProfile(id=uuid4(), organization_id=uuid4(), name="old", is_default=True)
        profile_repo.get_by_id = AsyncMock(return_value=p)
        profile_repo.get_default_for_organization = AsyncMock(return_value=existing_default)
        profile_repo.update = AsyncMock(return_value=p)
        await service.update_profile(p.id, is_default=True)
        assert existing_default.is_default is False

    async def test_duplicate_profile_not_found_raises(self, svc):
        """Branch: original not found → EntityNotFoundError"""
        service, profile_repo, _ = svc
        profile_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import EntityNotFoundError
        with pytest.raises(EntityNotFoundError):
            await service.duplicate_profile(uuid4(), "copy")

    async def test_duplicate_profile_copies_rules(self, svc):
        """Branch: original has rules → rules copied to new profile"""
        service, profile_repo, rule_repo = svc
        from domain.entities.verification_profile import VerificationProfile
        from domain.entities.verification_rule import VerificationRule
        from domain.enums import SeverityType
        rule = VerificationRule(profile_id=uuid4(), rule_template="RV01", severity=SeverityType.HIGH)
        original = VerificationProfile(id=uuid4(), organization_id=uuid4(), name="orig", rules=[rule])
        copy = VerificationProfile(id=uuid4(), organization_id=uuid4(), name="copy")
        profile_repo.get_by_id = AsyncMock(side_effect=[original, copy])
        profile_repo.create = AsyncMock(return_value=copy)
        rule_repo.create = AsyncMock(return_value=rule)
        result = await service.duplicate_profile(original.id, "copy")
        rule_repo.create.assert_awaited_once()

    async def test_delete_profile_not_found_raises(self, svc):
        """Branch: profile not found → EntityNotFoundError"""
        service, profile_repo, _ = svc
        profile_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import EntityNotFoundError
        with pytest.raises(EntityNotFoundError):
            await service.delete_profile(uuid4(), uuid4())

    async def test_delete_profile_success(self, svc):
        """Branch: profile found → delete called"""
        service, profile_repo, _ = svc
        from domain.entities.verification_profile import VerificationProfile
        p = VerificationProfile(id=uuid4(), organization_id=uuid4(), name="p")
        profile_repo.get_by_id = AsyncMock(return_value=p)
        profile_repo.delete = AsyncMock()
        await service.delete_profile(p.id, uuid4())
        profile_repo.delete.assert_awaited_once()

    async def test_add_rule_profile_not_found_raises(self, svc):
        """Branch: profile not found → EntityNotFoundError"""
        service, profile_repo, _ = svc
        profile_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import EntityNotFoundError
        with pytest.raises(EntityNotFoundError):
            await service.add_rule(uuid4(), "RV01")

    async def test_add_rule_success(self, svc):
        """Branch: profile found → rule created"""
        service, profile_repo, rule_repo = svc
        from domain.entities.verification_profile import VerificationProfile
        from domain.entities.verification_rule import VerificationRule
        from domain.enums import SeverityType
        p = VerificationProfile(id=uuid4(), organization_id=uuid4(), name="p")
        rule = VerificationRule(profile_id=p.id, rule_template="RV01", severity=SeverityType.HIGH)
        profile_repo.get_by_id = AsyncMock(return_value=p)
        rule_repo.create = AsyncMock(return_value=rule)
        result = await service.add_rule(p.id, "RV01")
        assert result.rule_template == "RV01"

    async def test_update_rule_not_found_raises(self, svc):
        """Branch: rule not found → EntityNotFoundError"""
        service, _, rule_repo = svc
        rule_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import EntityNotFoundError
        with pytest.raises(EntityNotFoundError):
            await service.update_rule(uuid4())

    async def test_update_rule_all_fields(self, svc):
        """Branch: all optional fields provided → all updated"""
        service, _, rule_repo = svc
        from domain.entities.verification_rule import VerificationRule
        from domain.enums import SeverityType
        rule = VerificationRule(profile_id=uuid4(), rule_template="RV01", severity=SeverityType.HIGH)
        rule_repo.get_by_id = AsyncMock(return_value=rule)
        rule_repo.update = AsyncMock(return_value=rule)
        conn_id = uuid4()
        await service.update_rule(
            rule.id,
            severity=SeverityType.LOW,
            connector_instance_id=conn_id,
            params={"k": "v"},
            display_order=5,
            is_active=False,
        )
        assert rule.severity == SeverityType.LOW
        assert rule.display_order == 5
        assert rule.is_active is False

    async def test_delete_rule_not_found_raises(self, svc):
        """Branch: rule not found → EntityNotFoundError"""
        service, _, rule_repo = svc
        rule_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import EntityNotFoundError
        with pytest.raises(EntityNotFoundError):
            await service.delete_rule(uuid4(), uuid4())

    async def test_reorder_rules_profile_not_found_raises(self, svc):
        """Branch: profile not found → EntityNotFoundError"""
        service, profile_repo, _ = svc
        profile_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import EntityNotFoundError
        with pytest.raises(EntityNotFoundError):
            await service.reorder_rules(uuid4(), [uuid4()])

    async def test_reorder_rules_success(self, svc):
        """Branch: profile found, rules match → display_order updated"""
        service, profile_repo, rule_repo = svc
        from domain.entities.verification_profile import VerificationProfile
        from domain.entities.verification_rule import VerificationRule
        from domain.enums import SeverityType
        p = VerificationProfile(id=uuid4(), organization_id=uuid4(), name="p")
        rule_id = uuid4()
        rule = VerificationRule(profile_id=p.id, rule_template="RV01", severity=SeverityType.HIGH)
        profile_repo.get_by_id = AsyncMock(return_value=p)
        rule_repo.get_by_id = AsyncMock(return_value=rule)
        rule_repo.update = AsyncMock(return_value=rule)
        result = await service.reorder_rules(p.id, [rule_id])
        assert result[0].display_order == 0


# ── AuditLogger ───────────────────────────────────────────────────────────────

class TestAuditLogger:
    def test_log_no_running_loop_does_not_raise(self):
        """Branch: no running asyncio loop (RuntimeError caught) → silent"""
        from core.audit import AuditLogger, AuditEntry, AuditEvent
        logger = AuditLogger()
        entry = AuditEntry(
            event=AuditEvent.LOGIN_SUCCESS,
            user_id=uuid4(),
            organization_id=None,
            resource_type="user",
            resource_id=uuid4(),
        )
        logger.log(entry)

    async def test_log_with_running_loop_schedules_task(self):
        """Branch: running loop → create_task called"""
        from core.audit import AuditLogger, AuditEntry, AuditEvent
        logger = AuditLogger()
        entry = AuditEntry(
            event=AuditEvent.LOGIN_SUCCESS,
            user_id=uuid4(),
            organization_id=uuid4(),
            resource_type="user",
            resource_id=uuid4(),
            ip_address="1.2.3.4",
        )
        logger.log(entry)

    def test_get_instance_singleton(self):
        """Branch: second call returns same instance"""
        from core.audit import AuditLogger
        a = AuditLogger.get_instance()
        b = AuditLogger.get_instance()
        assert a is b


# ── EmailService ──────────────────────────────────────────────────────────────

class TestEmailService:
    async def test_send_activation_email_success(self):
        """Branch: smtp send succeeds → no exception"""
        from core.email import EmailService
        svc = EmailService()
        with patch("core.email._send_smtp") as mock_send:
            mock_send.return_value = None
            with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
                mock_thread.return_value = None
                await svc.send_activation_email("x@x.com", "Test User", "ABC123")
                mock_thread.assert_awaited_once()

    async def test_send_activation_email_failure_raises(self):
        """Branch: smtp raises → exception propagated"""
        from core.email import EmailService
        svc = EmailService()
        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.side_effect = Exception("SMTP failure")
            with pytest.raises(Exception, match="SMTP"):
                await svc.send_activation_email("x@x.com", "Test", "token")

    def test_send_smtp_without_auth(self):
        """Branch: smtp_user empty → no starttls/login"""
        from core.email import _send_smtp
        from unittest.mock import patch as p
        with p("smtplib.SMTP") as mock_smtp_cls:
            mock_ctx = MagicMock()
            mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
            _send_smtp("to@x.com", "subject", "<html>x</html>", "plain")
            mock_ctx.sendmail.assert_called_once()

    def test_send_smtp_with_auth(self):
        """Branch: smtp_user and smtp_password set → starttls + login"""
        from core.email import _send_smtp
        from core import email as email_mod
        with patch.object(email_mod.settings, "smtp_user", "user"), \
             patch.object(email_mod.settings, "smtp_password", "pass"), \
             patch("smtplib.SMTP") as mock_smtp_cls:
            mock_ctx = MagicMock()
            mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
            _send_smtp("to@x.com", "sub", "<html/>", "plain")
            mock_ctx.starttls.assert_called_once()
            mock_ctx.login.assert_called_once()


# ── Logger ────────────────────────────────────────────────────────────────────

class TestLogger:
    def test_configure_root_logger_adds_handler_when_none(self):
        """Branch: root has no handlers → handler added"""
        from core.logger import _configure_root_logger
        root = logging.getLogger()
        original_handlers = root.handlers[:]
        root.handlers.clear()
        _configure_root_logger()
        assert len(root.handlers) >= 1
        root.handlers = original_handlers

    def test_configure_root_logger_skips_when_handler_exists(self):
        """Branch: root already has handlers → no duplicate added"""
        from core.logger import _configure_root_logger
        root = logging.getLogger()
        if not root.handlers:
            root.addHandler(logging.NullHandler())
        count_before = len(root.handlers)
        _configure_root_logger()
        assert len(root.handlers) == count_before

    def test_get_logger_returns_same_instance(self):
        """Branch: same name → cached instance returned"""
        from core.logger import get_logger
        a = get_logger("test.module")
        b = get_logger("test.module")
        assert a is b


# ── CustomRoleService ─────────────────────────────────────────────────────────

class TestCustomRoleService:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.custom_role_service import CustomRoleService
        repo = AsyncMock()
        return CustomRoleService(repo), repo

    async def test_create_duplicate_name_raises(self, svc):
        """Branch: role with same name exists → DuplicateEntityError"""
        service, repo = svc
        from domain.enums import Permission
        existing = MagicMock()
        existing.name = "Admin"
        repo.list_by_organization = AsyncMock(return_value=[existing])
        from domain.exceptions import DuplicateEntityError
        with pytest.raises(DuplicateEntityError):
            await service.create_role(uuid4(), "Admin", [Permission.VIEW_DASHBOARD], uuid4())

    async def test_create_empty_permissions_raises(self, svc):
        """Branch: permissions list is empty → ValidationError"""
        service, repo = svc
        repo.list_by_organization = AsyncMock(return_value=[])
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="permiso"):
            await service.create_role(uuid4(), "NewRole", [], uuid4())

    async def test_create_success(self, svc):
        """Branch: no duplicate, has permissions → role created"""
        service, repo = svc
        from domain.enums import Permission
        from domain.entities.custom_role import CustomRole
        role = CustomRole(id=uuid4(), organization_id=uuid4(), name="NewRole", permissions=[Permission.VIEW_DASHBOARD])
        repo.list_by_organization = AsyncMock(return_value=[])
        repo.create = AsyncMock(return_value=role)
        result = await service.create_role(uuid4(), "NewRole", [Permission.VIEW_DASHBOARD], uuid4())
        assert result.name == "NewRole"

    async def test_get_role(self, svc):
        service, repo = svc
        role = MagicMock()
        repo.get_by_id = AsyncMock(return_value=role)
        result = await service.get_role(uuid4())
        assert result == role

    async def test_list_roles(self, svc):
        service, repo = svc
        repo.list_by_organization = AsyncMock(return_value=[])
        result = await service.list_roles(uuid4())
        assert result == []

    async def test_update_not_found_raises(self, svc):
        """Branch: role not found → EntityNotFoundError"""
        service, repo = svc
        repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import EntityNotFoundError
        with pytest.raises(EntityNotFoundError):
            await service.update_role(uuid4(), name="new")

    async def test_update_empty_permissions_raises(self, svc):
        """Branch: permissions=[] → ValidationError"""
        service, repo = svc
        role = MagicMock()
        repo.get_by_id = AsyncMock(return_value=role)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError):
            await service.update_role(uuid4(), permissions=[])

    async def test_update_all_fields(self, svc):
        """Branch: name, permissions, is_active all provided → all updated"""
        service, repo = svc
        from domain.enums import Permission
        role = MagicMock()
        role.name = "old"
        role.is_active = True
        repo.get_by_id = AsyncMock(return_value=role)
        repo.update = AsyncMock(return_value=role)
        await service.update_role(uuid4(), name="new", permissions=[Permission.VIEW_DASHBOARD], is_active=False)
        assert role.name == "new"
        assert role.is_active is False

    async def test_delete_not_found_raises(self, svc):
        """Branch: role not found → EntityNotFoundError"""
        service, repo = svc
        repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import EntityNotFoundError
        with pytest.raises(EntityNotFoundError):
            await service.delete_role(uuid4(), uuid4())

    async def test_delete_success(self, svc):
        """Branch: role found → delete called"""
        service, repo = svc
        role = MagicMock()
        repo.get_by_id = AsyncMock(return_value=role)
        repo.delete = AsyncMock()
        await service.delete_role(uuid4(), uuid4())
        repo.delete.assert_awaited_once()


# ── VerificationService ───────────────────────────────────────────────────────

class TestVerificationService:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.verification_service import VerificationService
        rel_repo = AsyncMock()
        ver_repo = AsyncMock()
        task_queue = AsyncMock()
        registry = MagicMock()
        return VerificationService(rel_repo, ver_repo, task_queue, registry), rel_repo, ver_repo, task_queue, registry

    async def test_launch_release_not_found_raises(self, svc):
        """Branch: release not found → ValidationError"""
        service, rel_repo, *_ = svc
        rel_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError):
            await service.launch_verification(uuid4(), uuid4())

    async def test_launch_invalid_status_raises(self, svc):
        """Branch: release in EN_VERIFICACION → ValidationError"""
        service, rel_repo, *_ = svc
        from domain.enums import ReleaseStatus
        release = MagicMock()
        release.status = ReleaseStatus.EN_VERIFICACION
        release.artifacts = [MagicMock()]
        rel_repo.get_by_id = AsyncMock(return_value=release)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError):
            await service.launch_verification(uuid4(), uuid4())

    async def test_launch_no_artifacts_raises(self, svc):
        """Branch: no artifacts → ValidationError"""
        service, rel_repo, *_ = svc
        from domain.enums import ReleaseStatus
        release = MagicMock()
        release.status = ReleaseStatus.BORRADOR
        release.artifacts = []
        rel_repo.get_by_id = AsyncMock(return_value=release)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="artefactos"):
            await service.launch_verification(uuid4(), uuid4())

    async def test_launch_success_returns_task_id(self, svc):
        """Branch: valid release with artifacts → task enqueued"""
        service, rel_repo, _, task_queue, _ = svc
        from domain.enums import ReleaseStatus
        release = MagicMock()
        release.status = ReleaseStatus.BORRADOR
        release.artifacts = [MagicMock()]
        rel_repo.get_by_id = AsyncMock(return_value=release)
        rel_repo.update_status = AsyncMock()
        task_queue.enqueue_verification_task = AsyncMock(return_value="task-123")
        result = await service.launch_verification(uuid4(), uuid4())
        assert result == "task-123"

    async def test_fetch_artifacts_no_release(self, svc):
        """Branch: release not found → empty list"""
        service, rel_repo, *_ = svc
        rel_repo.get_by_id = AsyncMock(return_value=None)
        result = await service.fetch_artifacts_via_connectors(uuid4())
        assert result == []

    async def test_fetch_artifacts_no_artifacts(self, svc):
        """Branch: release has no artifacts → empty list"""
        service, rel_repo, *_ = svc
        release = MagicMock()
        release.artifacts = []
        rel_repo.get_by_id = AsyncMock(return_value=release)
        result = await service.fetch_artifacts_via_connectors(uuid4())
        assert result == []

    async def test_fetch_artifacts_connector_exception_silent(self, svc):
        """Branch: connector raises → exception silently caught"""
        service, rel_repo, _, _, registry = svc
        release = MagicMock()
        artifact = MagicMock()
        artifact.connector_implementation = "JIRA"
        release.artifacts = [artifact]
        rel_repo.get_by_id = AsyncMock(return_value=release)
        conn_impl = AsyncMock()
        conn_impl.fetch_artifact = AsyncMock(side_effect=Exception("conn error"))
        registry.get_by_implementation = MagicMock(return_value=conn_impl)
        result = await service.fetch_artifacts_via_connectors(uuid4())
        assert result == []

    async def test_get_verification_result_release_not_found(self, svc):
        """Branch: release not found → ValidationError"""
        service, rel_repo, *_ = svc
        rel_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError):
            await service.get_verification_result(uuid4(), uuid4())

    async def test_get_verification_result_wrong_release(self, svc):
        """Branch: result belongs to different release → ValidationError"""
        service, rel_repo, ver_repo, *_ = svc
        release_id = uuid4()
        release = MagicMock()
        rel_repo.get_by_id = AsyncMock(return_value=release)
        result = MagicMock()
        result.release_id = uuid4()  # different
        ver_repo.find_by_id = AsyncMock(return_value=result)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="pertenece"):
            await service.get_verification_result(release_id, uuid4())

    async def test_get_verification_result_success(self, svc):
        """Branch: result belongs to correct release → return result"""
        service, rel_repo, ver_repo, *_ = svc
        release_id = uuid4()
        release = MagicMock()
        rel_repo.get_by_id = AsyncMock(return_value=release)
        result = MagicMock()
        result.release_id = release_id
        ver_repo.find_by_id = AsyncMock(return_value=result)
        r = await service.get_verification_result(release_id, uuid4())
        assert r == result

    async def test_get_verification_history_release_not_found(self, svc):
        """Branch: release not found → ValidationError"""
        service, rel_repo, *_ = svc
        rel_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError):
            await service.get_verification_history(uuid4())

    async def test_get_latest_verification_no_results(self, svc):
        """Branch: no results → None"""
        service, _, ver_repo, *_ = svc
        ver_repo.find_by_release = AsyncMock(return_value=[])
        result = await service.get_latest_verification(uuid4())
        assert result is None

    async def test_get_latest_verification_returns_first(self, svc):
        """Branch: results exist → first result"""
        service, _, ver_repo, *_ = svc
        r1, r2 = MagicMock(), MagicMock()
        ver_repo.find_by_release = AsyncMock(return_value=[r1, r2])
        result = await service.get_latest_verification(uuid4())
        assert result == r1


# ── ArtifactService ───────────────────────────────────────────────────────────

class TestArtifactService:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.artifact_service import ArtifactService
        art_repo = AsyncMock()
        rel_repo = AsyncMock()
        return ArtifactService(art_repo, rel_repo), art_repo, rel_repo

    async def test_list_release_not_found_raises(self, svc):
        """Branch: release not found → ValidationError"""
        service, _, rel_repo = svc
        rel_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError):
            await service.list_artifacts(uuid4())

    async def test_list_success(self, svc):
        """Branch: release found → artifacts returned"""
        service, art_repo, rel_repo = svc
        rel_repo.get_by_id = AsyncMock(return_value=MagicMock())
        art_repo.find_by_release = AsyncMock(return_value=[])
        result = await service.list_artifacts(uuid4())
        assert result == []

    async def test_add_release_not_found_raises(self, svc):
        """Branch: release not found → ValidationError"""
        service, _, rel_repo = svc
        rel_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import ValidationError
        from domain.enums import ArtifactType
        with pytest.raises(ValidationError):
            await service.add_artifact(uuid4(), uuid4(), "JIRA", ArtifactType.TAREA, "J-1")

    async def test_add_success(self, svc):
        """Branch: release found → artifact saved"""
        service, art_repo, rel_repo = svc
        from domain.enums import ArtifactType
        release = MagicMock()
        rel_repo.get_by_id = AsyncMock(return_value=release)
        artifact = MagicMock()
        art_repo.save = AsyncMock(return_value=artifact)
        result = await service.add_artifact(uuid4(), uuid4(), "JIRA", ArtifactType.TAREA, "J-1")
        assert result == artifact

    async def test_remove_release_not_found_raises(self, svc):
        """Branch: release not found → ValidationError"""
        service, _, rel_repo = svc
        rel_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError):
            await service.remove_artifact(uuid4(), uuid4())

    async def test_remove_artifact_not_found_raises(self, svc):
        """Branch: artifact not found → ValidationError"""
        service, art_repo, rel_repo = svc
        rel_repo.get_by_id = AsyncMock(return_value=MagicMock())
        art_repo.find_by_id = AsyncMock(return_value=None)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="Artifact no encontrado"):
            await service.remove_artifact(uuid4(), uuid4())

    async def test_remove_artifact_wrong_release_raises(self, svc):
        """Branch: artifact belongs to different release → ValidationError"""
        service, art_repo, rel_repo = svc
        release_id = uuid4()
        rel_repo.get_by_id = AsyncMock(return_value=MagicMock())
        artifact = MagicMock()
        artifact.release_id = uuid4()  # different
        art_repo.find_by_id = AsyncMock(return_value=artifact)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="no pertenece"):
            await service.remove_artifact(release_id, uuid4())

    async def test_remove_success(self, svc):
        """Branch: valid artifact → delete called"""
        service, art_repo, rel_repo = svc
        release_id = uuid4()
        artifact_id = uuid4()
        rel_repo.get_by_id = AsyncMock(return_value=MagicMock())
        artifact = MagicMock()
        artifact.release_id = release_id
        art_repo.find_by_id = AsyncMock(return_value=artifact)
        art_repo.delete = AsyncMock()
        await service.remove_artifact(release_id, artifact_id)
        art_repo.delete.assert_awaited_once_with(artifact_id)


# ── ManageProfileGaps ─────────────────────────────────────────────────────────

class TestManageProfileGaps:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.manage_profile import ManageProfileUseCase
        profile_repo = AsyncMock()
        rule_repo = AsyncMock()
        return ManageProfileUseCase(profile_repo, rule_repo), profile_repo, rule_repo

    async def test_update_profile_with_description(self, svc):
        """Branch: update_profile with description not None sets description"""
        service, profile_repo, _ = svc
        from domain.entities.verification_profile import VerificationProfile
        p = VerificationProfile(id=uuid4(), organization_id=uuid4(), name="p", description="old")
        profile_repo.get_by_id = AsyncMock(return_value=p)
        profile_repo.update = AsyncMock(return_value=p)
        result = await service.update_profile(p.id, description="new desc")
        assert result.description == "new desc"

    async def test_get_profile_found(self, svc):
        """Branch: get_profile calls repo.get_by_id and returns profile"""
        service, profile_repo, _ = svc
        from domain.entities.verification_profile import VerificationProfile
        p = VerificationProfile(id=uuid4(), organization_id=uuid4(), name="p")
        profile_repo.get_by_id = AsyncMock(return_value=p)
        result = await service.get_profile(p.id)
        assert result.name == "p"

    async def test_list_profiles(self, svc):
        """Branch: list_profiles calls repo.list_by_organization"""
        service, profile_repo, _ = svc
        from domain.entities.verification_profile import VerificationProfile
        p = VerificationProfile(id=uuid4(), organization_id=uuid4(), name="p")
        profile_repo.list_by_organization = AsyncMock(return_value=[p])
        results = await service.list_profiles(p.organization_id)
        assert len(results) == 1

    async def test_duplicate_profile_re_fetch_fails(self, svc):
        """Branch: duplicate_profile where re-fetch after creation returns None"""
        service, profile_repo, rule_repo = svc
        from domain.entities.verification_profile import VerificationProfile
        original = VerificationProfile(id=uuid4(), organization_id=uuid4(), name="orig", rules=[])
        created = VerificationProfile(id=uuid4(), organization_id=uuid4(), name="copy")
        profile_repo.get_by_id = AsyncMock(side_effect=[original, None])
        profile_repo.create = AsyncMock(return_value=created)
        from domain.exceptions import EntityNotFoundError
        with pytest.raises(EntityNotFoundError):
            await service.duplicate_profile(original.id, "copy")


# ── OrganizationServiceGaps ───────────────────────────────────────────────────

class TestOrganizationServiceGaps:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.organization_service import OrganizationService
        org_repo = AsyncMock()
        project_repo = AsyncMock()
        user_repo = AsyncMock()
        return OrganizationService(org_repo, project_repo, user_repo), org_repo, project_repo, user_repo

    async def test_get_organization(self, svc):
        """Branch: get_organization calls repo.get_by_id"""
        service, org_repo, _, _ = svc
        from domain.entities.organization import Organization
        o = Organization(id=uuid4(), name="org", slug="org-slug")
        org_repo.get_by_id = AsyncMock(return_value=o)
        result = await service.get_organization(o.id)
        assert result.name == "org"

    async def test_list_organizations(self, svc):
        """Branch: list_organizations calls repo.list_all"""
        service, org_repo, _, _ = svc
        from domain.entities.organization import Organization
        o = Organization(id=uuid4(), name="org", slug="org-slug")
        org_repo.list_all = AsyncMock(return_value=[o])
        results = await service.list_organizations()
        assert len(results) == 1

    async def test_list_projects(self, svc):
        """Branch: list_projects calls repo.list_by_organization"""
        service, _, project_repo, _ = svc
        from domain.entities.project import Project
        p = Project(id=uuid4(), name="p", organization_id=uuid4(), description="d", profile_id=uuid4())
        project_repo.list_by_organization = AsyncMock(return_value=[p])
        results = await service.list_projects(p.organization_id)
        assert len(results) == 1

    async def test_get_project(self, svc):
        """Branch: get_project calls repo.get_by_id"""
        service, _, project_repo, _ = svc
        from domain.entities.project import Project
        p = Project(id=uuid4(), name="p", organization_id=uuid4(), description="d", profile_id=uuid4())
        project_repo.get_by_id = AsyncMock(return_value=p)
        result = await service.get_project(p.id)
        assert result.name == "p"

    async def test_list_accessible_projects(self, svc):
        """Branch: list_accessible_projects iterates orgs and aggregates projects"""
        service, org_repo, project_repo, _ = svc
        from domain.entities.organization import Organization
        from domain.entities.project import Project

        org1 = Organization(id=uuid4(), name="o1", slug="o1")
        org2 = Organization(id=uuid4(), name="o2", slug="o2")
        org_repo.list_all = AsyncMock(return_value=[org1, org2])

        p1 = Project(id=uuid4(), name="p1", organization_id=org1.id, description="d", profile_id=uuid4())
        p2 = Project(id=uuid4(), name="p2", organization_id=org2.id, description="d", profile_id=uuid4())
        project_repo.list_by_organization = AsyncMock(side_effect=[[p1], [p2]])

        results = await service.list_accessible_projects(uuid4())
        assert len(results) == 2


# ── TaskServiceGap ────────────────────────────────────────────────────────────

class TestTaskServiceGap:
    async def test_get_task_status(self):
        """Branch: get_task_status calls task_queue.get_task_status"""
        from application.use_cases.main.task_service import TaskService

        queue = AsyncMock()
        queue.get_task_status = AsyncMock(return_value="SUCCESS")
        svc = TaskService(queue)

        result = await svc.get_task_status("task-123")
        assert result == "SUCCESS"


# ── TemplateServiceGaps ───────────────────────────────────────────────────────

class TestTemplateServiceGaps:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.template_service import TemplateService
        template_repo = AsyncMock()
        profile_repo = AsyncMock()
        return TemplateService(template_repo, profile_repo), template_repo, profile_repo

    async def test_get_template_not_found(self, svc):
        """Branch: get_template not found returns None"""
        service, template_repo, _ = svc
        template_repo.get_by_id = AsyncMock(return_value=None)
        result = await service.get_template(uuid4())
        assert result is None


# ── ReleaseServiceGaps ────────────────────────────────────────────────────────

class TestReleaseServiceGaps:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.release_service import CreateReleaseUseCase
        release_repo = AsyncMock()
        project_repo = AsyncMock()
        profile_repo = AsyncMock()
        return CreateReleaseUseCase(release_repo, project_repo, profile_repo), release_repo, project_repo, profile_repo

    async def test_get_release_found(self, svc):
        """Branch: get_release returns release"""
        service, release_repo, _, _ = svc
        from domain.entities.release import Release
        r = Release(
            id=uuid4(), name="r1", version="1.0", project_id=uuid4(),
            profile_id=uuid4(), created_by=uuid4(),
        )
        release_repo.get_by_id = AsyncMock(return_value=r)
        result = await service.get_release(r.id)
        assert result.name == "r1"


# ── UserServiceGaps ───────────────────────────────────────────────────────────

class TestUserServiceGaps:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.user_service import UserService
        user_repo = AsyncMock()
        org_repo = AsyncMock()
        password_hasher = AsyncMock()
        return UserService(user_repo, org_repo, password_hasher), user_repo, org_repo

    async def test_get_user_by_id_found(self, svc):
        """Branch: get_user_by_id returns user"""
        service, user_repo, _ = svc
        from domain.entities.user import User
        from domain.enums import UserRole
        u = User(
            id=uuid4(), email="t@t.com", hashed_password="h",
            display_name="Test", role=UserRole.U2,
        )
        user_repo.get_by_id = AsyncMock(return_value=u)
        result = await service.get_user_by_id(u.id)
        assert result.email == "t@t.com"


# ── ConnectorServiceRemaining ─────────────────────────────────────────────────

class TestConnectorServiceRemaining:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.connector_service import ConnectorService
        connector_repo = AsyncMock()
        connector_registry = MagicMock()
        return ConnectorService(connector_repo, connector_registry), connector_repo, connector_registry

    async def test_list_connectors(self, svc):
        """Branch: list_connectors calls repo.list_by_organization"""
        service, connector_repo, _ = svc
        from domain.entities.connector_instance import ConnectorInstance
        from domain.enums import ConnectorStatus
        c = ConnectorInstance(
            id=uuid4(), name="c1", connector_type="GESTOR_TAREAS",
            connector_implementation="JIRA", organization_id=uuid4(),
            encrypted_credentials=b"enc", status=ConnectorStatus.ACTIVO,
        )
        connector_repo.list_by_organization = AsyncMock(return_value=[c])
        results = await service.list_connectors(c.organization_id)
        assert len(results) == 1

    async def test_get_connector(self, svc):
        """Branch: get_connector calls repo.get_by_id"""
        service, connector_repo, _ = svc
        from domain.entities.connector_instance import ConnectorInstance
        from domain.enums import ConnectorStatus
        c = ConnectorInstance(
            id=uuid4(), name="c1", connector_type="GESTOR_TAREAS",
            connector_implementation="JIRA", organization_id=uuid4(),
            encrypted_credentials=b"enc", status=ConnectorStatus.ACTIVO,
        )
        connector_repo.get_by_id = AsyncMock(return_value=c)
        result = await service.get_connector(c.id)
        assert result.name == "c1"

    async def test_delete_connector(self, svc):
        """Branch: delete_connector found deletes and audits"""
        service, connector_repo, _ = svc
        from domain.entities.connector_instance import ConnectorInstance
        from domain.enums import ConnectorStatus
        c = ConnectorInstance(
            id=uuid4(), name="c1", connector_type="GESTOR_TAREAS",
            connector_implementation="JIRA", organization_id=uuid4(),
            encrypted_credentials=b"enc", status=ConnectorStatus.ACTIVO,
        )
        connector_repo.get_by_id = AsyncMock(return_value=c)
        connector_repo.delete = AsyncMock()
        await service.delete_connector(c.id, uuid4())
        connector_repo.delete.assert_awaited_once()


# ── ReleaseServiceRemaining ───────────────────────────────────────────────────

class TestReleaseServiceRemaining:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.release_service import CreateReleaseUseCase
        release_repo = AsyncMock()
        project_repo = AsyncMock()
        profile_repo = AsyncMock()
        return CreateReleaseUseCase(release_repo, project_repo, profile_repo), release_repo

    async def test_list_releases(self, svc):
        """Branch: list_releases calls repo.list_by_project"""
        service, release_repo = svc
        from domain.entities.release import Release
        r = Release(
            id=uuid4(), name="r1", version="1.0", project_id=uuid4(),
            profile_id=uuid4(), created_by=uuid4(),
        )
        release_repo.list_by_project = AsyncMock(return_value=[r])
        results = await service.list_releases(r.project_id)
        assert len(results) == 1

    async def test_update_status_success(self, svc):
        """Branch: update_status returns updated release"""
        service, release_repo = svc
        from domain.entities.release import Release
        from domain.enums import ReleaseStatus
        r = Release(
            id=uuid4(), name="r1", version="1.0", project_id=uuid4(),
            profile_id=uuid4(), created_by=uuid4(), status=ReleaseStatus.EN_VERIFICACION,
        )
        release_repo.update_status = AsyncMock(return_value=r)
        result = await service.update_status(r.id, ReleaseStatus.VALIDA)
        assert result.status == ReleaseStatus.EN_VERIFICACION

    async def test_list_org_releases(self, svc):
        """Branch: list_org_releases calls repo.list_by_organization"""
        service, release_repo = svc
        from domain.entities.release import Release
        r = Release(
            id=uuid4(), name="r1", version="1.0", project_id=uuid4(),
            profile_id=uuid4(), created_by=uuid4(),
        )
        release_repo.list_by_organization = AsyncMock(return_value=[r])
        results = await service.list_org_releases()
        assert len(results) == 1


# ── VerificationServiceRemaining ─────────────────────────────────────────────

class TestVerificationServiceRemaining:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.verification_service import VerificationService
        release_repo = AsyncMock()
        verification_repo = AsyncMock()
        task_queue = AsyncMock()
        connector_registry = MagicMock()
        return VerificationService(release_repo, verification_repo, task_queue, connector_registry), release_repo, verification_repo

    async def test_get_verification_history_success(self, svc):
        """Branch: get_verification_history with valid release returns results"""
        service, release_repo, verification_repo = svc
        from domain.entities.release import Release
        r = Release(
            id=uuid4(), name="r1", version="1.0", project_id=uuid4(),
            profile_id=uuid4(), created_by=uuid4(),
        )
        release_repo.get_by_id = AsyncMock(return_value=r)
        v_result = MagicMock()
        verification_repo.find_by_release = AsyncMock(return_value=[v_result])
        results = await service.get_verification_history(r.id)
        assert len(results) == 1


# ── ConnectorServiceTestConnection ───────────────────────────────────────────

class TestConnectorServiceTestConnection:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.connector_service import ConnectorService
        connector_repo = AsyncMock()
        connector_registry = MagicMock()
        return ConnectorService(connector_repo, connector_registry), connector_repo, connector_registry

    async def test_test_connection_success(self, svc):
        """Branch: test_connector_connection success path sets ACTIVO"""
        service, connector_repo, connector_registry = svc
        from domain.entities.connector_instance import ConnectorInstance
        from domain.enums import ConnectorStatus
        c = ConnectorInstance(
            id=uuid4(), name="c1", connector_type="GESTOR_TAREAS",
            connector_implementation="JIRA", organization_id=uuid4(),
            encrypted_credentials=b"enc", status=ConnectorStatus.INACTIVO,
        )
        connector_repo.get_by_id = AsyncMock(return_value=c)
        connector_repo.update = AsyncMock(return_value=c)

        mock_impl = MagicMock()
        mock_impl.test_connection = AsyncMock(return_value=True)
        connector_registry.get_by_implementation = MagicMock(return_value=mock_impl)

        with patch("cryptography.fernet.Fernet") as mock_fernet_cls, \
             patch("application.use_cases.main.connector_service.settings") as mock_settings:
            mock_settings.encryption_key = "dummy-key"
            mock_fernet = MagicMock()
            mock_fernet.decrypt = MagicMock(return_value=b"{'key': 'val'}")
            mock_fernet_cls.return_value = mock_fernet

            result = await service.test_connector_connection(c.id, uuid4())

        assert isinstance(result, ConnectorInstance)
        assert result.status == ConnectorStatus.ACTIVO
        assert c.status == ConnectorStatus.ACTIVO
        connector_repo.update.assert_awaited_once()

    async def test_test_connection_failure(self, svc):
        """Branch: test_connector_connection exception sets ERROR and raises"""
        service, connector_repo, connector_registry = svc
        from domain.entities.connector_instance import ConnectorInstance
        from domain.enums import ConnectorStatus
        c = ConnectorInstance(
            id=uuid4(), name="c1", connector_type="GESTOR_TAREAS",
            connector_implementation="JIRA", organization_id=uuid4(),
            encrypted_credentials=b"enc", status=ConnectorStatus.ACTIVO,
        )
        connector_repo.get_by_id = AsyncMock(return_value=c)
        connector_repo.update = AsyncMock()

        mock_impl = MagicMock()
        mock_impl.test_connection = MagicMock(side_effect=Exception("Boom"))
        connector_registry.get_by_implementation = MagicMock(return_value=mock_impl)

        with patch("cryptography.fernet.Fernet") as mock_fernet_cls, \
             patch("application.use_cases.main.connector_service.settings") as mock_settings:
            mock_settings.encryption_key = "dummy-key"
            mock_fernet = MagicMock()
            mock_fernet.decrypt = MagicMock(return_value=b"{'key': 'val'}")
            mock_fernet_cls.return_value = mock_fernet

            from domain.exceptions import ConnectorConnectionFailedError
            with pytest.raises(ConnectorConnectionFailedError):
                await service.test_connector_connection(c.id, uuid4())

        assert c.status == ConnectorStatus.ERROR
        connector_repo.update.assert_awaited_once()

    async def test_test_connection_impl_not_found(self, svc):
        """Branch: test_connector_connection impl not found → ValidationError"""
        service, connector_repo, connector_registry = svc
        from domain.entities.connector_instance import ConnectorInstance
        from domain.enums import ConnectorStatus
        c = ConnectorInstance(
            id=uuid4(), name="c1", connector_type="GESTOR_TAREAS",
            connector_implementation="UNKNOWN", organization_id=uuid4(),
            encrypted_credentials=b"enc", status=ConnectorStatus.ACTIVO,
        )
        connector_repo.get_by_id = AsyncMock(return_value=c)
        connector_registry.get_by_implementation = MagicMock(return_value=None)

        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError):
            await service.test_connector_connection(c.id, uuid4())


# ── UserServiceMoreGaps ───────────────────────────────────────────────────────

class TestUserServiceMoreGaps:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.user_service import UserService
        user_repo = AsyncMock()
        org_repo = AsyncMock()
        from infrastructure.primary.middleware.password_hasher import BcryptPasswordHasher
        password_hasher = BcryptPasswordHasher()
        return UserService(user_repo, org_repo, password_hasher), user_repo, org_repo, password_hasher

    async def test_list_organization_users(self, svc):
        """Branch: list_organization_users calls repo.list_all"""
        service, user_repo, _, _ = svc
        from domain.entities.user import User
        from domain.enums import UserRole
        u = User(id=uuid4(), email="t@t.com", hashed_password="h", display_name="T", role=UserRole.U2)
        user_repo.list_all = AsyncMock(return_value=[u])
        results = await service.list_organization_users(uuid4())
        assert len(results) == 1

    async def test_deactivate_user_not_found(self, svc):
        """Branch: deactivate_user not found raises EntityNotFoundError"""
        service, user_repo, _, _ = svc
        user_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import EntityNotFoundError
        with pytest.raises(EntityNotFoundError):
            await service.deactivate_user(uuid4(), uuid4())

    async def test_deactivate_user_success(self, svc):
        """Branch: deactivate_user found sets is_active=False"""
        service, user_repo, _, _ = svc
        from domain.entities.user import User
        from domain.enums import UserRole
        u = User(id=uuid4(), email="t@t.com", hashed_password="h", display_name="T", role=UserRole.U2, is_active=True)
        user_repo.get_by_id = AsyncMock(return_value=u)
        user_repo.update = AsyncMock(return_value=u)
        result = await service.deactivate_user(u.id, uuid4())
        assert result.is_active is False

    async def test_update_global_role_success(self, svc):
        """Branch: update_global_role found updates role"""
        service, user_repo, _, _ = svc
        from domain.entities.user import User
        from domain.enums import UserRole
        u = User(id=uuid4(), email="t@t.com", hashed_password="h", display_name="T", role=UserRole.U2)
        user_repo.get_by_id = AsyncMock(return_value=u)
        user_repo.update = AsyncMock(return_value=u)
        result = await service.update_global_role(u.id, UserRole.U3, uuid4())
        assert result.role == UserRole.U3


# ── AuthServiceGap ────────────────────────────────────────────────────────────

class TestAuthServiceGap:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.auth_service import AuthService
        user_repo = AsyncMock()
        token_service = MagicMock()
        password_hasher = MagicMock()
        return AuthService(user_repo, token_service, password_hasher), user_repo

    async def test_disable_totp_invalid_code_raises(self, svc):
        """Branch: disable_totp with invalid code -> ValidationError"""
        service, user_repo = svc
        from domain.entities.user import User
        from domain.enums import UserRole
        u = User(
            id=uuid4(), email="t@t.com", hashed_password="h",
            display_name="T", role=UserRole.U2,
            totp_enabled=True, totp_secret="JBSWY3DPEHPK3PXP",
        )
        user_repo.get_by_id = AsyncMock(return_value=u)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError):
            await service.disable_totp(u.id, "000000")


# ── TemplateServiceList ───────────────────────────────────────────────────────

class TestTemplateServiceList:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.template_service import TemplateService
        template_repo = AsyncMock()
        profile_repo = AsyncMock()
        return TemplateService(template_repo, profile_repo), template_repo

    async def test_list_templates_include_archived(self, svc):
        """Branch: list_templates with include_archived=True"""
        service, template_repo = svc
        template_repo.list_by_organization = AsyncMock(return_value=[])
        results = await service.list_templates(uuid4(), include_archived=True)
        assert results == []


# ── ReleaseServiceFinal ───────────────────────────────────────────────────────

class TestReleaseServiceFinal:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.release_service import CreateReleaseUseCase
        release_repo = AsyncMock()
        project_repo = AsyncMock()
        profile_repo = AsyncMock()
        return CreateReleaseUseCase(release_repo, project_repo, profile_repo), release_repo

    async def test_remove_artifact(self, svc):
        """Branch: remove_artifact removes artifact from release and deletes"""
        service, release_repo = svc
        from domain.entities.release import Release
        from domain.entities.artifact import Artifact

        art_id = uuid4()
        artifact = Artifact(
            id=art_id, release_id=uuid4(), connector_instance_id=uuid4(),
            connector_implementation="JIRA", artifact_type="TAREA",
            external_ref="REF-1",
        )
        r = Release(
            id=artifact.release_id, name="r1", version="1.0", project_id=uuid4(),
            profile_id=uuid4(), created_by=uuid4(), artifacts=[artifact],
        )
        release_repo.get_artifact_by_id = AsyncMock(return_value=artifact)
        release_repo.get_by_id = AsyncMock(return_value=r)
        release_repo.update = AsyncMock()
        release_repo.delete_artifact = AsyncMock()

        await service.remove_artifact(art_id)
        release_repo.delete_artifact.assert_awaited_once()

    async def test_list_artifacts(self, svc):
        """Branch: list_artifacts with release found returns sliced list"""
        service, release_repo = svc
        from domain.entities.release import Release
        from domain.entities.artifact import Artifact

        art = Artifact(
            id=uuid4(), release_id=uuid4(), connector_instance_id=uuid4(),
            connector_implementation="JIRA", artifact_type="TAREA",
            external_ref="REF-1",
        )
        r = Release(
            id=uuid4(), name="r1", version="1.0", project_id=uuid4(),
            profile_id=uuid4(), created_by=uuid4(), artifacts=[art],
        )
        release_repo.get_by_id = AsyncMock(return_value=r)
        results = await service.list_artifacts(r.id)
        assert len(results) == 1


# ── ManageApiKeysGap ──────────────────────────────────────────────────────────

class TestManageApiKeysGap:
    @pytest.fixture
    def svc(self):
        from application.use_cases.others.manage_api_keys import ManageApiKeysUseCase
        api_key_repo = AsyncMock()
        return ManageApiKeysUseCase(api_key_repository=api_key_repo), api_key_repo

    async def test_revoke_api_key_not_found(self, svc):
        """Branch: revoke_api_key not found raises EntityNotFoundError"""
        service, api_key_repo = svc
        api_key_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import EntityNotFoundError
        with pytest.raises(EntityNotFoundError):
            await service.revoke_api_key(uuid4(), uuid4())


# ── ProfileServiceWrappers ────────────────────────────────────────────────────

class TestProfileServiceWrappers:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.profile_service import ProfileService
        profile_repo = AsyncMock()
        rule_repo = AsyncMock()
        return ProfileService(profile_repo, rule_repo), profile_repo, rule_repo

    @pytest.fixture(autouse=True)
    def _patch_audit(self):
        with patch("application.use_cases.main.profile_service.get_audit_logger") as mock_audit:
            mock_audit.return_value.log = MagicMock()
            yield

    async def test_create_profile_not_default(self, svc):
        """Branch: ProfileService.create_profile with is_default=False → delegates + audits"""
        service, profile_repo, rule_repo = svc
        from domain.entities.verification_profile import VerificationProfile
        p = VerificationProfile(id=uuid4(), organization_id=uuid4(), name="p")
        profile_repo.create = AsyncMock(return_value=p)
        profile_repo.get_default_for_organization = AsyncMock(return_value=None)

        result = await service.create_profile(uuid4(), "name", is_default=False)
        assert result == p

    async def test_create_profile_default_unsets_existing(self, svc):
        """Branch: ProfileService.create_profile is_default=True, existing default → unset"""
        service, profile_repo, rule_repo = svc
        from domain.entities.verification_profile import VerificationProfile
        existing = VerificationProfile(id=uuid4(), organization_id=uuid4(), name="old", is_default=True)
        new_p = VerificationProfile(id=uuid4(), organization_id=uuid4(), name="new", is_default=True)
        profile_repo.get_default_for_organization = AsyncMock(return_value=existing)
        profile_repo.update = AsyncMock(return_value=existing)
        profile_repo.create = AsyncMock(return_value=new_p)

        result = await service.create_profile(uuid4(), "new", is_default=True)
        assert existing.is_default is False
        assert result == new_p

    async def test_update_profile_success(self, svc):
        """Branch: ProfileService.update_profile → delegates + audits"""
        service, profile_repo, rule_repo = svc
        from domain.entities.verification_profile import VerificationProfile
        p = VerificationProfile(id=uuid4(), organization_id=uuid4(), name="updated-name")
        profile_repo.get_by_id = AsyncMock(return_value=p)
        profile_repo.update = AsyncMock(return_value=p)

        result = await service.update_profile(p.id, name="updated-name")
        assert result.name == "updated-name"

    async def test_duplicate_profile_success(self, svc):
        """Branch: ProfileService.duplicate_profile → delegates"""
        service, profile_repo, rule_repo = svc
        from domain.entities.verification_profile import VerificationProfile
        from domain.entities.verification_rule import VerificationRule
        from domain.enums import SeverityType

        rule = VerificationRule(profile_id=uuid4(), rule_template="RV01", severity=SeverityType.HIGH)
        original = VerificationProfile(id=uuid4(), organization_id=uuid4(), name="orig", rules=[rule])
        copy = VerificationProfile(id=uuid4(), organization_id=uuid4(), name="copy")
        profile_repo.get_by_id = AsyncMock(side_effect=[original, copy])
        profile_repo.create = AsyncMock(return_value=copy)
        rule_repo.create = AsyncMock(return_value=rule)

        result = await service.duplicate_profile(original.id, "copy")
        assert result.name == "copy"

    async def test_delete_profile_success(self, svc):
        """Branch: ProfileService.delete_profile found → deletes + audits"""
        service, profile_repo, rule_repo = svc
        from domain.entities.verification_profile import VerificationProfile
        p = VerificationProfile(id=uuid4(), organization_id=uuid4(), name="p")
        profile_repo.get_by_id = AsyncMock(return_value=p)
        profile_repo.delete = AsyncMock()

        await service.delete_profile(p.id, uuid4())
        profile_repo.delete.assert_awaited_once()

    async def test_delete_profile_not_found_raises(self, svc):
        """Branch: ProfileService.delete_profile not found → EntityNotFoundError"""
        service, profile_repo, rule_repo = svc
        profile_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import EntityNotFoundError
        with pytest.raises(EntityNotFoundError):
            await service.delete_profile(uuid4(), uuid4())

    async def test_add_rule_success(self, svc):
        """Branch: ProfileService.add_rule found → creates + audits"""
        service, profile_repo, rule_repo = svc
        from domain.entities.verification_profile import VerificationProfile
        from domain.entities.verification_rule import VerificationRule
        from domain.enums import SeverityType

        p = VerificationProfile(id=uuid4(), organization_id=uuid4(), name="p")
        rule = VerificationRule(profile_id=p.id, rule_template="RV01", severity=SeverityType.HIGH)
        profile_repo.get_by_id = AsyncMock(return_value=p)
        rule_repo.create = AsyncMock(return_value=rule)

        result = await service.add_rule(p.id, "RV01")
        assert result.rule_template == "RV01"

    async def test_update_rule_success(self, svc):
        """Branch: ProfileService.update_rule → delegates + audits"""
        service, profile_repo, rule_repo = svc
        from domain.entities.verification_rule import VerificationRule
        from domain.entities.verification_profile import VerificationProfile
        from domain.enums import SeverityType

        rule = VerificationRule(profile_id=uuid4(), rule_template="RV01", severity=SeverityType.HIGH)
        profile = VerificationProfile(id=rule.profile_id, organization_id=uuid4(), name="test", is_default=False)
        rule_repo.get_by_id = AsyncMock(return_value=rule)
        rule_repo.update = AsyncMock(return_value=rule)
        profile_repo.get_by_id = AsyncMock(return_value=profile)

        result = await service.update_rule(rule.id, severity=SeverityType.LOW)
        assert result.severity == SeverityType.LOW

    async def test_delete_rule_success(self, svc):
        """Branch: ProfileService.delete_rule → delegates"""
        service, profile_repo, rule_repo = svc
        from domain.entities.verification_rule import VerificationRule
        from domain.entities.verification_profile import VerificationProfile
        from domain.enums import SeverityType

        rule = VerificationRule(profile_id=uuid4(), rule_template="RV01", severity=SeverityType.HIGH)
        profile = VerificationProfile(id=rule.profile_id, organization_id=uuid4(), name="test", is_default=False)
        rule_repo.get_by_id = AsyncMock(return_value=rule)
        rule_repo.delete = AsyncMock()
        profile_repo.get_by_id = AsyncMock(return_value=profile)

        await service.delete_rule(rule.id, uuid4())
        rule_repo.delete.assert_awaited_once()

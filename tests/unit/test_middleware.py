"""
Unit tests for infrastructure/primary/middleware modules.
Covers: rate_limit limiter instantiation and configuration, JWT handler, password hasher.
"""

import os
import sys
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET_KEY", "base-choice-test-secret-key-32-ch!")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXPIRE_MINUTES", "60")
os.environ.setdefault("ALLOWED_ORIGINS", "*")
os.environ.setdefault("ENCRYPTION_KEY", "g7vylajG0IOM0hvMbCNcVWN7G9l1oIF_pHFIj5uO5m8=")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api", "src"))

pytestmark = pytest.mark.unit


class TestRateLimitMiddleware:
    def test_limiter_is_instantiated(self):
        """Branch: rate_limit limiter is a Limiter instance with get_remote_address"""
        from slowapi import Limiter
        from slowapi.util import get_remote_address
        from infrastructure.primary.middleware.rate_limit import limiter

        assert isinstance(limiter, Limiter)
        assert limiter._key_func is get_remote_address  # type: ignore[attr-defined]

    def test_limiter_key_func_uses_client_ip(self):
        """Branch: key_func resolves to get_remote_address"""
        from infrastructure.primary.middleware.rate_limit import limiter

        assert limiter._key_func is not None  # type: ignore[attr-defined]
        assert callable(limiter._key_func)  # type: ignore[attr-defined]


# ── JWT Handler ───────────────────────────────────────────────────────────────

class TestJwtHandler:
    @pytest.fixture
    def handler(self):
        from infrastructure.primary.middleware.jwt_handler import JwtHandler
        return JwtHandler(
            secret=os.environ["JWT_SECRET_KEY"],
            algorithm=os.environ["JWT_ALGORITHM"],
            access_token_expire_minutes=60,
            refresh_token_expire_days=30,
            redis_url=None,
        )

    def test_create_and_decode_access_token(self, handler):
        """Branch: create access token + decode → valid payload"""
        from domain.enums import UserRole
        user_id = uuid4()
        token = handler.create_access_token(
            user_id=user_id, email="x@x.com", role=UserRole.U2, organization_id=uuid4()
        )
        payload = handler.decode_token(token)
        assert str(payload.user_id) == str(user_id)

    def test_create_and_decode_refresh_token(self, handler):
        """Branch: create refresh token → is_refresh_token=True"""
        from domain.enums import UserRole
        token = handler.create_refresh_token(
            user_id=uuid4(), email="x@x.com", role=UserRole.U2, organization_id=uuid4()
        )
        assert handler.is_refresh_token(token) is True

    def test_is_refresh_token_false_for_access(self, handler):
        """Branch: access token → is_refresh_token returns False"""
        from domain.enums import UserRole
        token = handler.create_access_token(
            user_id=uuid4(), email="x@x.com", role=UserRole.U2, organization_id=uuid4()
        )
        assert handler.is_refresh_token(token) is False

    def test_decode_invalid_token_raises(self, handler):
        """Branch: invalid token → ValueError"""
        with pytest.raises(ValueError):
            handler.decode_token("bad.token.here")

    def test_create_totp_pending_token_and_verify(self, handler):
        """Branch: create and verify TOTP pending token"""
        user_id = uuid4()
        token = handler.create_totp_pending_token(user_id)
        result = handler.verify_totp_pending_token(token)
        assert str(result) == str(user_id)

    def test_verify_totp_pending_token_invalid_returns_none(self, handler):
        """Branch: invalid pending token → None"""
        result = handler.verify_totp_pending_token("bad.token")
        assert result is None

    def test_blacklist_token(self, handler):
        """Branch: blacklist_token with no redis → no error"""
        handler.blacklist_token("some-token", 0)

    def test_is_token_blacklisted_no_redis_returns_false(self, handler):
        """Branch: no redis, fresh token → not blacklisted"""
        fresh_token = f"not-blacklisted-{uuid4()}"
        result = handler.is_token_blacklisted(fresh_token)
        assert result is False


# ── Password Hasher ───────────────────────────────────────────────────────────

class TestPasswordHasher:
    def test_hash_and_verify(self):
        """Branch: hash_password + verify_password → True"""
        from infrastructure.primary.middleware.password_hasher import BcryptPasswordHasher
        h = BcryptPasswordHasher()
        hashed = h.hash_password("mypassword")
        assert h.verify_password("mypassword", hashed) is True

    def test_verify_wrong_password_returns_false(self):
        """Branch: wrong password → False"""
        from infrastructure.primary.middleware.password_hasher import BcryptPasswordHasher
        h = BcryptPasswordHasher()
        hashed = h.hash_password("mypassword")
        assert h.verify_password("wrongpassword", hashed) is False

"""
Unit tests for core/email.py
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

pytestmark = pytest.mark.unit


class TestSendFeedbackEmail:
    """Tests for EmailService.send_feedback_email"""

    @pytest.fixture
    def email_service(self):
        import os
        os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
        os.environ.setdefault("ENVIRONMENT", "test")
        os.environ.setdefault("JWT_SECRET_KEY", "base-choice-test-secret-key-32-ch!")
        os.environ.setdefault("JWT_ALGORITHM", "HS256")
        os.environ.setdefault("JWT_EXPIRE_MINUTES", "60")
        os.environ.setdefault("ALLOWED_ORIGINS", "*")
        os.environ.setdefault("ENCRYPTION_KEY", "dMs9Bu4qV9bunZU511boUnNpC0jYXubAfB8a5VPynsE=")
        os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
        os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
        os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
        os.environ.setdefault("ENGINE_URL", "http://localhost:8081")
        os.environ.setdefault("ENGINE_API_KEY", "test-key")
        os.environ.setdefault("ADMIN_EMAIL", "admin@test.local")
        os.environ.setdefault("ADMIN_PASSWORD", "admin-pass")

        from core.email import EmailService
        return EmailService()

    @pytest.mark.asyncio
    async def test_send_feedback_email_success(self, email_service):
        """Test successful feedback email sending"""
        feedback = {
            "name": "Test User",
            "email": "test@example.com",
            "rating": 5,
            "comments": "Great app!"
        }

        with patch("core.email._send_smtp") as mock_smtp:
            await email_service.send_feedback_email(feedback)

            mock_smtp.assert_called_once()
            call_args = mock_smtp.call_args
            assert call_args[0][0] == "admin@test.local"  # to_email
            assert "5/5" in call_args[0][1]  # subject contains rating
            assert "★" in call_args[0][2]  # html contains stars

    @pytest.mark.asyncio
    async def test_send_feedback_email_rating_3(self, email_service):
        """Test feedback email with rating 3 (medium)"""
        feedback = {
            "name": "Test User",
            "email": "test@example.com",
            "rating": 3,
            "comments": "It's okay"
        }

        with patch("core.email._send_smtp") as mock_smtp:
            await email_service.send_feedback_email(feedback)

            call_args = mock_smtp.call_args
            html = call_args[0][2]
            plain = call_args[0][3]
            assert "★★★☆☆" in html or "★★" in html
            assert "Test User" in plain
            assert "It's okay" in plain

    @pytest.mark.asyncio
    async def test_send_feedback_email_no_email(self, email_service):
        """Test feedback email without optional email"""
        feedback = {
            "name": "Anonymous",
            "email": "",
            "rating": 4,
            "comments": "Nice app"
        }

        with patch("core.email._send_smtp") as mock_smtp:
            await email_service.send_feedback_email(feedback)

            call_args = mock_smtp.call_args
            plain = call_args[0][3]
            assert "Anonymous" in plain
            assert "Nice app" in plain

    @pytest.mark.asyncio
    async def test_send_feedback_email_smtp_failure(self, email_service):
        """Test feedback email handles SMTP failure"""
        feedback = {
            "name": "Test",
            "email": "test@test.com",
            "rating": 1,
            "comments": "Bad"
        }

        with patch("core.email._send_smtp", side_effect=Exception("SMTP error")):
            with pytest.raises(Exception, match="SMTP error"):
                await email_service.send_feedback_email(feedback)


class TestSendActivationEmail:
    """Tests for EmailService.send_activation_email"""

    @pytest.fixture
    def email_service(self):
        import os
        os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
        os.environ.setdefault("ENVIRONMENT", "test")
        os.environ.setdefault("JWT_SECRET_KEY", "base-choice-test-secret-key-32-ch!")
        os.environ.setdefault("JWT_ALGORITHM", "HS256")
        os.environ.setdefault("JWT_EXPIRE_MINUTES", "60")
        os.environ.setdefault("ALLOWED_ORIGINS", "*")
        os.environ.setdefault("ENCRYPTION_KEY", "dMs9Bu4qV9bunZU511boUnNpC0jYXubAfB8a5VPynsE=")
        os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
        os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
        os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
        os.environ.setdefault("ENGINE_URL", "http://localhost:8081")
        os.environ.setdefault("ENGINE_API_KEY", "test-key")
        os.environ.setdefault("ADMIN_EMAIL", "admin@test.local")
        os.environ.setdefault("ADMIN_PASSWORD", "admin-pass")

        from core.email import EmailService
        return EmailService()

    @pytest.mark.asyncio
    async def test_send_activation_email_success(self, email_service):
        """Test successful activation email"""
        with patch("core.email._send_smtp") as mock_smtp:
            await email_service.send_activation_email(
                to_email="user@test.com",
                to_name="Test User",
                token="abc123"
            )

            mock_smtp.assert_called_once()
            call_args = mock_smtp.call_args
            assert call_args[0][0] == "user@test.com"
            assert "Activa tu cuenta" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_send_activation_email_smtp_failure(self, email_service):
        """Test activation email handles SMTP failure"""
        with patch("core.email._send_smtp", side_effect=Exception("Connection refused")):
            with pytest.raises(Exception, match="Connection refused"):
                await email_service.send_activation_email(
                    to_email="user@test.com",
                    to_name="Test User",
                    token="abc123"
                )


class TestSendVerificationResultEmail:
    """Tests for EmailService.send_verification_result_email"""

    @pytest.fixture
    def email_service(self):
        import os
        os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
        os.environ.setdefault("ENVIRONMENT", "test")
        os.environ.setdefault("JWT_SECRET_KEY", "base-choice-test-secret-key-32-ch!")
        os.environ.setdefault("JWT_ALGORITHM", "HS256")
        os.environ.setdefault("JWT_EXPIRE_MINUTES", "60")
        os.environ.setdefault("ALLOWED_ORIGINS", "*")
        os.environ.setdefault("ENCRYPTION_KEY", "dMs9Bu4qV9bunZU511boUnNpC0jYXubAfB8a5VPynsE=")
        os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
        os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
        os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
        os.environ.setdefault("ENGINE_URL", "http://localhost:8081")
        os.environ.setdefault("ENGINE_API_KEY", "test-key")
        os.environ.setdefault("ADMIN_EMAIL", "admin@test.local")
        os.environ.setdefault("ADMIN_PASSWORD", "admin-pass")

        from core.email import EmailService
        return EmailService()

    @pytest.mark.asyncio
    async def test_send_verification_result_valid(self, email_service):
        """Test verification result email with VALID verdict"""
        with patch("core.email._send_smtp") as mock_smtp:
            await email_service.send_verification_result_email(
                to_email="user@test.com",
                to_name="Test User",
                release_name="release-1",
                verdict="VALID",
                release_id="rel-123"
            )

            mock_smtp.assert_called_once()
            call_args = mock_smtp.call_args
            assert "release-1" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_send_verification_result_invalid(self, email_service):
        """Test verification result email with INVALID verdict"""
        with patch("core.email._send_smtp") as mock_smtp:
            await email_service.send_verification_result_email(
                to_email="user@test.com",
                to_name="Test User",
                release_name="release-2",
                verdict="INVALID",
                release_id="rel-456"
            )

            mock_smtp.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_verification_result_unknown_verdict(self, email_service):
        """Test verification result email with unknown verdict uses default"""
        with patch("core.email._send_smtp") as mock_smtp:
            await email_service.send_verification_result_email(
                to_email="user@test.com",
                to_name="Test User",
                release_name="release-3",
                verdict="UNKNOWN_VERDICT",
                release_id="rel-789"
            )

            mock_smtp.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_verification_result_smtp_failure_logs_error(self, email_service):
        """Test verification result email logs error on SMTP failure but does not raise"""
        with patch("core.email._send_smtp", side_effect=Exception("SMTP error")):
            # Should not raise, just log
            await email_service.send_verification_result_email(
                to_email="user@test.com",
                to_name="Test User",
                release_name="release-1",
                verdict="VALID",
                release_id="rel-123"
            )


class TestSendPasswordResetEmail:
    """Tests for EmailService.send_password_reset_email"""

    @pytest.fixture
    def email_service(self):
        import os
        os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
        os.environ.setdefault("ENVIRONMENT", "test")
        os.environ.setdefault("JWT_SECRET_KEY", "base-choice-test-secret-key-32-ch!")
        os.environ.setdefault("JWT_ALGORITHM", "HS256")
        os.environ.setdefault("JWT_EXPIRE_MINUTES", "60")
        os.environ.setdefault("ALLOWED_ORIGINS", "*")
        os.environ.setdefault("ENCRYPTION_KEY", "dMs9Bu4qV9bunZU511boUnNpC0jYXubAfB8a5VPynsE=")
        os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
        os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
        os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
        os.environ.setdefault("ENGINE_URL", "http://localhost:8081")
        os.environ.setdefault("ENGINE_API_KEY", "test-key")
        os.environ.setdefault("ADMIN_EMAIL", "admin@test.local")
        os.environ.setdefault("ADMIN_PASSWORD", "admin-pass")

        from core.email import EmailService
        return EmailService()

    @pytest.mark.asyncio
    async def test_send_password_reset_success(self, email_service):
        """Test successful password reset email"""
        with patch("core.email._send_smtp") as mock_smtp:
            await email_service.send_password_reset_email(
                to_email="user@test.com",
                to_name="Test User",
                token="reset-token-123"
            )

            mock_smtp.assert_called_once()
            call_args = mock_smtp.call_args
            assert "Restablece tu contraseña" in call_args[0][1]
            assert "reset-token-123" in call_args[0][2]  # plain text

    @pytest.mark.asyncio
    async def test_send_password_reset_smtp_failure(self, email_service):
        """Test password reset email raises on SMTP failure"""
        with patch("core.email._send_smtp", side_effect=Exception("Connection refused")):
            with pytest.raises(Exception, match="Connection refused"):
                await email_service.send_password_reset_email(
                    to_email="user@test.com",
                    to_name="Test User",
                    token="reset-token"
                )

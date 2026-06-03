"""
Branch-coverage tests for core/bootstrap.py — seed_admin_user.
"""

import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api", "src"))

pytestmark = pytest.mark.unit


class TestSeedAdminUser:
    """Cover every branch inside seed_admin_user."""

    @pytest.fixture
    def settings(self):
        from core.config import Settings
        return Settings(
            admin_email="admin@test.local",
            admin_password="admin-pass",
        )

    async def test_existing_admin_no_org_id_skips_and_logs(self, settings):
        """Branch: admin already exists, org_id is None → skip seed"""
        from core.bootstrap import seed_admin_user
        from infrastructure.secondary.database.models.user_model import UserModel
        from domain.enums import UserRole

        existing = UserModel(
            id=uuid4(),
            email=settings.admin_email,
            hashed_password="hashed",
            display_name="Admin",
            role=UserRole.U3.value,
            organization_id=None,
            is_active=True,
        )

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=existing)))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with patch("core.bootstrap.AsyncSessionLocal", return_value=mock_session):
            await seed_admin_user(settings)

        mock_session.commit.assert_not_awaited()

    async def test_existing_admin_with_org_id_strips_it(self, settings):
        """Branch: admin exists but has organization_id → strip it"""
        from core.bootstrap import seed_admin_user
        from infrastructure.secondary.database.models.user_model import UserModel
        from domain.enums import UserRole

        existing = UserModel(
            id=uuid4(),
            email=settings.admin_email,
            hashed_password="hashed",
            display_name="Admin",
            role=UserRole.U3.value,
            organization_id=uuid4(),
            is_active=True,
        )

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=existing)))
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with patch("core.bootstrap.AsyncSessionLocal", return_value=mock_session):
            await seed_admin_user(settings)

        assert existing.organization_id is None
        mock_session.commit.assert_awaited_once()

    async def test_email_already_taken_by_other_user_skips(self, settings):
        """Branch: no admin role user, but email taken by another → skip"""
        from core.bootstrap import seed_admin_user
        from infrastructure.secondary.database.models.user_model import UserModel
        from domain.enums import UserRole

        other_user = UserModel(
            id=uuid4(),
            email=settings.admin_email,
            hashed_password="hashed",
            display_name="Regular",
            role=UserRole.U2.value,
            is_active=True,
        )

        call_count = 0
        async def side_effect(stmt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return MagicMock(scalar_one_or_none=MagicMock(return_value=None))
            else:
                return MagicMock(scalar_one_or_none=MagicMock(return_value=other_user))

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=side_effect)
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with patch("core.bootstrap.AsyncSessionLocal", return_value=mock_session):
            await seed_admin_user(settings)

        mock_session.add.assert_not_called()

    async def test_no_admin_creates_successfully(self, settings):
        """Branch: no existing admin, email free → seed new admin"""
        from core.bootstrap import seed_admin_user

        call_count = 0
        async def side_effect(stmt):
            nonlocal call_count
            call_count += 1
            return MagicMock(scalar_one_or_none=MagicMock(return_value=None))

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=side_effect)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with patch("core.bootstrap.AsyncSessionLocal", return_value=mock_session):
            await seed_admin_user(settings)

        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()
        mock_session.refresh.assert_awaited_once()

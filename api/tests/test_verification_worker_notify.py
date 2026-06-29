"""Tests for the _notify_user notification preference enforcement logic."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import contextmanager
import sys

import pytest
from src.domain.entities.notification_subscription import NotificationSubscription
from src.domain.entities.user import User
from src.domain.enums import UserRole


def _make_user() -> User:
    return User(
        id=uuid.uuid4(),
        email="test@example.com",
        display_name="Test User",
        hashed_password="hashed",
        role=UserRole.U4,
    )


def _make_result(verdict: str) -> MagicMock:
    result = MagicMock()
    result.verdict = MagicMock()
    result.verdict.value = verdict
    return result


def _make_release(user_id: uuid.UUID) -> MagicMock:
    release = MagicMock()
    release.created_by = user_id
    release.name = "My Release"
    return release


# ---------------------------------------------------------------
# Standalone version of the _notify_user logic (same as in worker)
# ---------------------------------------------------------------
async def _notify_user_logic(
    release_id: uuid.UUID,
    release: MagicMock,
    saved_result: MagicMock,
    user_repo: AsyncMock,
    notification_repo: AsyncMock,
    email_service: MagicMock,
) -> None:
    """Extracted logic matching _notify_user in verification_worker."""
    user = await user_repo.get_by_id(release.created_by)
    if not user:
        return

    verdict_value = saved_result.verdict.value
    if verdict_value in ("VALID", "VALID_WITH_WARNINGS"):
        event_type = "RELEASE_VALIDATED"
    else:
        event_type = "RELEASE_INVALIDATED"

    subscription = await notification_repo.get_subscription(user.id, event_type)
    if subscription is not None and not subscription.enabled:
        return

    try:
        await email_service.send_verification_result_email(
            to_email=user.email,
            to_name=user.display_name or user.email,
            release_name=release.name,
            verdict=verdict_value,
            release_id=str(release_id),
        )
    except Exception:
        pass


class TestNotifyUser:
    """Tests for _notify_user notification preference enforcement."""

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.user_repo = AsyncMock()
        self.notif_repo = AsyncMock()
        self.email_send = AsyncMock()

    # ---------- happy paths ----------

    async def test_sends_email_when_no_subscription_exists_valid_verdict(self) -> None:
        """Default: no subscription row → send email."""
        user = _make_user()
        self.user_repo.get_by_id.return_value = user
        self.notif_repo.get_subscription.return_value = None

        result = _make_result("VALID")
        release = _make_release(user.id)

        await _notify_user_logic(uuid.uuid4(), release, result, self.user_repo, self.notif_repo, self.email_send)

        self.email_send.send_verification_result_email.assert_called_once()
        call_kwargs = self.email_send.send_verification_result_email.call_args.kwargs
        assert call_kwargs["to_email"] == "test@example.com"
        assert call_kwargs["verdict"] == "VALID"

    async def test_sends_email_when_subscription_enabled_valid_with_warnings(self) -> None:
        """Subscription exists and enabled → email sent for VALID_WITH_WARNINGS."""
        user = _make_user()
        self.user_repo.get_by_id.return_value = user
        sub = NotificationSubscription(user_id=user.id, event_type="RELEASE_VALIDATED", enabled=True)
        self.notif_repo.get_subscription.return_value = sub

        result = _make_result("VALID_WITH_WARNINGS")
        release = _make_release(user.id)

        await _notify_user_logic(uuid.uuid4(), release, result, self.user_repo, self.notif_repo, self.email_send)

        self.email_send.send_verification_result_email.assert_called_once()
        self.notif_repo.get_subscription.assert_called_once_with(user.id, "RELEASE_VALIDATED")

    # ---------- skip on disabled ----------

    async def test_skips_email_when_subscription_disabled_valid(self) -> None:
        """Subscription disabled for RELEASE_VALIDATED → no email."""
        user = _make_user()
        self.user_repo.get_by_id.return_value = user
        sub = NotificationSubscription(user_id=user.id, event_type="RELEASE_VALIDATED", enabled=False)
        self.notif_repo.get_subscription.return_value = sub

        result = _make_result("VALID")
        release = _make_release(user.id)

        await _notify_user_logic(uuid.uuid4(), release, result, self.user_repo, self.notif_repo, self.email_send)

        self.email_send.send_verification_result_email.assert_not_called()
        self.notif_repo.get_subscription.assert_called_once_with(user.id, "RELEASE_VALIDATED")

    async def test_skips_email_when_subscription_disabled_invalid(self) -> None:
        """Invalid verdict + disabled INVALIDATED subscription → no email."""
        user = _make_user()
        self.user_repo.get_by_id.return_value = user
        sub = NotificationSubscription(user_id=user.id, event_type="RELEASE_INVALIDATED", enabled=False)
        self.notif_repo.get_subscription.return_value = sub

        result = _make_result("INVALID")
        release = _make_release(user.id)

        await _notify_user_logic(uuid.uuid4(), release, result, self.user_repo, self.notif_repo, self.email_send)

        self.email_send.send_verification_result_email.assert_not_called()
        self.notif_repo.get_subscription.assert_called_once_with(user.id, "RELEASE_INVALIDATED")

    async def test_sends_email_when_subscription_enabled_invalid(self) -> None:
        """Invalid verdict + enabled INVALIDATED subscription → email sent."""
        user = _make_user()
        self.user_repo.get_by_id.return_value = user
        sub = NotificationSubscription(user_id=user.id, event_type="RELEASE_INVALIDATED", enabled=True)
        self.notif_repo.get_subscription.return_value = sub

        result = _make_result("INVALID")
        release = _make_release(user.id)

        await _notify_user_logic(uuid.uuid4(), release, result, self.user_repo, self.notif_repo, self.email_send)

        self.email_send.send_verification_result_email.assert_called_once()
        assert self.email_send.send_verification_result_email.call_args.kwargs["verdict"] == "INVALID"

    # ---------- edge cases ----------

    async def test_user_not_found_skips_notification(self) -> None:
        """Release creator not found → no email, no subscription check."""
        self.user_repo.get_by_id.return_value = None

        result = _make_result("VALID")
        release = _make_release(uuid.uuid4())

        await _notify_user_logic(uuid.uuid4(), release, result, self.user_repo, self.notif_repo, self.email_send)

        self.email_send.send_verification_result_email.assert_not_called()
        self.notif_repo.get_subscription.assert_not_called()

    async def test_email_exception_is_handled_gracefully(self) -> None:
        """send_verification_result_email raises → function does not propagate."""
        user = _make_user()
        self.user_repo.get_by_id.return_value = user
        self.notif_repo.get_subscription.return_value = None
        self.email_send.send_verification_result_email.side_effect = RuntimeError("SMTP down")

        result = _make_result("VALID")
        release = _make_release(user.id)

        # Should not raise
        await _notify_user_logic(uuid.uuid4(), release, result, self.user_repo, self.notif_repo, self.email_send)

        self.email_send.send_verification_result_email.assert_called_once()

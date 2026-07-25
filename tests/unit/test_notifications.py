"""
Unit tests for infrastructure.secondary.notifications package
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

pytestmark = pytest.mark.unit


class TestNotificationsInit:
    """Tests for the notifications __init__.py re-exports."""

    def test_init_exports_send_outbound_notification(self):
        """__init__ should expose send_outbound_notification."""
        from infrastructure.secondary.notifications import send_outbound_notification
        assert callable(send_outbound_notification)


class TestSlackPayload:
    """Tests for _slack_payload formatter."""

    def test_slack_payload_basic(self):
        from infrastructure.secondary.notifications.outbound_webhook_sender import _slack_payload

        ctx = {
            "release_name": "MyRelease",
            "version": "1.0.0",
            "project_name": "MyProject",
            "verdict": "VALID",
        }
        payload = _slack_payload("RELEASE_VALIDATED", ctx)
        assert "text" in payload
        assert "MyRelease" in payload["text"]
        assert "1.0.0" in payload["text"]
        assert "MyProject" in payload["text"]
        assert "VALID" in payload["text"]

    def test_slack_payload_with_url(self):
        from infrastructure.secondary.notifications.outbound_webhook_sender import _slack_payload

        ctx = {"release_name": "R", "version": "2.0", "verdict": "NO_VALIDA", "release_url": "https://example.com/r"}
        payload = _slack_payload("RELEASE_INVALIDATED", ctx)
        assert "https://example.com/r" in payload["text"]

    def test_slack_payload_minimal(self):
        from infrastructure.secondary.notifications.outbound_webhook_sender import _slack_payload

        ctx = {"release_name": "R", "version": "1", "verdict": "UNKNOWN"}
        payload = _slack_payload("UNKNOWN_EVENT", ctx)
        assert "RELEASE_INVALIDATED" not in payload["text"]
        assert "UNKNOWN_EVENT" in payload["text"]


class TestTeamsPayload:
    """Tests for _teams_payload formatter."""

    def test_teams_payload_basic(self):
        from infrastructure.secondary.notifications.outbound_webhook_sender import _teams_payload

        ctx = {"release_name": "R", "version": "1.0", "verdict": "VALID", "project_name": "P"}
        payload = _teams_payload("RELEASE_VALIDATED", ctx)
        assert payload["@type"] == "MessageCard"
        assert "facts" in payload["sections"][0]

    def test_teams_payload_with_url(self):
        from infrastructure.secondary.notifications.outbound_webhook_sender import _teams_payload

        ctx = {"release_name": "R", "version": "1.0", "verdict": "VALID", "release_url": "https://example.com"}
        payload = _teams_payload("RELEASE_VALIDATED", ctx)
        assert "potentialAction" in payload
        assert payload["potentialAction"][0]["targets"][0]["uri"] == "https://example.com"

    def test_teams_payload_theme_color(self):
        from infrastructure.secondary.notifications.outbound_webhook_sender import _teams_payload

        ctx = {"release_name": "R", "version": "1", "verdict": "NOK"}
        payload_valid = _teams_payload("RELEASE_VALIDATED", ctx)
        payload_invalid = _teams_payload("RELEASE_INVALIDATED", ctx)
        payload_drift = _teams_payload("DRIFT_DETECTED", ctx)
        assert payload_valid["themeColor"] == "22c55e"
        assert payload_invalid["themeColor"] == "ef4444"
        assert payload_drift["themeColor"] == "f59e0b"


class TestGenericPayload:
    """Tests for _generic_payload formatter."""

    def test_generic_payload(self):
        from infrastructure.secondary.notifications.outbound_webhook_sender import _generic_payload

        ctx = {"release_name": "R", "version": "1.0"}
        payload = _generic_payload("RELEASE_VALIDATED", ctx)
        assert payload["event"] == "RELEASE_VALIDATED"
        assert payload["release_name"] == "R"
        assert payload["version"] == "1.0"


class TestSign:
    """Tests for _sign helper."""

    def test_sign_returns_sha256_prefix(self):
        from infrastructure.secondary.notifications.outbound_webhook_sender import _sign

        result = _sign("secret", b"body")
        assert result.startswith("sha256=")
        assert len(result) > len("sha256=")

    def test_sign_is_deterministic(self):
        from infrastructure.secondary.notifications.outbound_webhook_sender import _sign

        r1 = _sign("secret", b"body")
        r2 = _sign("secret", b"body")
        assert r1 == r2

    def test_sign_differs_with_different_secret(self):
        from infrastructure.secondary.notifications.outbound_webhook_sender import _sign

        r1 = _sign("secretA", b"body")
        r2 = _sign("secretB", b"body")
        assert r1 != r2


class TestBuildPayload:
    """Tests for _build_payload dispatcher."""

    def test_build_slack(self):
        from infrastructure.secondary.notifications.outbound_webhook_sender import _build_payload

        ctx = {"release_name": "R", "version": "1", "verdict": "OK"}
        payload = _build_payload("SLACK", "RELEASE_VALIDATED", ctx)
        assert "text" in payload

    def test_build_teams(self):
        from infrastructure.secondary.notifications.outbound_webhook_sender import _build_payload

        ctx = {"release_name": "R", "version": "1", "verdict": "OK"}
        payload = _build_payload("MS_TEAMS", "RELEASE_VALIDATED", ctx)
        assert payload["@type"] == "MessageCard"

    def test_build_generic(self):
        from infrastructure.secondary.notifications.outbound_webhook_sender import _build_payload

        ctx = {"release_name": "R", "version": "1"}
        payload = _build_payload("GENERIC", "RELEASE_VALIDATED", ctx)
        assert payload["event"] == "RELEASE_VALIDATED"


class TestSendOutboundNotification:
    """Tests for send_outbound_notification."""

    def _mock_channel(self, channel_type="SLACK", webhook_url="https://hooks.example.com/webhook", signing_secret=None):
        channel = MagicMock()
        channel.channel_type = channel_type
        channel.config_data = {"webhook_url": webhook_url}
        if signing_secret:
            channel.config_data["signing_secret"] = signing_secret
        return channel

    def _make_ctx(self, **overrides):
        ctx = {
            "release_name": "test-release",
            "version": "1.0.0",
            "verdict": "VALID",
        }
        ctx.update(overrides)
        return ctx

    def test_skips_when_no_url(self):
        from infrastructure.secondary.notifications.outbound_webhook_sender import send_outbound_notification

        channel = MagicMock()
        channel.config_data = {}
        channel.channel_type = "SLACK"

        result = asyncio.run(send_outbound_notification(channel, "RELEASE_VALIDATED", self._make_ctx()))
        assert result is False

    @pytest.mark.asyncio
    async def test_skips_when_no_webhook_url_config_key(self):
        from infrastructure.secondary.notifications.outbound_webhook_sender import send_outbound_notification

        channel = MagicMock()
        channel.config_data = {"url": None}
        channel.channel_type = "SLACK"

        result = await send_outbound_notification(channel, "RELEASE_VALIDATED", self._make_ctx())
        assert result is False

    @pytest.mark.asyncio
    async def test_sends_slack_notification(self):
        from infrastructure.secondary.notifications.outbound_webhook_sender import send_outbound_notification

        channel = self._mock_channel("SLACK", "https://hooks.example.com/slack")
        ctx = self._make_ctx()

        with patch("infrastructure.secondary.notifications.outbound_webhook_sender.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=MagicMock(raise_for_status=MagicMock())
            )
            result = await send_outbound_notification(channel, "RELEASE_VALIDATED", ctx)
            assert result is True

    @pytest.mark.asyncio
    async def test_sends_teams_notification(self):
        from infrastructure.secondary.notifications.outbound_webhook_sender import send_outbound_notification

        channel = self._mock_channel("MS_TEAMS", "https://hooks.example.com/teams")
        ctx = self._make_ctx()

        with patch("infrastructure.secondary.notifications.outbound_webhook_sender.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=MagicMock(raise_for_status=MagicMock())
            )
            result = await send_outbound_notification(channel, "RELEASE_VALIDATED", ctx)
            assert result is True

    @pytest.mark.asyncio
    async def test_adds_signature_header_for_generic_with_secret(self):
        from infrastructure.secondary.notifications.outbound_webhook_sender import send_outbound_notification

        channel = self._mock_channel("GENERIC", "https://hooks.example.com/generic", signing_secret="my-secret")
        ctx = self._make_ctx()

        with patch("infrastructure.secondary.notifications.outbound_webhook_sender.httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=MagicMock(raise_for_status=MagicMock()))
            mock_client.return_value.__aenter__.return_value.post = mock_post
            result = await send_outbound_notification(channel, "RELEASE_VALIDATED", ctx)
            assert result is True
            call_kwargs = mock_post.call_args.kwargs
            assert "X-SVAES-Signature" in call_kwargs["headers"]

    @pytest.mark.asyncio
    async def test_no_signature_for_slack(self):
        from infrastructure.secondary.notifications.outbound_webhook_sender import send_outbound_notification

        channel = self._mock_channel("SLACK", "https://hooks.example.com/slack", signing_secret="ignored")
        ctx = self._make_ctx()

        with patch("infrastructure.secondary.notifications.outbound_webhook_sender.httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=MagicMock(raise_for_status=MagicMock()))
            mock_client.return_value.__aenter__.return_value.post = mock_post
            result = await send_outbound_notification(channel, "RELEASE_VALIDATED", ctx)
            assert result is True
            call_kwargs = mock_post.call_args.kwargs
            assert "X-SVAES-Signature" not in call_kwargs["headers"]

    @pytest.mark.asyncio
    async def test_returns_false_on_blocked_url(self):
        from infrastructure.secondary.notifications.outbound_webhook_sender import send_outbound_notification

        channel = self._mock_channel("SLACK", "file:///etc/passwd")
        ctx = self._make_ctx()

        result = await send_outbound_notification(channel, "RELEASE_VALIDATED", ctx)
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_http_error(self):
        from infrastructure.secondary.notifications.outbound_webhook_sender import send_outbound_notification

        channel = self._mock_channel("SLACK", "https://hooks.example.com/slack")
        ctx = self._make_ctx()

        with patch("infrastructure.secondary.notifications.outbound_webhook_sender.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=MagicMock(raise_for_status=MagicMock(side_effect=Exception("HTTP 500")))
            )
            result = await send_outbound_notification(channel, "RELEASE_VALIDATED", ctx)
            assert result is False

    @pytest.mark.asyncio
    async def test_drift_detected_event(self):
        from infrastructure.secondary.notifications.outbound_webhook_sender import send_outbound_notification

        channel = self._mock_channel("SLACK", "https://hooks.example.com/slack")
        ctx = self._make_ctx()

        with patch("infrastructure.secondary.notifications.outbound_webhook_sender.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=MagicMock(raise_for_status=MagicMock())
            )
            result = await send_outbound_notification(channel, "DRIFT_DETECTED", ctx)
            assert result is True

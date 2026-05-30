import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi.testclient import TestClient

from main import app
from core.dependencies import (
    CurrentUser,
    get_current_user,
    require_permission,
    get_notification_service,
    get_user_repository,
)
from domain.enums import UserRole, Permission
from domain.exceptions import EntityNotFoundError, ValidationError

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_notification_service():
    svc = AsyncMock()
    svc.list_channels = AsyncMock(return_value=[])
    svc.configure_channel = AsyncMock()
    svc.update_channel = AsyncMock()
    svc.delete_channel = AsyncMock()
    svc.get_user_preferences = AsyncMock(
        return_value={
            "release_validated": True,
            "release_invalidated": True,
            "release_pending_reminder": False,
            "weekly_digest": True,
        }
    )
    svc.update_user_preferences = AsyncMock(return_value={})
    svc.subscribe = AsyncMock()
    svc.unsubscribe = AsyncMock()
    return svc


@pytest.fixture
def mock_user_repo():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def test_user():
    return CurrentUser(
        user_id=uuid4(),
        role=UserRole.U4,
        email="manager@test.com",
        organization_id=uuid4(),
    )


@pytest.fixture
def test_app(mock_notification_service, mock_user_repo, test_user):
    app.dependency_overrides[get_notification_service] = lambda: mock_notification_service
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[require_permission(Permission.MANAGE_PROFILES)] = lambda: test_user
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repo

    @asynccontextmanager
    async def _test_lifespan(app):
        yield

    app.router.lifespan_context = _test_lifespan

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


class TestListNotificationChannels:
    def test_list_channels_success(self, test_app, mock_notification_service):
        mock_notification_service.list_channels.return_value = [
            {"channel_type": "EMAIL", "enabled": True, "configured": True}
        ]
        response = test_app.get("/api/v1/notifications/channels")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestConfigureNotificationChannel:
    def test_configure_channel_success(self, test_app, mock_notification_service):
        from unittest.mock import MagicMock
        channel = MagicMock()
        channel.id = uuid4()
        channel.channel_type = "EMAIL"
        channel.enabled = True
        mock_notification_service.configure_channel.return_value = channel

        response = test_app.post("/api/v1/notifications/channels", json={
            "channel_type": "EMAIL",
            "enabled": True,
            "config_data": {"host": "smtp.test.com"},
        })
        assert response.status_code == 201
        assert "id" in response.json()

    def test_configure_channel_conflict(self, test_app, mock_notification_service):
        mock_notification_service.configure_channel.side_effect = ValidationError("Tipo no soportado")
        response = test_app.post("/api/v1/notifications/channels", json={
            "channel_type": "INVALID",
            "enabled": True,
            "config_data": {},
        })
        assert response.status_code == 409


class TestUpdateNotificationChannel:
    def test_update_channel_success(self, test_app, mock_notification_service):
        from unittest.mock import MagicMock
        channel = MagicMock()
        mock_notification_service.update_channel.return_value = channel

        response = test_app.patch(f"/api/v1/notifications/channels/{uuid4()}", json={
            "channel_type": "EMAIL",
            "enabled": False,
            "config_data": {},
        })
        assert response.status_code == 200

    def test_update_channel_not_found(self, test_app, mock_notification_service):
        mock_notification_service.update_channel.side_effect = EntityNotFoundError("Canal no encontrado")
        response = test_app.patch(f"/api/v1/notifications/channels/{uuid4()}", json={
            "channel_type": "EMAIL",
            "enabled": True,
            "config_data": {},
        })
        assert response.status_code == 404


class TestDeleteNotificationChannel:
    def test_delete_channel_success(self, test_app, mock_notification_service):
        response = test_app.delete(f"/api/v1/notifications/channels/{uuid4()}")
        assert response.status_code == 204

    def test_delete_channel_not_found(self, test_app, mock_notification_service):
        mock_notification_service.delete_channel.side_effect = EntityNotFoundError("Canal no encontrado")
        response = test_app.delete(f"/api/v1/notifications/channels/{uuid4()}")
        assert response.status_code == 404


class TestNotificationPreferences:
    def test_get_preferences_success(self, test_app, mock_notification_service):
        response = test_app.get("/api/v1/notifications/preferences")
        assert response.status_code == 200
        data = response.json()
        assert "release_validated" in data

    def test_update_preferences_success(self, test_app, mock_notification_service):
        mock_notification_service.update_user_preferences.return_value = {
            "release_validated": False,
            "release_invalidated": True,
            "release_pending_reminder": True,
            "weekly_digest": False,
        }
        response = test_app.patch("/api/v1/notifications/preferences", json={
            "release_validated": False,
            "release_invalidated": True,
            "release_pending_reminder": True,
            "weekly_digest": False,
        })
        assert response.status_code == 200


class TestSubscriptions:
    def test_subscribe_success(self, test_app, mock_notification_service):
        from unittest.mock import MagicMock
        sub = MagicMock()
        sub.id = uuid4()
        sub.user_id = uuid4()
        sub.event_type = "RELEASE_VALIDATED"
        sub.enabled = True
        sub.created_at = datetime.now(timezone.utc)
        mock_notification_service.subscribe.return_value = sub

        response = test_app.post("/api/v1/notifications/subscriptions", json={
            "event_type": "RELEASE_VALIDATED",
            "enabled": True,
        })
        assert response.status_code == 201

    def test_subscribe_conflict(self, test_app, mock_notification_service):
        mock_notification_service.subscribe.side_effect = ValidationError("Evento no soportado")
        response = test_app.post("/api/v1/notifications/subscriptions", json={
            "event_type": "INVALID",
            "enabled": True,
        })
        assert response.status_code == 409

    def test_unsubscribe_success(self, test_app, mock_notification_service):
        response = test_app.delete("/api/v1/notifications/subscriptions/RELEASE_VALIDATED")
        assert response.status_code == 204

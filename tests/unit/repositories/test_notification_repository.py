import pytest
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from domain.entities.notification_channel import NotificationChannel
from domain.entities.notification_subscription import NotificationSubscription

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    session.get = AsyncMock(return_value=None)
    session.execute = AsyncMock()
    return session


@pytest.fixture
def repo(mock_session):
    @asynccontextmanager
    async def _scope():
        yield mock_session

    with patch(
        "infrastructure.secondary.database.repositories.notification_repository._session_scope",
        new=_scope,
    ):
        from infrastructure.secondary.database.repositories.notification_repository import (
            SqlNotificationRepository,
        )
        yield SqlNotificationRepository()


class TestChannelOperations:
    async def test_create_channel_success(self, repo, mock_session):
        channel = NotificationChannel(
            id=uuid4(),
            organization_id=uuid4(),
            channel_type="EMAIL",
            enabled=True,
            config_data={"host": "smtp.test.com"},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        result = await repo.create_channel(channel)
        assert result is not None
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    async def test_list_channels_returns_channels(self, repo, mock_session):
        row = MagicMock()
        row.id = uuid4()
        row.organization_id = uuid4()
        row.channel_type = "EMAIL"
        row.enabled = True
        row.config_data = {}
        row.created_at = datetime.now(timezone.utc)
        row.updated_at = datetime.now(timezone.utc)

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [row]
        mock_session.execute.return_value = result_mock

        channels = await repo.list_channels(uuid4())
        assert len(channels) == 1

    async def test_get_channel_by_id_returns_channel(self, repo, mock_session):
        row = MagicMock()
        row.id = uuid4()
        row.organization_id = uuid4()
        row.channel_type = "SLACK"
        row.enabled = True
        row.config_data = {}
        row.created_at = datetime.now(timezone.utc)
        row.updated_at = datetime.now(timezone.utc)

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = row
        mock_session.execute.return_value = result_mock

        channel = await repo.get_channel_by_id(uuid4())
        assert channel is not None

    async def test_get_channel_by_id_returns_none(self, repo, mock_session):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result_mock

        channel = await repo.get_channel_by_id(uuid4())
        assert channel is None

    async def test_update_channel_success(self, repo, mock_session):
        channel_id = uuid4()
        model = MagicMock()
        model.id = channel_id
        mock_session.get.return_value = model

        channel = NotificationChannel(
            id=channel_id,
            organization_id=uuid4(),
            channel_type="EMAIL",
            enabled=False,
            config_data={"host": "new.host"},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        result = await repo.update_channel(channel)
        assert result is not None
        mock_session.commit.assert_called_once()

    async def test_update_channel_not_found(self, repo, mock_session):
        mock_session.get.return_value = None
        channel = NotificationChannel(
            id=uuid4(),
            organization_id=uuid4(),
            channel_type="EMAIL",
            enabled=True,
            config_data={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        with pytest.raises(ValueError, match="Notification channel not found"):
            await repo.update_channel(channel)

    async def test_delete_channel_success(self, repo, mock_session):
        model = MagicMock()
        mock_session.get.return_value = model

        await repo.delete_channel(uuid4())

        mock_session.delete.assert_called_once_with(model)
        mock_session.commit.assert_called_once()

    async def test_delete_channel_not_found(self, repo, mock_session):
        mock_session.get.return_value = None

        with pytest.raises(ValueError, match="Notification channel not found"):
            await repo.delete_channel(uuid4())


class TestSubscriptionOperations:
    async def test_list_subscriptions(self, repo, mock_session):
        row = MagicMock()
        row.id = uuid4()
        row.user_id = uuid4()
        row.event_type = "RELEASE_VALIDATED"
        row.enabled = True
        row.created_at = datetime.now(timezone.utc)
        row.updated_at = datetime.now(timezone.utc)

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [row]
        mock_session.execute.return_value = result_mock

        subs = await repo.list_subscriptions(uuid4())
        assert len(subs) == 1

    async def test_get_subscription_returns_subscription(self, repo, mock_session):
        row = MagicMock()
        row.id = uuid4()
        row.user_id = uuid4()
        row.event_type = "WEEKLY_DIGEST"
        row.enabled = True
        row.created_at = datetime.now(timezone.utc)
        row.updated_at = datetime.now(timezone.utc)

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = row
        mock_session.execute.return_value = result_mock

        sub = await repo.get_subscription(uuid4(), "WEEKLY_DIGEST")
        assert sub is not None

    async def test_get_subscription_returns_none(self, repo, mock_session):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result_mock

        sub = await repo.get_subscription(uuid4(), "RELEASE_VALIDATED")
        assert sub is None

    async def test_upsert_subscription_creates_new(self, repo, mock_session):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result_mock

        subscription = NotificationSubscription(
            id=uuid4(),
            user_id=uuid4(),
            event_type="RELEASE_VALIDATED",
            enabled=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        result = await repo.upsert_subscription(subscription)
        assert result is not None
        mock_session.add.assert_called_once()

    async def test_upsert_subscription_updates_existing(self, repo, mock_session):
        existing = MagicMock()
        existing.id = uuid4()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = existing
        mock_session.execute.return_value = result_mock

        subscription = NotificationSubscription(
            id=uuid4(),
            user_id=uuid4(),
            event_type="WEEKLY_DIGEST",
            enabled=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        result = await repo.upsert_subscription(subscription)
        assert result is not None
        assert existing.enabled is True

    async def test_delete_subscription_success(self, repo, mock_session):
        model = MagicMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = model
        mock_session.execute.return_value = result_mock

        await repo.delete_subscription(uuid4(), "RELEASE_VALIDATED")

        mock_session.delete.assert_called_once_with(model)
        mock_session.commit.assert_called_once()

    async def test_delete_subscription_no_match(self, repo, mock_session):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result_mock

        await repo.delete_subscription(uuid4(), "UNKNOWN")

        mock_session.delete.assert_not_called()

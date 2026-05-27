import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
from datetime import datetime, timezone

from application.use_cases.main.notification_service import NotificationService
from domain.entities.notification_channel import NotificationChannel
from domain.entities.notification_subscription import NotificationSubscription
from domain.exceptions import EntityNotFoundError, ValidationError


@pytest.fixture
def mock_notification_repo():
    repo = AsyncMock()
    repo.list_channels = AsyncMock(return_value=[])
    repo.create_channel = AsyncMock()
    repo.get_channel_by_id = AsyncMock(return_value=None)
    repo.update_channel = AsyncMock()
    repo.delete_channel = AsyncMock()
    repo.list_subscriptions = AsyncMock(return_value=[])
    repo.upsert_subscription = AsyncMock()
    repo.delete_subscription = AsyncMock()
    return repo


@pytest.fixture
def mock_audit_logger():
    logger = MagicMock()
    logger.log = MagicMock()
    return logger


@pytest.fixture
def service(mock_notification_repo, mock_audit_logger):
    with patch(
        "application.use_cases.main.notification_service.get_audit_logger",
        return_value=mock_audit_logger,
    ):
        yield NotificationService(mock_notification_repo)


pytestmark = pytest.mark.unit


class TestListChannels:
    async def test_list_channels_all_configured(self, service, mock_notification_repo):
        """Verifica que se listen todos los tipos de canal con estado configurado cuando existen en el repositorio."""
        org_id = uuid4()
        email_channel = MagicMock()
        email_channel.id = uuid4()
        email_channel.organization_id = org_id
        email_channel.channel_type = "EMAIL"
        email_channel.enabled = True
        email_channel.config_data = {"smtp_host": "localhost"}
        email_channel.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
        email_channel.updated_at = datetime(2025, 1, 2, tzinfo=timezone.utc)

        slack_channel = MagicMock()
        slack_channel.id = uuid4()
        slack_channel.organization_id = org_id
        slack_channel.channel_type = "SLACK"
        slack_channel.enabled = False
        slack_channel.config_data = {"webhook_url": "https://hooks.slack/xxx"}
        slack_channel.created_at = datetime(2025, 2, 1, tzinfo=timezone.utc)
        slack_channel.updated_at = datetime(2025, 2, 2, tzinfo=timezone.utc)

        teams_channel = MagicMock()
        teams_channel.id = uuid4()
        teams_channel.organization_id = org_id
        teams_channel.channel_type = "MS_TEAMS"
        teams_channel.enabled = True
        teams_channel.config_data = {"webhook_url": "https://teams/xxx"}
        teams_channel.created_at = datetime(2025, 3, 1, tzinfo=timezone.utc)
        teams_channel.updated_at = datetime(2025, 3, 2, tzinfo=timezone.utc)

        mock_notification_repo.list_channels.return_value = [
            email_channel, slack_channel, teams_channel
        ]

        result = await service.list_channels(org_id)

        assert len(result) == 3
        for item in result:
            assert item["configured"] is True
            assert item["enabled"] is not None
            assert item["id"] is not None
            assert item["created_at"] is not None
            assert item["updated_at"] is not None
        mock_notification_repo.list_channels.assert_called_once_with(org_id)

    async def test_list_channels_all_unconfigured(self, service, mock_notification_repo):
        """Verifica que se listen todos los tipos de canal con estado no configurado cuando no existen en el repositorio."""
        org_id = uuid4()
        mock_notification_repo.list_channels.return_value = []

        result = await service.list_channels(org_id)

        assert len(result) == 3
        for item in result:
            assert item["configured"] is False
            assert item["enabled"] is False
            assert item["id"] is None
            assert item["config_data"] == {}
            assert item["created_at"] is None
            assert item["updated_at"] is None
            assert item["organization_id"] == str(org_id)

        channel_types = {item["channel_type"] for item in result}
        assert channel_types == {"EMAIL", "SLACK", "MS_TEAMS"}

    async def test_list_channels_mixed_configured(self, service, mock_notification_repo):
        """Verifica que se listen canales configurados y no configurados correctamente en una misma llamada."""
        org_id = uuid4()
        email_channel = MagicMock()
        email_channel.id = uuid4()
        email_channel.organization_id = org_id
        email_channel.channel_type = "EMAIL"
        email_channel.enabled = True
        email_channel.config_data = {}
        email_channel.created_at = datetime.now(timezone.utc)
        email_channel.updated_at = datetime.now(timezone.utc)

        mock_notification_repo.list_channels.return_value = [email_channel]

        result = await service.list_channels(org_id)

        assert len(result) == 3
        configured_items = [item for item in result if item["configured"]]
        unconfigured_items = [item for item in result if not item["configured"]]
        assert len(configured_items) == 1
        assert configured_items[0]["channel_type"] == "EMAIL"
        assert len(unconfigured_items) == 2


class TestConfigureChannel:
    async def test_configure_channel_success(self, service, mock_notification_repo, mock_audit_logger):
        """Verifica la creación exitosa de un canal de notificación con datos completos."""
        org_id = uuid4()
        config_data = {"smtp_host": "smtp.example.com", "port": 587}

        mock_notification_repo.create_channel.return_value = MagicMock(
            id=uuid4(),
            spec=NotificationChannel,
        )

        result = await service.configure_channel(
            organization_id=org_id,
            channel_type="EMAIL",
            enabled=True,
            config_data=config_data,
        )

        mock_notification_repo.create_channel.assert_called_once()
        mock_audit_logger.log.assert_called_once()
        assert result is not None

    async def test_configure_channel_unsupported_type(self, service, mock_notification_repo):
        """Verifica que se lance ValidationError al configurar un tipo de canal no soportado."""
        org_id = uuid4()
        with pytest.raises(ValidationError, match="no soportado"):
            await service.configure_channel(
                organization_id=org_id,
                channel_type="DISCORD",
                enabled=True,
                config_data={},
            )
        mock_notification_repo.create_channel.assert_not_called()

    async def test_configure_channel_slack_type(self, service, mock_notification_repo, mock_audit_logger):
        """Verifica la creación exitosa de un canal SLACK con datos de configuración."""
        org_id = uuid4()
        config_data = {"webhook_url": "https://hooks.slack.com/services/xxx"}

        mock_notification_repo.create_channel.return_value = MagicMock(
            id=uuid4(),
            spec=NotificationChannel,
        )

        result = await service.configure_channel(
            organization_id=org_id,
            channel_type="SLACK",
            enabled=True,
            config_data=config_data,
        )

        mock_notification_repo.create_channel.assert_called_once()
        mock_audit_logger.log.assert_called_once()
        assert result is not None

    async def test_configure_channel_ms_teams_type(self, service, mock_notification_repo, mock_audit_logger):
        """Verifica la creación exitosa de un canal MS_TEAMS con datos de configuración."""
        org_id = uuid4()
        config_data = {"webhook_url": "https://outlook.office.com/webhook/xxx"}

        mock_notification_repo.create_channel.return_value = MagicMock(
            id=uuid4(),
            spec=NotificationChannel,
        )

        result = await service.configure_channel(
            organization_id=org_id,
            channel_type="MS_TEAMS",
            enabled=False,
            config_data=config_data,
        )

        mock_notification_repo.create_channel.assert_called_once()
        mock_audit_logger.log.assert_called_once()
        assert result is not None

    async def test_configure_channel_empty_config(self, service, mock_notification_repo, mock_audit_logger):
        """Verifica la creación exitosa de un canal con configuración vacía."""
        org_id = uuid4()

        mock_notification_repo.create_channel.return_value = MagicMock(
            id=uuid4(),
            spec=NotificationChannel,
        )

        result = await service.configure_channel(
            organization_id=org_id,
            channel_type="EMAIL",
            enabled=False,
            config_data={},
        )

        mock_notification_repo.create_channel.assert_called_once()
        assert result is not None


class TestUpdateChannel:
    async def test_update_channel_enabled_success(self, service, mock_notification_repo, mock_audit_logger):
        """Verifica la actualización exitosa del campo enabled de un canal."""
        channel_id = uuid4()
        channel = MagicMock()
        channel.id = channel_id
        channel.organization_id = uuid4()
        channel.channel_type = "EMAIL"
        channel.enabled = True
        channel.config_data = {}

        mock_notification_repo.get_channel_by_id.return_value = channel
        mock_notification_repo.update_channel.return_value = channel

        result = await service.update_channel(
            channel_id=channel_id,
            enabled=False,
        )

        assert channel.enabled is False
        mock_notification_repo.update_channel.assert_called_once_with(channel)
        mock_audit_logger.log.assert_called_once()
        assert result is not None

    async def test_update_channel_config_data_success(self, service, mock_notification_repo, mock_audit_logger):
        """Verifica la actualización exitosa del campo config_data de un canal."""
        channel_id = uuid4()
        channel = MagicMock()
        channel.id = channel_id
        channel.organization_id = uuid4()
        channel.channel_type = "SLACK"
        channel.enabled = True
        channel.config_data = {"old": "data"}

        mock_notification_repo.get_channel_by_id.return_value = channel
        mock_notification_repo.update_channel.return_value = channel

        new_config = {"webhook_url": "https://new.example.com"}
        result = await service.update_channel(
            channel_id=channel_id,
            config_data=new_config,
        )

        assert channel.config_data == new_config
        mock_notification_repo.update_channel.assert_called_once_with(channel)
        assert result is not None

    async def test_update_channel_both_fields(self, service, mock_notification_repo, mock_audit_logger):
        """Verifica la actualización exitosa de ambos campos enabled y config_data simultáneamente."""
        channel_id = uuid4()
        channel = MagicMock()
        channel.id = channel_id
        channel.organization_id = uuid4()
        channel.channel_type = "EMAIL"
        channel.enabled = False
        channel.config_data = {}

        mock_notification_repo.get_channel_by_id.return_value = channel
        mock_notification_repo.update_channel.return_value = channel

        new_config = {"host": "smtp.new.com"}
        result = await service.update_channel(
            channel_id=channel_id,
            enabled=True,
            config_data=new_config,
        )

        assert channel.enabled is True
        assert channel.config_data == new_config
        mock_notification_repo.update_channel.assert_called_once_with(channel)
        mock_audit_logger.log.assert_called_once()
        assert result is not None

    async def test_update_channel_no_changes(self, service, mock_notification_repo, mock_audit_logger):
        """Verifica que se pueda llamar a update_channel sin modificar ningún campo."""
        channel_id = uuid4()
        channel = MagicMock()
        channel.id = channel_id
        channel.organization_id = uuid4()
        channel.channel_type = "EMAIL"
        channel.enabled = True
        channel.config_data = {"host": "smtp.test.com"}
        original_enabled = channel.enabled
        original_config = channel.config_data

        mock_notification_repo.get_channel_by_id.return_value = channel
        mock_notification_repo.update_channel.return_value = channel

        result = await service.update_channel(channel_id=channel_id)

        assert channel.enabled == original_enabled
        assert channel.config_data == original_config
        mock_notification_repo.update_channel.assert_called_once_with(channel)
        mock_audit_logger.log.assert_called_once()
        assert result is not None

    async def test_update_channel_not_found(self, service, mock_notification_repo):
        """Verifica que se lance EntityNotFoundError al intentar actualizar un canal inexistente."""
        channel_id = uuid4()
        mock_notification_repo.get_channel_by_id.return_value = None

        with pytest.raises(EntityNotFoundError, match="no encontrado"):
            await service.update_channel(
                channel_id=channel_id,
                enabled=True,
            )

        mock_notification_repo.update_channel.assert_not_called()

    async def test_update_channel_only_enabled_unchanged(self, service, mock_notification_repo):
        """Verifica que el canal no se modifique si enabled ya tenía el mismo valor."""
        channel_id = uuid4()
        channel = MagicMock()
        channel.id = channel_id
        channel.organization_id = uuid4()
        channel.channel_type = "SLACK"
        channel.enabled = True

        mock_notification_repo.get_channel_by_id.return_value = channel
        mock_notification_repo.update_channel.return_value = channel

        result = await service.update_channel(
            channel_id=channel_id,
            enabled=True,
        )

        assert channel.enabled is True
        mock_notification_repo.update_channel.assert_called_once()
        assert result is not None


class TestDeleteChannel:
    async def test_delete_channel_success(self, service, mock_notification_repo, mock_audit_logger):
        """Verifica la eliminación exitosa de un canal de notificación existente."""
        channel_id = uuid4()
        channel = MagicMock()
        channel.id = channel_id
        channel.organization_id = uuid4()
        channel.channel_type = "EMAIL"

        mock_notification_repo.get_channel_by_id.return_value = channel

        await service.delete_channel(channel_id)

        mock_notification_repo.delete_channel.assert_called_once_with(channel_id)
        mock_audit_logger.log.assert_called_once()

    async def test_delete_channel_not_found(self, service, mock_notification_repo):
        """Verifica que se lance EntityNotFoundError al eliminar un canal inexistente."""
        channel_id = uuid4()
        mock_notification_repo.get_channel_by_id.return_value = None

        with pytest.raises(EntityNotFoundError, match="no encontrado"):
            await service.delete_channel(channel_id)

        mock_notification_repo.delete_channel.assert_not_called()

    async def test_delete_channel_ms_teams_type(self, service, mock_notification_repo, mock_audit_logger):
        """Verifica la eliminación exitosa de un canal de tipo MS_TEAMS."""
        channel_id = uuid4()
        channel = MagicMock()
        channel.id = channel_id
        channel.organization_id = uuid4()
        channel.channel_type = "MS_TEAMS"

        mock_notification_repo.get_channel_by_id.return_value = channel

        await service.delete_channel(channel_id)

        mock_notification_repo.delete_channel.assert_called_once_with(channel_id)
        mock_audit_logger.log.assert_called_once()


class TestGetUserPreferences:
    async def test_get_user_preferences_defaults(self, service, mock_notification_repo):
        """Verifica que se retornen las preferencias por defecto cuando el usuario no tiene subscripciones."""
        user_id = uuid4()
        mock_notification_repo.list_subscriptions.return_value = []

        result = await service.get_user_preferences(user_id)

        assert result == {
            "release_validated": True,
            "release_invalidated": True,
            "release_pending_reminder": False,
            "weekly_digest": True,
        }
        mock_notification_repo.list_subscriptions.assert_called_once_with(user_id)

    async def test_get_user_preferences_with_subscriptions(self, service, mock_notification_repo):
        """Verifica que las subscripciones existentes sobrescriban los valores por defecto correctamente."""
        user_id = uuid4()

        sub1 = MagicMock()
        sub1.event_type = "RELEASE_VALIDATED"
        sub1.enabled = False

        sub2 = MagicMock()
        sub2.event_type = "WEEKLY_DIGEST"
        sub2.enabled = False

        mock_notification_repo.list_subscriptions.return_value = [sub1, sub2]

        result = await service.get_user_preferences(user_id)

        assert result["release_validated"] is False
        assert result["release_invalidated"] is True
        assert result["release_pending_reminder"] is False
        assert result["weekly_digest"] is False

    async def test_get_user_preferences_ignores_unknown_event_types(self, service, mock_notification_repo):
        """Verifica que las subscripciones con tipos de evento desconocidos sean ignoradas."""
        user_id = uuid4()

        sub = MagicMock()
        sub.event_type = "UNKNOWN_EVENT"
        sub.enabled = True

        mock_notification_repo.list_subscriptions.return_value = [sub]

        result = await service.get_user_preferences(user_id)

        assert result == {
            "release_validated": True,
            "release_invalidated": True,
            "release_pending_reminder": False,
            "weekly_digest": True,
        }

    async def test_get_user_preferences_partial_overrides(self, service, mock_notification_repo):
        """Verifica que solo se sobrescriban las preferencias que tienen subscripción y el resto conserven sus defaults."""
        user_id = uuid4()

        sub = MagicMock()
        sub.event_type = "RELEASE_PENDING"
        sub.enabled = True

        mock_notification_repo.list_subscriptions.return_value = [sub]

        result = await service.get_user_preferences(user_id)

        assert result["release_validated"] is True
        assert result["release_invalidated"] is True
        assert result["release_pending_reminder"] is True
        assert result["weekly_digest"] is True


class TestUpdateUserPreferences:
    async def test_update_all_preferences(self, service, mock_notification_repo):
        """Verifica la actualización exitosa de todas las preferencias del usuario."""
        user_id = uuid4()

        mock_notification_repo.upsert_subscription.return_value = MagicMock()
        mock_notification_repo.list_subscriptions.return_value = []

        result = await service.update_user_preferences(
            user_id=user_id,
            release_validated=False,
            release_invalidated=False,
            release_pending_reminder=True,
            weekly_digest=False,
        )

        assert mock_notification_repo.upsert_subscription.call_count == 4
        assert result is not None

    async def test_update_partial_preferences(self, service, mock_notification_repo):
        """Verifica que solo se actualicen los campos proporcionados, ignorando los None."""
        user_id = uuid4()

        mock_notification_repo.upsert_subscription.return_value = MagicMock()
        mock_notification_repo.list_subscriptions.return_value = []

        result = await service.update_user_preferences(
            user_id=user_id,
            release_validated=False,
        )

        assert mock_notification_repo.upsert_subscription.call_count == 1
        assert result is not None

    async def test_update_single_preference_false(self, service, mock_notification_repo):
        """Verifica la actualización de una sola preferencia a False."""
        user_id = uuid4()

        mock_notification_repo.upsert_subscription.return_value = MagicMock()
        mock_notification_repo.list_subscriptions.return_value = []

        result = await service.update_user_preferences(
            user_id=user_id,
            weekly_digest=False,
        )

        assert mock_notification_repo.upsert_subscription.call_count == 1
        upserted_sub = mock_notification_repo.upsert_subscription.call_args[0][0]
        assert upserted_sub.event_type == "WEEKLY_DIGEST"
        assert upserted_sub.enabled is False
        assert result is not None

    async def test_update_no_preferences(self, service, mock_notification_repo):
        """Verifica que al no pasar ninguna preferencia no se realicen upserts."""
        user_id = uuid4()

        mock_notification_repo.list_subscriptions.return_value = []

        result = await service.update_user_preferences(user_id=user_id)

        mock_notification_repo.upsert_subscription.assert_not_called()
        assert result is not None

    async def test_update_preferences_returns_current_state(self, service, mock_notification_repo):
        """Verifica que update_user_preferences retorne las preferencias actualizadas correctamente."""
        user_id = uuid4()

        sub = MagicMock()
        sub.event_type = "RELEASE_VALIDATED"
        sub.enabled = False

        mock_notification_repo.upsert_subscription.return_value = MagicMock()
        mock_notification_repo.list_subscriptions.return_value = [sub]

        result = await service.update_user_preferences(
            user_id=user_id,
            release_validated=False,
        )

        assert result["release_validated"] is False
        assert result["release_invalidated"] is True


class TestSubscribe:
    async def test_subscribe_success(self, service, mock_notification_repo, mock_audit_logger):
        """Verifica la subscripción exitosa a un evento soportado."""
        user_id = uuid4()
        created_sub = MagicMock()
        created_sub.id = uuid4()
        created_sub.user_id = user_id
        created_sub.event_type = "RELEASE_VALIDATED"
        created_sub.enabled = True
        created_sub.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)

        mock_notification_repo.upsert_subscription.return_value = created_sub

        result = await service.subscribe(
            user_id=user_id,
            event_type="RELEASE_VALIDATED",
            enabled=True,
        )

        assert result["event_type"] == "RELEASE_VALIDATED"
        assert result["enabled"] is True
        assert result["user_id"] == str(user_id)
        assert "created_at" in result
        mock_notification_repo.upsert_subscription.assert_called_once()
        mock_audit_logger.log.assert_called_once()

    async def test_subscribe_unsupported_event_type(self, service, mock_notification_repo):
        """Verifica que se lance ValidationError al suscribirse a un tipo de evento no soportado."""
        user_id = uuid4()
        with pytest.raises(ValidationError, match="no soportado"):
            await service.subscribe(
                user_id=user_id,
                event_type="INVALID_EVENT",
            )
        mock_notification_repo.upsert_subscription.assert_not_called()

    async def test_subscribe_disabled(self, service, mock_notification_repo, mock_audit_logger):
        """Verifica la subscripción exitosa con enabled=False para desactivar notificaciones."""
        user_id = uuid4()
        created_sub = MagicMock()
        created_sub.id = uuid4()
        created_sub.user_id = user_id
        created_sub.event_type = "WEEKLY_DIGEST"
        created_sub.enabled = False
        created_sub.created_at = datetime.now(timezone.utc)

        mock_notification_repo.upsert_subscription.return_value = created_sub

        result = await service.subscribe(
            user_id=user_id,
            event_type="WEEKLY_DIGEST",
            enabled=False,
        )

        assert result["enabled"] is False
        mock_notification_repo.upsert_subscription.assert_called_once()
        mock_audit_logger.log.assert_called_once()

    async def test_subscribe_release_invalidated(self, service, mock_notification_repo, mock_audit_logger):
        """Verifica la subscripción exitosa al evento RELEASE_INVALIDATED."""
        user_id = uuid4()
        created_sub = MagicMock()
        created_sub.id = uuid4()
        created_sub.user_id = user_id
        created_sub.event_type = "RELEASE_INVALIDATED"
        created_sub.enabled = True
        created_sub.created_at = datetime.now(timezone.utc)

        mock_notification_repo.upsert_subscription.return_value = created_sub

        result = await service.subscribe(
            user_id=user_id,
            event_type="RELEASE_INVALIDATED",
        )

        assert result["event_type"] == "RELEASE_INVALIDATED"
        assert result["enabled"] is True
        mock_notification_repo.upsert_subscription.assert_called_once()

    async def test_subscribe_release_pending(self, service, mock_notification_repo, mock_audit_logger):
        """Verifica la subscripción exitosa al evento RELEASE_PENDING."""
        user_id = uuid4()
        created_sub = MagicMock()
        created_sub.id = uuid4()
        created_sub.user_id = user_id
        created_sub.event_type = "RELEASE_PENDING"
        created_sub.enabled = True
        created_sub.created_at = datetime.now(timezone.utc)

        mock_notification_repo.upsert_subscription.return_value = created_sub

        result = await service.subscribe(
            user_id=user_id,
            event_type="RELEASE_PENDING",
        )

        assert result["event_type"] == "RELEASE_PENDING"
        mock_notification_repo.upsert_subscription.assert_called_once()

    async def test_subscribe_returns_isoformatted_date(self, service, mock_notification_repo, mock_audit_logger):
        """Verifica que el campo created_at en la respuesta esté en formato ISO 8601."""
        user_id = uuid4()
        created_sub = MagicMock()
        created_sub.id = uuid4()
        created_sub.user_id = user_id
        created_sub.event_type = "WEEKLY_DIGEST"
        created_sub.enabled = True
        created_sub.created_at = datetime(2025, 6, 15, 10, 30, 0, tzinfo=timezone.utc)

        mock_notification_repo.upsert_subscription.return_value = created_sub

        result = await service.subscribe(
            user_id=user_id,
            event_type="WEEKLY_DIGEST",
        )

        assert result["created_at"] == "2025-06-15T10:30:00+00:00"


class TestUnsubscribe:
    async def test_unsubscribe_success(self, service, mock_notification_repo, mock_audit_logger):
        """Verifica la cancelación exitosa de una subscripción a un evento."""
        user_id = uuid4()
        event_type = "RELEASE_VALIDATED"

        await service.unsubscribe(user_id=user_id, event_type=event_type)

        mock_notification_repo.delete_subscription.assert_called_once_with(user_id, event_type)
        mock_audit_logger.log.assert_called_once()

    async def test_unsubscribe_weekly_digest(self, service, mock_notification_repo, mock_audit_logger):
        """Verifica la cancelación exitosa de la subscripción a WEEKLY_DIGEST."""
        user_id = uuid4()
        event_type = "WEEKLY_DIGEST"

        await service.unsubscribe(user_id=user_id, event_type=event_type)

        mock_notification_repo.delete_subscription.assert_called_once_with(user_id, event_type)
        mock_audit_logger.log.assert_called_once()

    async def test_unsubscribe_release_pending(self, service, mock_notification_repo, mock_audit_logger):
        """Verifica la cancelación exitosa de la subscripción a RELEASE_PENDING."""
        user_id = uuid4()
        event_type = "RELEASE_PENDING"

        await service.unsubscribe(user_id=user_id, event_type=event_type)

        mock_notification_repo.delete_subscription.assert_called_once_with(user_id, event_type)
        mock_audit_logger.log.assert_called_once()

    async def test_unsubscribe_calls_delete_subscription_only(self, service, mock_notification_repo, mock_audit_logger):
        """Verifica que unsubscribe solo llame a delete_subscription y al audit logger, sin otras llamadas."""
        user_id = uuid4()
        event_type = "RELEASE_INVALIDATED"

        await service.unsubscribe(user_id=user_id, event_type=event_type)

        mock_notification_repo.delete_subscription.assert_called_once()
        mock_audit_logger.log.assert_called_once()
        mock_notification_repo.upsert_subscription.assert_not_called()
        mock_notification_repo.list_subscriptions.assert_not_called()

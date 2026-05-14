from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from application.ports.input.i_notification_service import INotificationService
from application.ports.output.i_notification_repository import INotificationRepository
from domain.entities.notification_channel import NotificationChannel
from domain.entities.notification_subscription import NotificationSubscription
from domain.exceptions import EntityNotFoundError, ValidationError
from core.audit import AuditEntry, AuditEvent, get_audit_logger
from core.logger import get_logger

_log = get_logger(__name__)

SUPPORTED_CHANNEL_TYPES = {"EMAIL", "SLACK", "MS_TEAMS"}
SUPPORTED_EVENT_TYPES = {"RELEASE_VALIDATED", "RELEASE_INVALIDATED", "RELEASE_PENDING", "WEEKLY_DIGEST"}
PREFERENCE_EVENT_MAP = {
    "release_validated": "RELEASE_VALIDATED",
    "release_invalidated": "RELEASE_INVALIDATED",
    "release_pending_reminder": "RELEASE_PENDING",
    "weekly_digest": "WEEKLY_DIGEST",
}
EVENT_PREFERENCE_MAP = {v: k for k, v in PREFERENCE_EVENT_MAP.items()}


class NotificationService(INotificationService):
    def __init__(self, notification_repository: INotificationRepository) -> None:
        self._repo = notification_repository

    async def list_channels(self, organization_id: UUID) -> List[Dict[str, Any]]:
        channels = await self._repo.list_channels(organization_id)
        return [
            {
                "id": str(c.id),
                "organization_id": str(c.organization_id),
                "channel_type": c.channel_type,
                "enabled": c.enabled,
                "config_data": c.config_data,
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat(),
            }
            for c in channels
        ]

    async def configure_channel(
        self,
        organization_id: UUID,
        channel_type: str,
        enabled: bool,
        config_data: Dict[str, Any],
    ):
        if channel_type not in SUPPORTED_CHANNEL_TYPES:
            raise ValidationError(f"Tipo de canal no soportado: {channel_type}")

        channel = NotificationChannel(
            organization_id=organization_id,
            channel_type=channel_type,
            enabled=enabled,
            config_data=config_data,
        )
        created = await self._repo.create_channel(channel)

        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.NOTIFICATION_CHANNEL_CREATED,
            user_id=UUID(int=0),
            organization_id=organization_id,
            resource_type="notification_channel",
            resource_id=created.id,
            details={"channel_type": channel_type, "enabled": enabled},
        ))
        _log.info("Notification channel configured: org=%s type=%s enabled=%s", organization_id, channel_type, enabled)

        return created

    async def update_channel(
        self,
        channel_id: UUID,
        enabled: Optional[bool] = None,
        config_data: Optional[Dict[str, Any]] = None,
    ):
        channel = await self._repo.get_channel_by_id(channel_id)
        if not channel:
            raise EntityNotFoundError(f"Canal de notificación no encontrado: {channel_id}")

        if enabled is not None:
            channel.enabled = enabled
        if config_data is not None:
            channel.config_data = config_data

        updated = await self._repo.update_channel(channel)

        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.NOTIFICATION_CHANNEL_UPDATED,
            user_id=UUID(int=0),
            organization_id=channel.organization_id,
            resource_type="notification_channel",
            resource_id=channel_id,
            details={"channel_type": channel.channel_type, "enabled": channel.enabled},
        ))
        _log.info("Notification channel updated: id=%s type=%s", channel_id, channel.channel_type)

        return updated

    async def delete_channel(self, channel_id: UUID):
        channel = await self._repo.get_channel_by_id(channel_id)
        if not channel:
            raise EntityNotFoundError(f"Canal de notificación no encontrado: {channel_id}")

        await self._repo.delete_channel(channel_id)

        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.NOTIFICATION_CHANNEL_DELETED,
            user_id=UUID(int=0),
            organization_id=channel.organization_id,
            resource_type="notification_channel",
            resource_id=channel_id,
            details={"channel_type": channel.channel_type},
        ))
        _log.info("Notification channel deleted: id=%s type=%s", channel_id, channel.channel_type)

    async def get_user_preferences(self, user_id: UUID) -> Dict[str, Any]:
        subscriptions = await self._repo.list_subscriptions(user_id)

        prefs: Dict[str, Any] = {
            "release_validated": True,
            "release_invalidated": True,
            "release_pending_reminder": False,
            "weekly_digest": True,
        }

        for sub in subscriptions:
            pref_key = EVENT_PREFERENCE_MAP.get(sub.event_type)
            if pref_key:
                prefs[pref_key] = sub.enabled

        return prefs

    async def update_user_preferences(
        self,
        user_id: UUID,
        release_validated: Optional[bool] = None,
        release_invalidated: Optional[bool] = None,
        release_pending_reminder: Optional[bool] = None,
        weekly_digest: Optional[bool] = None,
    ):
        updates = {
            "RELEASE_VALIDATED": release_validated,
            "RELEASE_INVALIDATED": release_invalidated,
            "RELEASE_PENDING": release_pending_reminder,
            "WEEKLY_DIGEST": weekly_digest,
        }

        for event_type, enabled in updates.items():
            if enabled is not None:
                sub = NotificationSubscription(
                    user_id=user_id,
                    event_type=event_type,
                    enabled=enabled,
                )
                await self._repo.upsert_subscription(sub)

        return await self.get_user_preferences(user_id)

    async def subscribe(
        self,
        user_id: UUID,
        event_type: str,
        enabled: bool = True,
    ) -> Dict[str, Any]:
        if event_type not in SUPPORTED_EVENT_TYPES:
            raise ValidationError(f"Tipo de evento no soportado: {event_type}")

        sub = NotificationSubscription(
            user_id=user_id,
            event_type=event_type,
            enabled=enabled,
        )
        created = await self._repo.upsert_subscription(sub)

        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.NOTIFICATION_SUBSCRIBED,
            user_id=user_id,
            organization_id=None,
            resource_type="notification_subscription",
            resource_id=created.id,
            details={"event_type": event_type, "enabled": enabled},
        ))
        _log.info("Notification subscription: user=%s event=%s enabled=%s", user_id, event_type, enabled)

        return {
            "id": str(created.id),
            "user_id": str(created.user_id),
            "event_type": created.event_type,
            "enabled": created.enabled,
            "created_at": created.created_at.isoformat(),
        }

    async def unsubscribe(self, user_id: UUID, event_type: str):
        await self._repo.delete_subscription(user_id, event_type)

        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.NOTIFICATION_UNSUBSCRIBED,
            user_id=user_id,
            organization_id=None,
            resource_type="notification_subscription",
            resource_id=None,
            details={"event_type": event_type},
        ))
        _log.info("Notification unsubscription: user=%s event=%s", user_id, event_type)

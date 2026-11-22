from typing import Any, Protocol

from features.notifications.domain.notification_channel import NotificationChannel


class INotificationSender(Protocol):
    async def __call__(self, channel: NotificationChannel, event_type: str, ctx: dict[str, Any]) -> bool: ...

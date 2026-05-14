from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID
from domain.entities.notification_channel import NotificationChannel
from domain.entities.notification_subscription import NotificationSubscription


class INotificationRepository(ABC):
    @abstractmethod
    async def create_channel(self, channel: NotificationChannel) -> NotificationChannel:
        pass

    @abstractmethod
    async def list_channels(self, organization_id: UUID) -> List[NotificationChannel]:
        pass

    @abstractmethod
    async def get_channel_by_id(self, channel_id: UUID) -> Optional[NotificationChannel]:
        pass

    @abstractmethod
    async def update_channel(self, channel: NotificationChannel) -> NotificationChannel:
        pass

    @abstractmethod
    async def delete_channel(self, channel_id: UUID) -> None:
        pass

    @abstractmethod
    async def list_subscriptions(self, user_id: UUID) -> List[NotificationSubscription]:
        pass

    @abstractmethod
    async def get_subscription(self, user_id: UUID, event_type: str) -> Optional[NotificationSubscription]:
        pass

    @abstractmethod
    async def upsert_subscription(self, subscription: NotificationSubscription) -> NotificationSubscription:
        pass

    @abstractmethod
    async def delete_subscription(self, user_id: UUID, event_type: str) -> None:
        pass

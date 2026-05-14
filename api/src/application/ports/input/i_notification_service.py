from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from uuid import UUID
from domain.entities.notification_channel import NotificationChannel

class INotificationService(ABC):
    @abstractmethod
    async def list_channels(self, organization_id: UUID) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def configure_channel(
        self,
        organization_id: UUID,
        channel_type: str,
        enabled: bool,
        config_data: Dict[str, Any],
    ) -> NotificationChannel:
        pass

    @abstractmethod
    async def update_channel(
        self,
        channel_id: UUID,
        enabled: Optional[bool] = None,
        config_data: Optional[Dict[str, Any]] = None,
    ) -> NotificationChannel:
        pass

    @abstractmethod
    async def delete_channel(self, channel_id: UUID) -> None:
        pass

    @abstractmethod
    async def get_user_preferences(self, user_id: UUID) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def update_user_preferences(
        self,
        user_id: UUID,
        release_validated: Optional[bool] = None,
        release_invalidated: Optional[bool] = None,
        release_pending_reminder: Optional[bool] = None,
        weekly_digest: Optional[bool] = None,
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def subscribe(
        self,
        user_id: UUID,
        event_type: str,
        enabled: bool = True,
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def unsubscribe(self, user_id: UUID, event_type: str) -> None:
        pass
from typing import Optional, List, cast
import uuid
from datetime import datetime, timezone
from application.ports.output.i_notification_repository import INotificationRepository
from domain.entities.notification_channel import NotificationChannel
from domain.entities.notification_subscription import NotificationSubscription
from infrastructure.secondary.database.models.notification_channel_model import NotificationChannelModel
from infrastructure.secondary.database.models.notification_subscription_model import NotificationSubscriptionModel
from infrastructure.secondary.database.repositories.base_sql_repository import _session_scope
from contextlib import asynccontextmanager
from sqlalchemy.future import select


class SqlNotificationRepository(INotificationRepository):
    def _channel_model_to_entity(self, row: NotificationChannelModel) -> NotificationChannel:
        return NotificationChannel(
            id=cast(uuid.UUID, row.id),
            organization_id=cast(uuid.UUID, row.organization_id),
            channel_type=cast(str, row.channel_type),
            enabled=cast(bool, row.enabled),
            config_data=cast(dict, row.config_data) or {},
            created_at=cast(datetime, row.created_at),
            updated_at=cast(datetime, row.updated_at),
        )

    def _channel_entity_to_model_attrs(self, entity: NotificationChannel) -> dict:
        return {
            "organization_id": entity.organization_id,
            "channel_type": entity.channel_type,
            "enabled": entity.enabled,
            "config_data": entity.config_data,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
        }

    def _subscription_model_to_entity(self, row: NotificationSubscriptionModel) -> NotificationSubscription:
        return NotificationSubscription(
            id=cast(uuid.UUID, row.id),
            user_id=cast(uuid.UUID, row.user_id),
            event_type=cast(str, row.event_type),
            enabled=cast(bool, row.enabled),
            created_at=cast(datetime, row.created_at),
            updated_at=cast(datetime, row.updated_at),
        )

    def _subscription_entity_to_model_attrs(self, entity: NotificationSubscription) -> dict:
        return {
            "user_id": entity.user_id,
            "event_type": entity.event_type,
            "enabled": entity.enabled,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
        }

    async def create_channel(self, channel: NotificationChannel) -> NotificationChannel:
        async with _session_scope() as session:
            model = NotificationChannelModel(**self._channel_entity_to_model_attrs(channel))
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return self._channel_model_to_entity(model)

    async def list_channels(self, organization_id: uuid.UUID) -> List[NotificationChannel]:
        async with _session_scope() as session:
            result = await session.execute(
                select(NotificationChannelModel).where(NotificationChannelModel.organization_id == organization_id)
            )
            rows = result.scalars().all()
            return [self._channel_model_to_entity(row) for row in rows]

    async def get_channel_by_id(self, channel_id: uuid.UUID) -> Optional[NotificationChannel]:
        async with _session_scope() as session:
            result = await session.execute(select(NotificationChannelModel).where(NotificationChannelModel.id == channel_id))
            row = result.scalar_one_or_none()
            if row is None:
                return None
            return self._channel_model_to_entity(row)

    async def update_channel(self, channel: NotificationChannel) -> NotificationChannel:
        async with _session_scope() as session:
            model = await session.get(NotificationChannelModel, channel.id)
            if not model:
                raise ValueError("Notification channel not found")
            model.channel_type = channel.channel_type  # pyright: ignore[reportAttributeAccessIssue]
            model.enabled = channel.enabled  # pyright: ignore[reportAttributeAccessIssue]
            model.config_data = channel.config_data  # pyright: ignore[reportAttributeAccessIssue]
            model.updated_at = datetime.now(timezone.utc)  # pyright: ignore[reportAttributeAccessIssue]
            await session.commit()
            await session.refresh(model)
            return self._channel_model_to_entity(model)

    async def delete_channel(self, channel_id: uuid.UUID) -> None:
        async with _session_scope() as session:
            model = await session.get(NotificationChannelModel, channel_id)
            if not model:
                raise ValueError("Notification channel not found")
            session.delete(model)  # pyright: ignore[reportUnusedCoroutine]
            await session.commit()

    async def list_subscriptions(self, user_id: uuid.UUID) -> List[NotificationSubscription]:
        async with _session_scope() as session:
            result = await session.execute(
                select(NotificationSubscriptionModel).where(NotificationSubscriptionModel.user_id == user_id)
            )
            rows = result.scalars().all()
            return [self._subscription_model_to_entity(row) for row in rows]

    async def get_subscription(self, user_id: uuid.UUID, event_type: str) -> Optional[NotificationSubscription]:
        async with _session_scope() as session:
            result = await session.execute(
                select(NotificationSubscriptionModel).where(
                    NotificationSubscriptionModel.user_id == user_id,
                    NotificationSubscriptionModel.event_type == event_type,
                )
            )
            row = result.scalar_one_or_none()
            if row is None:
                return None
            return self._subscription_model_to_entity(row)

    async def upsert_subscription(self, subscription: NotificationSubscription) -> NotificationSubscription:
        async with _session_scope() as session:
            result = await session.execute(
                select(NotificationSubscriptionModel).where(
                    NotificationSubscriptionModel.user_id == subscription.user_id,
                    NotificationSubscriptionModel.event_type == subscription.event_type,
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                existing.enabled = subscription.enabled  # pyright: ignore[reportAttributeAccessIssue]
                existing.updated_at = datetime.now(timezone.utc)  # pyright: ignore[reportAttributeAccessIssue]
                await session.commit()
                await session.refresh(existing)
                return self._subscription_model_to_entity(existing)
            model = NotificationSubscriptionModel(**self._subscription_entity_to_model_attrs(subscription))
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return self._subscription_model_to_entity(model)

    async def delete_subscription(self, user_id: uuid.UUID, event_type: str) -> None:
        async with _session_scope() as session:
            result = await session.execute(
                select(NotificationSubscriptionModel).where(
                    NotificationSubscriptionModel.user_id == user_id,
                    NotificationSubscriptionModel.event_type == event_type,
                )
            )
            model = result.scalar_one_or_none()
            if not model:
                return
            session.delete(model)  # pyright: ignore[reportUnusedCoroutine]
            await session.commit()
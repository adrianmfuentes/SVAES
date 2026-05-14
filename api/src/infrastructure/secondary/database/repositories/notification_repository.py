from sqlalchemy.future import select
from typing import Optional, List, cast
import uuid
from datetime import datetime
from application.ports.output.i_notification_repository import INotificationRepository
from domain.entities.notification_channel import NotificationChannel
from domain.entities.notification_subscription import NotificationSubscription
from infrastructure.secondary.database.models.notification_channel_model import NotificationChannelModel
from infrastructure.secondary.database.models.notification_subscription_model import NotificationSubscriptionModel
from infrastructure.secondary.database.get_async_session import get_async_session


class SqlNotificationRepository(INotificationRepository):
    async def create_channel(self, channel: NotificationChannel) -> NotificationChannel:
        session = await get_async_session().__anext__()

        try:
            model = NotificationChannelModel(
                id=channel.id,
                organization_id=channel.organization_id,
                channel_type=channel.channel_type,
                enabled=channel.enabled,
                config_data=channel.config_data,
                created_at=channel.created_at,
                updated_at=channel.updated_at,
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)

            return NotificationChannel(
                id=cast(uuid.UUID, model.id),
                organization_id=cast(uuid.UUID, model.organization_id),
                channel_type=cast(str, model.channel_type),
                enabled=cast(bool, model.enabled),
                config_data=cast(dict, model.config_data) or {},
                created_at=cast(datetime, model.created_at),
                updated_at=cast(datetime, model.updated_at),
            )
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def list_channels(self, organization_id: uuid.UUID) -> List[NotificationChannel]:
        session = await get_async_session().__anext__()

        try:
            result = await session.execute(
                select(NotificationChannelModel).where(NotificationChannelModel.organization_id == organization_id)
            )
            rows = result.scalars().all()

            return [
                NotificationChannel(
                    id=cast(uuid.UUID, row.id),
                    organization_id=cast(uuid.UUID, row.organization_id),
                    channel_type=cast(str, row.channel_type),
                    enabled=cast(bool, row.enabled),
                    config_data=cast(dict, row.config_data) or {},
                    created_at=cast(datetime, row.created_at),
                    updated_at=cast(datetime, row.updated_at),
                )
                for row in rows
            ]
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def get_channel_by_id(self, channel_id: uuid.UUID) -> Optional[NotificationChannel]:
        session = await get_async_session().__anext__()

        try:
            result = await session.execute(select(NotificationChannelModel).where(NotificationChannelModel.id == channel_id))
            row = result.scalar_one_or_none()
            if not row:
                return None

            return NotificationChannel(
                id=cast(uuid.UUID, row.id),
                organization_id=cast(uuid.UUID, row.organization_id),
                channel_type=cast(str, row.channel_type),
                enabled=cast(bool, row.enabled),
                config_data=cast(dict, row.config_data) or {},
                created_at=cast(datetime, row.created_at),
                updated_at=cast(datetime, row.updated_at),
            )
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def update_channel(self, channel: NotificationChannel) -> NotificationChannel:
        session = await get_async_session().__anext__()

        try:
            model = await session.get(NotificationChannelModel, channel.id)
            if not model:
                raise ValueError("Notification channel not found")

            model.channel_type = channel.channel_type  # pyright: ignore[reportAttributeAccessIssue]
            model.enabled = channel.enabled  # pyright: ignore[reportAttributeAccessIssue]
            model.config_data = channel.config_data  # pyright: ignore[reportAttributeAccessIssue]
            model.updated_at = datetime.now(datetime.timezone.utc)

            await session.commit()
            await session.refresh(model)

            return NotificationChannel(
                id=cast(uuid.UUID, model.id),
                organization_id=cast(uuid.UUID, model.organization_id),
                channel_type=cast(str, model.channel_type),
                enabled=cast(bool, model.enabled),
                config_data=cast(dict, model.config_data) or {},
                created_at=cast(datetime, model.created_at),
                updated_at=cast(datetime, model.updated_at),
            )
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def delete_channel(self, channel_id: uuid.UUID) -> None:
        session = await get_async_session().__anext__()

        try:
            model = await session.get(NotificationChannelModel, channel_id)
            if not model:
                raise ValueError("Notification channel not found")

            await session.delete(model)
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def list_subscriptions(self, user_id: uuid.UUID) -> List[NotificationSubscription]:
        session = await get_async_session().__anext__()

        try:
            result = await session.execute(
                select(NotificationSubscriptionModel).where(NotificationSubscriptionModel.user_id == user_id)
            )
            rows = result.scalars().all()

            return [
                NotificationSubscription(
                    id=cast(uuid.UUID, row.id),
                    user_id=cast(uuid.UUID, row.user_id),
                    event_type=cast(str, row.event_type),
                    enabled=cast(bool, row.enabled),
                    created_at=cast(datetime, row.created_at),
                    updated_at=cast(datetime, row.updated_at),
                )
                for row in rows
            ]
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def get_subscription(self, user_id: uuid.UUID, event_type: str) -> Optional[NotificationSubscription]:
        session = await get_async_session().__anext__()

        try:
            result = await session.execute(
                select(NotificationSubscriptionModel).where(
                    NotificationSubscriptionModel.user_id == user_id,
                    NotificationSubscriptionModel.event_type == event_type,
                )
            )
            row = result.scalar_one_or_none()
            if not row:
                return None

            return NotificationSubscription(
                id=cast(uuid.UUID, row.id),
                user_id=cast(uuid.UUID, row.user_id),
                event_type=cast(str, row.event_type),
                enabled=cast(bool, row.enabled),
                created_at=cast(datetime, row.created_at),
                updated_at=cast(datetime, row.updated_at),
            )
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def upsert_subscription(self, subscription: NotificationSubscription) -> NotificationSubscription:
        session = await get_async_session().__anext__()

        try:
            result = await session.execute(
                select(NotificationSubscriptionModel).where(
                    NotificationSubscriptionModel.user_id == subscription.user_id,
                    NotificationSubscriptionModel.event_type == subscription.event_type,
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                existing.enabled = subscription.enabled  # pyright: ignore[reportAttributeAccessIssue]
                existing.updated_at = datetime.now(datetime.timezone.utc)
                await session.commit()
                await session.refresh(existing)
                row = existing
            else:
                model = NotificationSubscriptionModel(
                    id=subscription.id,
                    user_id=subscription.user_id,
                    event_type=subscription.event_type,
                    enabled=subscription.enabled,
                    created_at=subscription.created_at,
                    updated_at=subscription.updated_at,
                )
                session.add(model)
                await session.commit()
                await session.refresh(model)
                row = model

            return NotificationSubscription(
                id=cast(uuid.UUID, row.id),
                user_id=cast(uuid.UUID, row.user_id),
                event_type=cast(str, row.event_type),
                enabled=cast(bool, row.enabled),
                created_at=cast(datetime, row.created_at),
                updated_at=cast(datetime, row.updated_at),
            )
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def delete_subscription(self, user_id: uuid.UUID, event_type: str) -> None:
        session = await get_async_session().__anext__()

        try:
            result = await session.execute(
                select(NotificationSubscriptionModel).where(
                    NotificationSubscriptionModel.user_id == user_id,
                    NotificationSubscriptionModel.event_type == event_type,
                )
            )
            model = result.scalar_one_or_none()
            if not model:
                return

            await session.delete(model)
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

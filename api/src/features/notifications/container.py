from __future__ import annotations

from bootstrap.repositories import get_notification_repository
from features.notifications.application.ports.i_notification_service import INotificationService
from features.notifications.application.use_cases.notification_service import NotificationService
from features.notifications.infrastructure.gateways.outbound_webhook_sender import send_outbound_notification
from shared.infrastructure.audit_db import get_audit_logger


def get_notification_service() -> INotificationService:
    notification_repo = get_notification_repository()
    return NotificationService(
        notification_repository=notification_repo,
        audit_logger=get_audit_logger(),
        send_notification=send_outbound_notification,
    )

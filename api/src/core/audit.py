import asyncio
import logging
import uuid
from enum import Enum
from typing import Optional
from uuid import UUID
from dataclasses import dataclass, field
from datetime import datetime, timezone

class AuditEvent(str, Enum):
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILED = "LOGIN_FAILED"
    USER_INVITED = "USER_INVITED"
    USER_ROLE_CHANGED = "USER_ROLE_CHANGED"
    USER_REMOVED = "USER_REMOVED"
    USER_DEACTIVATED = "USER_DEACTIVATED"
    ORG_OWNERSHIP_TRANSFERRED = "ORG_OWNERSHIP_TRANSFERRED"
    API_KEY_CREATED = "API_KEY_CREATED"
    API_KEY_REVOKED = "API_KEY_REVOKED"
    CONNECTOR_CREATED = "CONNECTOR_CREATED"
    CONNECTOR_UPDATED = "CONNECTOR_UPDATED"
    CONNECTOR_DELETED = "CONNECTOR_DELETED"
    CONNECTOR_TESTED = "CONNECTOR_TESTED"
    RELEASE_CREATED = "RELEASE_CREATED"
    RELEASE_VERIFIED = "RELEASE_VERIFIED"
    RELEASE_ARCHIVED = "RELEASE_ARCHIVED"
    PROJECT_ARCHIVED = "PROJECT_ARCHIVED"
    PROFILE_CREATED = "PROFILE_CREATED"
    PROFILE_UPDATED = "PROFILE_UPDATED"
    PROFILE_DELETED = "PROFILE_DELETED"
    RULE_CREATED = "RULE_CREATED"
    RULE_UPDATED = "RULE_UPDATED"
    RULE_DELETED = "RULE_DELETED"
    CUSTOM_ROLE_CREATED = "CUSTOM_ROLE_CREATED"
    CUSTOM_ROLE_UPDATED = "CUSTOM_ROLE_UPDATED"
    CUSTOM_ROLE_DELETED = "CUSTOM_ROLE_DELETED"
    TEMPLATE_CREATED = "TEMPLATE_CREATED"
    TEMPLATE_UPDATED = "TEMPLATE_UPDATED"
    TEMPLATE_ARCHIVED = "TEMPLATE_ARCHIVED"
    TEMPLATE_CLONED = "TEMPLATE_CLONED"
    NOTIFICATION_CHANNEL_CREATED = "NOTIFICATION_CHANNEL_CREATED"
    NOTIFICATION_CHANNEL_UPDATED = "NOTIFICATION_CHANNEL_UPDATED"
    NOTIFICATION_CHANNEL_DELETED = "NOTIFICATION_CHANNEL_DELETED"
    NOTIFICATION_SUBSCRIBED = "NOTIFICATION_SUBSCRIBED"
    NOTIFICATION_UNSUBSCRIBED = "NOTIFICATION_UNSUBSCRIBED"
    USER_ACCOUNT_DELETED = "USER_ACCOUNT_DELETED"
    USER_LOGGED_OUT = "USER_LOGGED_OUT"
    SECURITY_BREACH_DETECTED = "SECURITY_BREACH_DETECTED"
    DATA_EXPORT_REQUESTED = "DATA_EXPORT_REQUESTED"

@dataclass
class AuditEntry:
    event: AuditEvent
    user_id: UUID
    organization_id: Optional[UUID]
    resource_type: str
    resource_id: Optional[UUID]
    details: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ip_address: Optional[str] = None

class AuditLogger:
    _instance: Optional["AuditLogger"] = None

    def __init__(self):
        self._logger = logging.getLogger("audit")

    @classmethod
    def get_instance(cls) -> "AuditLogger":
        if cls._instance is None:
            cls._instance = AuditLogger()
        return cls._instance

    def log(self, entry: AuditEntry) -> None:
        self._logger.info(
            "AUDIT | %s | user=%s | org=%s | %s/%s | %s | %s",
            entry.event.value,
            str(entry.user_id),
            str(entry.organization_id) if entry.organization_id else "N/A",
            entry.resource_type,
            str(entry.resource_id) if entry.resource_id else "N/A",
            entry.details or "",
            f"ip={entry.ip_address}" if entry.ip_address else "",
        )
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._persist(entry))
        except RuntimeError:
            pass

    async def _persist(self, entry: AuditEntry) -> None:
        try:
            from infrastructure.secondary.database.get_async_session import AsyncSessionLocal
            from infrastructure.secondary.database.models.audit_log_model import AuditLogModel
            async with AsyncSessionLocal() as session:
                record = AuditLogModel(
                    id=uuid.uuid4(),
                    event=entry.event.value,
                    user_id=entry.user_id,
                    organization_id=entry.organization_id,
                    resource_type=entry.resource_type,
                    resource_id=entry.resource_id,
                    details=entry.details or {},
                    ip_address=entry.ip_address,
                    timestamp=entry.timestamp,
                )
                session.add(record)
                await session.commit()
        except Exception as exc:
            self._logger.error("Failed to persist audit entry: %s", exc)

def get_audit_logger() -> AuditLogger:
    return AuditLogger.get_instance()
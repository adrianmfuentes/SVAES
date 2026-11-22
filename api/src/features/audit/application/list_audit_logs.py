import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class StoredAuditLog:
    id: UUID
    timestamp: datetime
    event: str
    user_id: UUID
    resource_type: str | None
    resource_id: UUID | None
    ip_address: str | None


class IAuditLogRepository(Protocol):
    async def list(
        self, included_events: set[str], excluded_events: set[str], limit: int, skip: int,
    ) -> tuple[int, list[StoredAuditLog]]: ...


EVENT_TO_CATEGORY: dict[str, str] = {
    "LOGIN_SUCCESS": "auth",
    "LOGIN_FAILED": "auth",
    "USER_LOGGED_OUT": "auth",
    "SECURITY_BREACH_DETECTED": "auth",
    "USER_INVITED": "admin",
    "USER_ROLE_CHANGED": "admin",
    "USER_REMOVED": "admin",
    "USER_DEACTIVATED": "admin",
    "USER_ACCOUNT_DELETED": "admin",
    "ORG_OWNERSHIP_TRANSFERRED": "admin",
    "API_KEY_CREATED": "admin",
    "API_KEY_REVOKED": "admin",
    "DATA_EXPORT_REQUESTED": "admin",
    "CONNECTOR_CREATED": "connector",
    "CONNECTOR_UPDATED": "connector",
    "CONNECTOR_DELETED": "connector",
    "CONNECTOR_TESTED": "connector",
    "RELEASE_CREATED": "release",
    "RELEASE_VERIFIED": "release",
    "RELEASE_ARCHIVED": "release",
    "PROJECT_ARCHIVED": "release",
    "PROJECT_UNARCHIVED": "release",
    "PROJECT_UPDATED": "release",
    "PROFILE_CREATED": "config",
    "PROFILE_UPDATED": "config",
    "PROFILE_DELETED": "config",
    "RULE_CREATED": "config",
    "RULE_UPDATED": "config",
    "RULE_DELETED": "config",
    "CUSTOM_ROLE_CREATED": "config",
    "CUSTOM_ROLE_UPDATED": "config",
    "CUSTOM_ROLE_DELETED": "config",
    "TEMPLATE_CREATED": "config",
    "TEMPLATE_UPDATED": "config",
    "TEMPLATE_ARCHIVED": "config",
    "TEMPLATE_CLONED": "config",
    "NOTIFICATION_CHANNEL_CREATED": "config",
    "NOTIFICATION_CHANNEL_UPDATED": "config",
    "NOTIFICATION_CHANNEL_DELETED": "config",
    "NOTIFICATION_SUBSCRIBED": "config",
    "NOTIFICATION_UNSUBSCRIBED": "config",
}

FAILURE_EVENTS: set[str] = {
    "LOGIN_FAILED",
    "SECURITY_BREACH_DETECTED",
}

def _mask_uuid(uid: str | None) -> str | None:
    if not uid:
        return None
    h = hashlib.sha256(uid.encode("utf-8")).hexdigest()
    return f"sha256:{h[:8]}…{h[-4:]}"


def _derive_result(event: str) -> str:
    if event in FAILURE_EVENTS:
        return "failure"
    return "success"


class ListAuditLogs:
    def __init__(self, repository: IAuditLogRepository) -> None:
        self._repository = repository

    async def execute(self, category: str | None, result: str | None, limit: int, skip: int) -> dict:
        events = {event for event, name in EVENT_TO_CATEGORY.items() if name == category}
        excluded = set()
        if result == "failure":
            events = events & FAILURE_EVENTS if events else FAILURE_EVENTS
            if not events:
                return {"total": 0, "logs": []}
        elif result == "success":
            excluded = FAILURE_EVENTS

        total, rows = await self._repository.list(events, excluded, limit, skip)
        return {
            "total": total,
            "logs": [
                {
                    "id": str(row.id),
                    "timestamp": row.timestamp.isoformat(),
                    "action": row.event,
                    "category": EVENT_TO_CATEGORY.get(row.event, "config"),
                    "actor_id": _mask_uuid(str(row.user_id)) or "",
                    "actor_role": "masked",
                    "target_type": row.resource_type,
                    "target_id": _mask_uuid(str(row.resource_id)) if row.resource_id is not None else None,
                    "result": _derive_result(row.event),
                    "ip_address": _mask_uuid(row.ip_address),
                }
                for row in rows
            ],
        }

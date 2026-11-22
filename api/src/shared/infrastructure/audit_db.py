import asyncio
import logging
import uuid
from typing import Optional

from shared.domain.audit import AuditEntry


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
            from shared.infrastructure.database.get_async_session import AsyncSessionLocal
            from shared.infrastructure.database.models.audit_log_model import AuditLogModel
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
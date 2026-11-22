from sqlalchemy import func, select

from features.audit.application.list_audit_logs import StoredAuditLog
from shared.infrastructure.database.get_async_session import AsyncSessionLocal
from shared.infrastructure.database.models.audit_log_model import AuditLogModel


class SqlAuditLogRepository:
    async def list(
        self, included_events: set[str], excluded_events: set[str], limit: int, skip: int,
    ) -> tuple[int, list[StoredAuditLog]]:
        query = select(AuditLogModel)
        if included_events:
            query = query.where(AuditLogModel.event.in_(included_events))
        if excluded_events:
            query = query.where(AuditLogModel.event.notin_(excluded_events))
        async with AsyncSessionLocal() as session:
            total = await session.scalar(select(func.count()).select_from(query.subquery()))
            rows = await session.scalars(query.order_by(AuditLogModel.timestamp.desc()).offset(skip).limit(limit))
            return total or 0, [
                StoredAuditLog(
                    row.id, row.timestamp, row.event, row.user_id, row.resource_type,
                    row.resource_id, str(row.ip_address) if row.ip_address is not None else None,
                )
                for row in rows
            ]

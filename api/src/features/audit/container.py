from features.audit.application.list_audit_logs import ListAuditLogs
from features.audit.infrastructure.audit_log_repository import SqlAuditLogRepository


def get_list_audit_logs() -> ListAuditLogs:
    return ListAuditLogs(SqlAuditLogRepository())

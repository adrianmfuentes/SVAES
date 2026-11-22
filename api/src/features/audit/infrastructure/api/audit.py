from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from bootstrap.dependencies import CurrentUser, require_role
from shared.domain.enums import UserRole
from features.audit.application.list_audit_logs import ListAuditLogs
from features.audit.container import get_list_audit_logs

router = APIRouter(tags=["Audit"])


class AuditLogEntry(BaseModel):
    id: str
    timestamp: str
    action: str
    category: str
    actor_id: str
    actor_role: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    result: str
    ip_address: Optional[str] = None


class AuditLogsResponse(BaseModel):
    total: int
    logs: List[AuditLogEntry]


@router.get("/api/v1/audit/logs", response_model=AuditLogsResponse)
async def get_audit_logs(
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.U3))],
    use_case: Annotated[ListAuditLogs, Depends(get_list_audit_logs)],
    category: Annotated[Optional[str], Query(description="Filtrar por categoría: auth, admin, release, connector, config")] = None,
    result: Annotated[Optional[str], Query(description="Filtrar por resultado: success, failure")] = None,
    limit: Annotated[int, Query(ge=1, le=1000, description="Máximo de registros a retornar")] = 500,
    skip: Annotated[int, Query(ge=0, description="Registros a omitir para paginación")] = 0,
):
    return await use_case.execute(category, result, limit, skip)

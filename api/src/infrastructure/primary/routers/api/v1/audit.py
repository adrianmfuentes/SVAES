import hashlib
from typing import Annotated, Optional, List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, desc, func
from sqlalchemy.sql.elements import ColumnElement

from core.dependencies import require_role, CurrentUser
from domain.enums import UserRole
from infrastructure.secondary.database.get_async_session import AsyncSessionLocal
from infrastructure.secondary.database.models.audit_log_model import AuditLogModel

router = APIRouter(tags=["Audit"])

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

EVENT_LABELS: dict[str, str] = {
    "LOGIN_SUCCESS": "Inicio de sesión exitoso",
    "LOGIN_FAILED": "Intento de inicio de sesión fallido",
    "USER_INVITED": "Usuario invitado",
    "USER_ROLE_CHANGED": "Cambio de rol de usuario",
    "USER_REMOVED": "Usuario eliminado de organización",
    "USER_DEACTIVATED": "Usuario desactivado",
    "ORG_OWNERSHIP_TRANSFERRED": "Propiedad de organización transferida",
    "API_KEY_CREATED": "API Key creada",
    "API_KEY_REVOKED": "API Key revocada",
    "CONNECTOR_CREATED": "Conector creado",
    "CONNECTOR_UPDATED": "Conector actualizado",
    "CONNECTOR_DELETED": "Conector eliminado",
    "CONNECTOR_TESTED": "Conector probado",
    "RELEASE_CREATED": "Entrega creada",
    "RELEASE_VERIFIED": "Entrega verificada",
    "RELEASE_ARCHIVED": "Entrega archivada",
    "PROJECT_ARCHIVED": "Proyecto archivado",
    "PROFILE_CREATED": "Perfil de verificación creado",
    "PROFILE_UPDATED": "Perfil de verificación actualizado",
    "PROFILE_DELETED": "Perfil de verificación eliminado",
    "RULE_CREATED": "Regla de verificación creada",
    "RULE_UPDATED": "Regla de verificación actualizada",
    "RULE_DELETED": "Regla de verificación eliminada",
    "CUSTOM_ROLE_CREATED": "Rol personalizado creado",
    "CUSTOM_ROLE_UPDATED": "Rol personalizado actualizado",
    "CUSTOM_ROLE_DELETED": "Rol personalizado eliminado",
    "TEMPLATE_CREATED": "Plantilla creada",
    "TEMPLATE_UPDATED": "Plantilla actualizada",
    "TEMPLATE_ARCHIVED": "Plantilla archivada",
    "TEMPLATE_CLONED": "Plantilla clonada",
    "NOTIFICATION_CHANNEL_CREATED": "Canal de notificación creado",
    "NOTIFICATION_CHANNEL_UPDATED": "Canal de notificación actualizado",
    "NOTIFICATION_CHANNEL_DELETED": "Canal de notificación eliminado",
    "NOTIFICATION_SUBSCRIBED": "Suscripción a notificaciones",
    "NOTIFICATION_UNSUBSCRIBED": "Cancelación de suscripción",
    "USER_LOGGED_OUT": "Cierre de sesión",
    "SECURITY_BREACH_DETECTED": "Brecha de seguridad detectada",
    "DATA_EXPORT_REQUESTED": "Exportación de datos solicitada",
    "USER_ACCOUNT_DELETED": "Cuenta de usuario eliminada",
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
    category: Annotated[Optional[str], Query(description="Filtrar por categoría: auth, admin, release, connector, config")] = None,
    result: Annotated[Optional[str], Query(description="Filtrar por resultado: success, failure")] = None,
    limit: Annotated[int, Query(ge=1, le=1000, description="Máximo de registros a retornar")] = 500,
    skip: Annotated[int, Query(ge=0, description="Registros a omitir para paginación")] = 0,
):
    async with AsyncSessionLocal() as session:
        base_query = select(AuditLogModel)
        conditions: list[ColumnElement[bool]] = []

        if category:
            allowed_events = [e for e, c in EVENT_TO_CATEGORY.items() if c == category]
            if allowed_events:
                conditions.append(AuditLogModel.event.in_(allowed_events))

        if result == "failure":
            conditions.append(AuditLogModel.event.in_(list(FAILURE_EVENTS)))
        elif result == "success":
            failure_list = list(FAILURE_EVENTS)
            conditions.append(AuditLogModel.event.notin_(failure_list))

        if conditions:
            base_query = base_query.where(*conditions)

        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar_one()

        query = (
            base_query
            .order_by(desc(AuditLogModel.timestamp))
            .offset(skip)
            .limit(limit)
        )
        result_rows = await session.execute(query)
        rows = result_rows.scalars().all()

    logs: list[AuditLogEntry] = []
    for row in rows:
        masked_ip = None
        if row.ip_address:
            masked_ip = _mask_uuid(row.ip_address)
        logs.append(AuditLogEntry(
            id=str(row.id),
            timestamp=row.timestamp.isoformat(),
            action=row.event,
            category=EVENT_TO_CATEGORY.get(row.event, "config"),
            actor_id=_mask_uuid(str(row.user_id)),
            actor_role="masked",
            target_type=row.resource_type,
            target_id=_mask_uuid(str(row.resource_id)) if row.resource_id else None,
            result=_derive_result(row.event),
            ip_address=masked_ip,
        ))

    return AuditLogsResponse(total=total, logs=logs)

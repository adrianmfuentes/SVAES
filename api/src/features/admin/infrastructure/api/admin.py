from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from features.admin.application.ports.i_rules_service import IRulesService
from bootstrap.dependencies import get_current_user, CurrentUser, require_role, get_rules_service
from shared.domain.enums import UserRole
from shared.infrastructure.api_errors import handle_internal_errors

router = APIRouter(tags=["Admin"])

class RulesReloadResponse(BaseModel):
    success: bool
    rules_loaded: int
    message: str


@router.post("/api/v1/admin/rules/reload", response_model=RulesReloadResponse)
@handle_internal_errors
async def reload_custom_rules(
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.U3))],
    service: Annotated[IRulesService, Depends(get_rules_service)],
):
    """Recarga en caliente las reglas personalizadas (solo U3).

    Este endpoint permite a los administradores recargar las reglas personalizadas
    sin necesidad de reiniciar el sistema, tal como exige el requisito MV6.2.1.

    Atributos:
        - current_user: Usuario autenticado con rol U3.
        - service: Servicio de reglas inyectado mediante dependencias.

    Retorna:
        - 200 OK con el resultado de la recarga.
        - 403 Forbidden si el usuario no es U3.
        - 500 Internal Server Error para cualquier error inesperado.
    """
    result = await service.reload_custom_rules()
    return RulesReloadResponse(
        success=result["success"],
        rules_loaded=result.get("rules_loaded", 0),
        message=result.get("message", "Reglas recargadas con éxito")
    )

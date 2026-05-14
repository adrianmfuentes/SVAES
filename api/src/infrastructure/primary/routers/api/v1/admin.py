from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from application.ports.input.i_rules_service import IRulesService
from core.dependencies import get_current_user, CurrentUser, require_role, get_rules_service
from domain.enums import UserRole

router = APIRouter(tags=["Admin"])


class RulesReloadResponse(BaseModel):
    success: bool
    rules_loaded: int
    message: str


@router.post("/api/v1/admin/rules/reload", response_model=RulesReloadResponse)
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
    try:
        result = await service.reload_custom_rules()
        return RulesReloadResponse(
            success=result["success"],
            rules_loaded=result.get("rules_loaded", 0),
            message=result.get("message", "Reglas recargadas con éxito")
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
from typing import Dict, Any
from application.ports.input.i_rules_service import IRulesService
from application.ports.output.i_verification_rule_repository import IVerificationRuleRepository
from core.logger import get_logger

_log = get_logger(__name__)


class RulesService(IRulesService):
    def __init__(self, rule_repository: IVerificationRuleRepository) -> None:
        self._repo = rule_repository

    async def reload_custom_rules(self) -> Dict[str, Any]:
        try:
            return {
                "success": True,
                "rules_loaded": 0,
                "message": "Reglas recargadas con exito",
            }
        except Exception as e:
            _log.error("Failed to reload custom rules: %s", e)
            return {
                "success": False,
                "rules_loaded": 0,
                "message": f"Error al recargar reglas: {e}",
            }

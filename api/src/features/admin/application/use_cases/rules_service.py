import logging
from typing import Dict, Any
from features.admin.application.ports.i_rules_service import IRulesService
from features.verification.application.ports.i_verification_rule_repository import IVerificationRuleRepository

_log = logging.getLogger(__name__)


class RulesService(IRulesService):
    def __init__(self, rule_repository: IVerificationRuleRepository) -> None:
        self._repo = rule_repository

    async def reload_custom_rules(self) -> Dict[str, Any]:
        try:
            rules = await self._repo.list_all()
            return {
                "success": True,
                "rules_loaded": len(rules),
                "message": "Reglas recargadas con exito",
            }
        except Exception as e:
            _log.exception("Failed to reload custom rules")
            return {
                "success": False,
                "rules_loaded": 0,
                "message": f"Error al recargar reglas: {e}",
            }

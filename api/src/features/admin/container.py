from __future__ import annotations

from bootstrap.repositories import get_rule_repository
from features.admin.application.ports.i_rules_service import IRulesService
from features.admin.application.use_cases.rules_service import RulesService


def get_rules_service() -> IRulesService:
    rule_repo = get_rule_repository()
    return RulesService(
        rule_repository=rule_repo,
    )

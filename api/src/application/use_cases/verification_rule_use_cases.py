import uuid
from dataclasses import dataclass, field
from typing import List, Optional

from domain.entities.verification_rule import VerificationRule
from domain.exceptions import EntityNotFoundError
from domain.ports.i_verification_rule_repository import IVerificationRuleRepository
from domain.ports.i_profile_repository import IProfileRepository

_VALID_TEMPLATES = {f"RV-{i:02d}" for i in range(1, 11)}
_VALID_SEVERITIES = {"OBLIGATORIA", "RECOMENDADA", "INFORMATIVA"}


@dataclass
class CreateRuleCommand:
    profile_id: uuid.UUID
    rule_template: str
    severity: str = "OBLIGATORIA"
    params: dict = field(default_factory=dict)
    connector_instance_id: Optional[uuid.UUID] = None
    display_order: int = 0


@dataclass
class UpdateRuleCommand:
    rule_id: uuid.UUID
    profile_id: uuid.UUID
    rule_template: Optional[str] = None
    severity: Optional[str] = None
    params: Optional[dict] = None
    connector_instance_id: Optional[uuid.UUID] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


class CreateRuleUseCase:
    def __init__(self, rule_repo: IVerificationRuleRepository, profile_repo: IProfileRepository) -> None:
        self.rule_repo = rule_repo
        self.profile_repo = profile_repo

    async def execute(self, command: CreateRuleCommand) -> VerificationRule:
        profile = await self.profile_repo.get_by_id(command.profile_id)
        if not profile:
            raise EntityNotFoundError(f"Profile {command.profile_id} not found")
        if command.rule_template not in _VALID_TEMPLATES:
            raise ValueError(f"Invalid rule_template: {command.rule_template}")
        if command.severity not in _VALID_SEVERITIES:
            raise ValueError(f"Invalid severity: {command.severity}")
        rule = VerificationRule(
            profile_id=command.profile_id,
            rule_template=command.rule_template,
            severity=command.severity,
            params=command.params,
            connector_instance_id=command.connector_instance_id,
            display_order=command.display_order,
        )
        return await self.rule_repo.create(rule)


class ListRulesUseCase:
    def __init__(self, rule_repo: IVerificationRuleRepository, profile_repo: IProfileRepository) -> None:
        self.rule_repo = rule_repo
        self.profile_repo = profile_repo

    async def execute(self, profile_id: uuid.UUID) -> List[VerificationRule]:
        profile = await self.profile_repo.get_by_id(profile_id)
        if not profile:
            raise EntityNotFoundError(f"Profile {profile_id} not found")
        return await self.rule_repo.list_by_profile(profile_id)


class GetRuleUseCase:
    def __init__(self, rule_repo: IVerificationRuleRepository) -> None:
        self.rule_repo = rule_repo

    async def execute(self, profile_id: uuid.UUID, rule_id: uuid.UUID) -> VerificationRule:
        rule = await self.rule_repo.get_by_id(rule_id)
        if not rule or rule.profile_id != profile_id:
            raise EntityNotFoundError(f"Rule {rule_id} not found")
        return rule


class UpdateRuleUseCase:
    def __init__(self, rule_repo: IVerificationRuleRepository) -> None:
        self.rule_repo = rule_repo

    async def execute(self, command: UpdateRuleCommand) -> VerificationRule:
        rule = await self.rule_repo.get_by_id(command.rule_id)
        if not rule or rule.profile_id != command.profile_id:
            raise EntityNotFoundError(f"Rule {command.rule_id} not found")
        if command.rule_template is not None:
            if command.rule_template not in _VALID_TEMPLATES:
                raise ValueError(f"Invalid rule_template: {command.rule_template}")
            rule.rule_template = command.rule_template
        if command.severity is not None:
            if command.severity not in _VALID_SEVERITIES:
                raise ValueError(f"Invalid severity: {command.severity}")
            rule.severity = command.severity
        if command.params is not None:
            rule.params = command.params
        if command.connector_instance_id is not None:
            rule.connector_instance_id = command.connector_instance_id
        if command.display_order is not None:
            rule.display_order = command.display_order
        if command.is_active is not None:
            rule.is_active = command.is_active
        return await self.rule_repo.update(rule)


class DeleteRuleUseCase:
    def __init__(self, rule_repo: IVerificationRuleRepository) -> None:
        self.rule_repo = rule_repo

    async def execute(self, profile_id: uuid.UUID, rule_id: uuid.UUID) -> None:
        rule = await self.rule_repo.get_by_id(rule_id)
        if not rule or rule.profile_id != profile_id:
            raise EntityNotFoundError(f"Rule {rule_id} not found")
        await self.rule_repo.delete(rule_id)

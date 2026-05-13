from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.verification_rule import VerificationRule
from domain.ports.i_verification_rule_repository import IVerificationRuleRepository
from api.src.infrastructure.secondary.database.models.verification_rule import VerificationRuleModel


class SqlVerificationRuleRepository(IVerificationRuleRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, rule: VerificationRule) -> VerificationRule:
        model = VerificationRuleModel(
            id=rule.id,
            profile_id=rule.profile_id,
            connector_instance_id=rule.connector_instance_id,
            rule_template=rule.rule_template,
            params=rule.params,
            severity=rule.severity,
            display_order=rule.display_order,
            is_active=rule.is_active,
        )
        self.session.add(model)
        await self.session.flush()
        return rule

    async def get_by_id(self, rule_id: UUID) -> Optional[VerificationRule]:
        model = await self.session.get(VerificationRuleModel, rule_id)
        return self._to_entity(model) if model else None

    async def list_by_profile(self, profile_id: UUID) -> List[VerificationRule]:
        result = await self.session.execute(
            select(VerificationRuleModel)
            .where(VerificationRuleModel.profile_id == profile_id)
            .order_by(VerificationRuleModel.display_order, VerificationRuleModel.created_at)
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def update(self, rule: VerificationRule) -> VerificationRule:
        model = await self.session.get(VerificationRuleModel, rule.id)
        if model:
            model.rule_template = rule.rule_template
            model.params = rule.params
            model.severity = rule.severity
            model.connector_instance_id = rule.connector_instance_id
            model.display_order = rule.display_order
            model.is_active = rule.is_active
            await self.session.flush()
        return rule

    async def delete(self, rule_id: UUID) -> None:
        model = await self.session.get(VerificationRuleModel, rule_id)
        if model:
            await self.session.delete(model)
            await self.session.flush()

    def _to_entity(self, model: VerificationRuleModel) -> VerificationRule:
        return VerificationRule(
            id=model.id,
            profile_id=model.profile_id,
            rule_template=model.rule_template,
            severity=model.severity,
            params=model.params or {},
            connector_instance_id=model.connector_instance_id,
            display_order=model.display_order,
            is_active=model.is_active,
            created_at=model.created_at,
        )

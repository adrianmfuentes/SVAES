from typing import List, Optional, cast
import uuid
from datetime import datetime
from application.ports.output.i_verification_rule_repository import IVerificationRuleRepository
from domain.entities.verification_rule import VerificationRule
from domain.enums import SeverityType
from infrastructure.secondary.database.models.rule_model import VerificationRuleModel
from infrastructure.secondary.database.get_async_session import AsyncSessionLocal
from sqlalchemy.future import select


class SqlVerificationRuleRepository(IVerificationRuleRepository):
    def _model_to_entity(self, row: VerificationRuleModel) -> VerificationRule:
        return VerificationRule(
            id=cast(uuid.UUID, row.id),
            profile_id=cast(uuid.UUID, row.profile_id),
            rule_template=cast(str, row.rule_template),
            severity=SeverityType(row.severity),
            params=cast(dict, row.params) or {},
            connector_instance_id=cast(uuid.UUID | None, row.connector_instance_id),
            display_order=cast(int, row.display_order),
            is_active=cast(bool, row.is_active),
            created_at=cast(datetime, row.created_at),
        )

    def _entity_to_model_attrs(self, entity: VerificationRule) -> dict:
        return {
            "profile_id": entity.profile_id,
            "rule_template": entity.rule_template,
            "severity": entity.severity.value,
            "params": entity.params,
            "connector_instance_id": entity.connector_instance_id,
            "display_order": entity.display_order,
            "is_active": entity.is_active,
            "created_at": entity.created_at,
        }

    async def create(self, rule: VerificationRule) -> VerificationRule:
        async with AsyncSessionLocal() as session:
            model = VerificationRuleModel(**self._entity_to_model_attrs(rule))
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return self._model_to_entity(model)

    async def get_by_id(self, rule_id: uuid.UUID) -> Optional[VerificationRule]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(VerificationRuleModel).where(VerificationRuleModel.id == rule_id))
            row = result.scalar_one_or_none()
            if row is None:
                return None
            return self._model_to_entity(row)

    async def list_all(self) -> List[VerificationRule]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(VerificationRuleModel))
            rows = result.scalars().all()
            return [self._model_to_entity(row) for row in rows]

    async def list_by_profile(self, profile_id: uuid.UUID) -> List[VerificationRule]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(VerificationRuleModel)
                .where(VerificationRuleModel.profile_id == profile_id)
                .order_by(VerificationRuleModel.display_order)
            )
            rows = result.scalars().all()
            return [self._model_to_entity(row) for row in rows]

    async def update(self, rule: VerificationRule) -> VerificationRule:
        async with AsyncSessionLocal() as session:
            model = await session.get(VerificationRuleModel, rule.id)
            if not model:
                raise ValueError("Rule not found")
            for key, value in self._entity_to_model_attrs(rule).items():
                setattr(model, key, value)
            await session.commit()
            await session.refresh(model)
            return self._model_to_entity(model)

    async def delete(self, rule_id: uuid.UUID) -> None:
        async with AsyncSessionLocal() as session:
            model = await session.get(VerificationRuleModel, rule_id)
            if not model:
                raise ValueError("Rule not found")
            session.delete(model)  # pyright: ignore[reportUnusedCoroutine]
            await session.commit()
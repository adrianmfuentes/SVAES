from sqlalchemy.future import select
from typing import List, Optional
import uuid
from datetime import datetime
from application.ports.output.i_verification_rule_repository import IVerificationRuleRepository
from domain.entities.verification_rule import VerificationRule
from domain.enums import SeverityType
from infrastructure.secondary.database.models.rule_model import VerificationRuleModel
from infrastructure.secondary.database.get_async_session import get_async_session


class SqlVerificationRuleRepository(IVerificationRuleRepository):
    async def create(self, rule: VerificationRule) -> VerificationRule:
        session = await get_async_session().__anext__()

        try:
            rule_model = VerificationRuleModel(
                id=rule.id,
                profile_id=rule.profile_id,
                rule_template=rule.rule_template,
                severity=rule.severity.value,
                params=rule.params,
                connector_instance_id=rule.connector_instance_id,
                display_order=rule.display_order,
                is_active=rule.is_active,
                created_at=rule.created_at,
            )
            session.add(rule_model)
            await session.commit()
            await session.refresh(rule_model)

            return VerificationRule(
                id=rule_model.id,
                profile_id=rule_model.profile_id,
                rule_template=rule_model.rule_template,
                severity=SeverityType(rule_model.severity),
                params=rule_model.params or {},
                connector_instance_id=rule_model.connector_instance_id,
                display_order=rule_model.display_order,
                is_active=rule_model.is_active,
                created_at=rule_model.created_at,
            )
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def get_by_id(self, rule_id: uuid.UUID) -> Optional[VerificationRule]:
        session = await get_async_session().__anext__()

        try:
            result = await session.execute(select(VerificationRuleModel).where(VerificationRuleModel.id == rule_id))
            rule_row = result.scalar_one_or_none()
            if not rule_row:
                return None

            return VerificationRule(
                id=rule_row.id,
                profile_id=rule_row.profile_id,
                rule_template=rule_row.rule_template,
                severity=SeverityType(rule_row.severity),
                params=rule_row.params or {},
                connector_instance_id=rule_row.connector_instance_id,
                display_order=rule_row.display_order,
                is_active=rule_row.is_active,
                created_at=rule_row.created_at,
            )
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def list_by_profile(self, profile_id: uuid.UUID) -> List[VerificationRule]:
        session = await get_async_session().__anext__()

        try:
            result = await session.execute(
                select(VerificationRuleModel)
                .where(VerificationRuleModel.profile_id == profile_id)
                .order_by(VerificationRuleModel.display_order)
            )
            rule_rows = result.scalars().all()

            return [
                VerificationRule(
                    id=row.id,
                    profile_id=row.profile_id,
                    rule_template=row.rule_template,
                    severity=SeverityType(row.severity),
                    params=row.params or {},
                    connector_instance_id=row.connector_instance_id,
                    display_order=row.display_order,
                    is_active=row.is_active,
                    created_at=row.created_at,
                )
                for row in rule_rows
            ]
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def update(self, rule: VerificationRule) -> VerificationRule:
        session = await get_async_session().__anext__()

        try:
            rule_model = await session.get(VerificationRuleModel, rule.id)
            if not rule_model:
                raise ValueError("Rule not found")

            rule_model.rule_template = rule.rule_template
            rule_model.severity = rule.severity.value
            rule_model.params = rule.params
            rule_model.connector_instance_id = rule.connector_instance_id
            rule_model.display_order = rule.display_order
            rule_model.is_active = rule.is_active

            await session.commit()
            await session.refresh(rule_model)

            return VerificationRule(
                id=rule_model.id,
                profile_id=rule_model.profile_id,
                rule_template=rule_model.rule_template,
                severity=SeverityType(rule_model.severity),
                params=rule_model.params or {},
                connector_instance_id=rule_model.connector_instance_id,
                display_order=rule_model.display_order,
                is_active=rule_model.is_active,
                created_at=rule_model.created_at,
            )
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def delete(self, rule_id: uuid.UUID) -> None:
        session = await get_async_session().__anext__()

        try:
            rule_model = await session.get(VerificationRuleModel, rule_id)
            if not rule_model:
                raise ValueError("Rule not found")

            await session.delete(rule_model)
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()
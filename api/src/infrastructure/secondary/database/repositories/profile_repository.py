from sqlalchemy.future import select
from sqlalchemy import or_
from typing import Optional, List, cast
import uuid
from datetime import datetime, timezone
from application.ports.output.i_profile_repository import IProfileRepository
from domain.entities.verification_profile import VerificationProfile
from domain.entities.verification_rule import VerificationRule
from domain.enums import SeverityType
from infrastructure.secondary.database.models.profile_model import VerificationProfileModel
from infrastructure.secondary.database.models.rule_model import VerificationRuleModel
from infrastructure.secondary.database.get_async_session import AsyncSessionLocal


def _row_to_entity(row: VerificationProfileModel, rules: list[VerificationRule]) -> VerificationProfile:
    return VerificationProfile(
        id=cast(uuid.UUID, row.id),
        organization_id=cast(uuid.UUID | None, row.organization_id),
        name=cast(str, row.name),
        description=cast(str, row.description) or "",
        is_default=cast(bool, row.is_default),
        is_system=cast(bool, row.is_system),
        rules=rules,
        created_at=cast(datetime, row.created_at),
        updated_at=cast(datetime, row.updated_at),
    )


def _rule_row_to_entity(r: VerificationRuleModel) -> VerificationRule:
    return VerificationRule(
        id=cast(uuid.UUID, r.id),
        profile_id=cast(uuid.UUID, r.profile_id),
        rule_template=cast(str, r.rule_template),
        severity=SeverityType(r.severity),
        params=cast(dict, r.params) or {},
        connector_instance_id=cast(uuid.UUID | None, r.connector_instance_id),
        display_order=cast(int, r.display_order),
        is_active=cast(bool, r.is_active),
        created_at=cast(datetime, r.created_at),
    )


class SqlProfileRepository(IProfileRepository):
    async def create(self, profile: VerificationProfile) -> VerificationProfile:
        async with AsyncSessionLocal() as session:
            profile_model = VerificationProfileModel(
                id=profile.id,
                organization_id=profile.organization_id,
                name=profile.name,
                description=profile.description,
                is_default=profile.is_default,
                is_system=profile.is_system,
                rules=[],
                created_at=profile.created_at,
                updated_at=profile.updated_at,
            )
            session.add(profile_model)
            await session.commit()
            await session.refresh(profile_model)
            return _row_to_entity(profile_model, [])

    async def get_by_id(self, profile_id: uuid.UUID) -> Optional[VerificationProfile]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(VerificationProfileModel).where(VerificationProfileModel.id == profile_id)
            )
            profile_row = result.scalar_one_or_none()
            if not profile_row:
                return None

            rules_result = await session.execute(
                select(VerificationRuleModel)
                .where(VerificationRuleModel.profile_id == profile_id)
                .order_by(VerificationRuleModel.display_order)
            )
            rules = [_rule_row_to_entity(r) for r in rules_result.scalars().all()]
            return _row_to_entity(profile_row, rules)

    async def get_default_for_organization(self, organization_id: uuid.UUID) -> Optional[VerificationProfile]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(VerificationProfileModel)
                .where(VerificationProfileModel.organization_id == organization_id)
                .where(VerificationProfileModel.is_default == True)
            )
            profile_row = result.scalar_one_or_none()
            if not profile_row:
                return None
            return await self.get_by_id(cast(uuid.UUID, profile_row.id))

    async def get_system_profile(self) -> Optional[VerificationProfile]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(VerificationProfileModel)
                .where(VerificationProfileModel.is_system == True)
                .limit(1)
            )
            profile_row = result.scalar_one_or_none()
            if not profile_row:
                return None
            return await self.get_by_id(cast(uuid.UUID, profile_row.id))

    async def update(self, profile: VerificationProfile) -> VerificationProfile:
        async with AsyncSessionLocal() as session:
            profile_model = await session.get(VerificationProfileModel, profile.id)
            if not profile_model:
                raise ValueError("Profile not found")

            profile_model.name = profile.name  # pyright: ignore[reportAttributeAccessIssue]
            profile_model.description = profile.description  # pyright: ignore[reportAttributeAccessIssue]
            profile_model.is_default = profile.is_default  # pyright: ignore[reportAttributeAccessIssue]
            profile_model.updated_at = datetime.now(timezone.utc)  # pyright: ignore[reportAttributeAccessIssue]

            await session.commit()
            await session.refresh(profile_model)
            return _row_to_entity(profile_model, profile.rules)

    async def list_by_organization(self, organization_id: uuid.UUID, skip: int = 0, limit: int = 50) -> List[VerificationProfile]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(VerificationProfileModel)
                .where(
                    or_(
                        VerificationProfileModel.organization_id == organization_id,
                        VerificationProfileModel.is_system == True,
                    )
                )
                .order_by(
                    VerificationProfileModel.is_system.desc(),
                    VerificationProfileModel.created_at.asc(),
                )
                .offset(skip)
                .limit(limit)
            )
            profile_rows = result.scalars().all()

            profiles = []
            for row in profile_rows:
                rules_result = await session.execute(
                    select(VerificationRuleModel)
                    .where(VerificationRuleModel.profile_id == row.id)
                    .order_by(VerificationRuleModel.display_order)
                )
                rules = [_rule_row_to_entity(r) for r in rules_result.scalars().all()]
                profiles.append(_row_to_entity(row, rules))

            return profiles

    async def delete(self, profile_id: uuid.UUID) -> None:
        async with AsyncSessionLocal() as session:
            profile_model = await session.get(VerificationProfileModel, profile_id)
            if not profile_model:
                raise ValueError("Profile not found")

            await session.delete(profile_model)
            await session.commit()

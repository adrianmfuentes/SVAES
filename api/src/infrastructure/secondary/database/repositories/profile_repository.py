from sqlalchemy.future import select
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


class SqlProfileRepository(IProfileRepository):
    async def create(self, profile: VerificationProfile) -> VerificationProfile:
        async with AsyncSessionLocal() as session:
            profile_model = VerificationProfileModel(
                id=profile.id,
                organization_id=profile.organization_id,
                name=profile.name,
                description=profile.description,
                is_default=profile.is_default,
                rules=[],
                created_at=profile.created_at,
                updated_at=profile.updated_at,
            )
            session.add(profile_model)
            await session.commit()
            await session.refresh(profile_model)

            return VerificationProfile(
                id=cast(uuid.UUID, profile_model.id),
                organization_id=cast(uuid.UUID, profile_model.organization_id),
                name=cast(str, profile_model.name),
                description=cast(str, profile_model.description),
                is_default=cast(bool, profile_model.is_default),
                rules=[],
                created_at=cast(datetime, profile_model.created_at),
                updated_at=cast(datetime, profile_model.updated_at),
            )

    async def get_by_id(self, profile_id: uuid.UUID) -> Optional[VerificationProfile]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(VerificationProfileModel).where(VerificationProfileModel.id == profile_id))
            profile_row = result.scalar_one_or_none()
            if not profile_row:
                return None

            rules_result = await session.execute(
                select(VerificationRuleModel)
                .where(VerificationRuleModel.profile_id == profile_id)
                .order_by(VerificationRuleModel.display_order)
            )
            rule_rows = rules_result.scalars().all()
            rules = [
                VerificationRule(
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
                for row in rule_rows
            ]

            return VerificationProfile(
                id=cast(uuid.UUID, profile_row.id),
                organization_id=cast(uuid.UUID, profile_row.organization_id),
                name=cast(str, profile_row.name),
                description=cast(str, profile_row.description),
                is_default=cast(bool, profile_row.is_default),
                rules=rules,
                created_at=cast(datetime, profile_row.created_at),
                updated_at=cast(datetime, profile_row.updated_at),
            )

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

    async def update(self, profile: VerificationProfile) -> VerificationProfile:
        async with AsyncSessionLocal() as session:
            profile_model = await session.get(VerificationProfileModel, profile.id)
            if not profile_model:
                raise ValueError("Profile not found")

            profile_model.name = profile.name  # pyright: ignore[reportAttributeAccessIssue]
            profile_model.description = profile.description  # pyright: ignore[reportAttributeAccessIssue]
            profile_model.is_default = profile.is_default  # pyright: ignore[reportAttributeAccessIssue]
            profile_model.updated_at = datetime.now(timezone.utc)

            await session.commit()
            await session.refresh(profile_model)

            return VerificationProfile(
                id=cast(uuid.UUID, profile_model.id),
                organization_id=cast(uuid.UUID, profile_model.organization_id),
                name=cast(str, profile_model.name),
                description=cast(str, profile_model.description),
                is_default=cast(bool, profile_model.is_default),
                rules=profile.rules,
                created_at=cast(datetime, profile_model.created_at),
                updated_at=cast(datetime, profile_model.updated_at),
            )

    async def list_by_organization(self, organization_id: uuid.UUID, skip: int = 0, limit: int = 50) -> List[VerificationProfile]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(VerificationProfileModel)
                .where(VerificationProfileModel.organization_id == organization_id)
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
                rule_rows = rules_result.scalars().all()
                rules = [
                    VerificationRule(
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
                    for r in rule_rows
                ]
                profiles.append(
                    VerificationProfile(
                        id=cast(uuid.UUID, row.id),
                        organization_id=cast(uuid.UUID, row.organization_id),
                        name=cast(str, row.name),
                        description=cast(str, row.description),
                        is_default=cast(bool, row.is_default),
                        rules=rules,
                        created_at=cast(datetime, row.created_at),
                        updated_at=cast(datetime, row.updated_at),
                    )
                )

            return profiles

    async def delete(self, profile_id: uuid.UUID) -> None:
        async with AsyncSessionLocal() as session:
            profile_model = await session.get(VerificationProfileModel, profile_id)
            if not profile_model:
                raise ValueError("Profile not found")

            await session.delete(profile_model)
            await session.commit()
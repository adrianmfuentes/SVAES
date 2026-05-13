from sqlalchemy.future import select
from typing import Optional, List
import uuid
from datetime import datetime
from application.ports.output.i_profile_repository import IProfileRepository
from domain.entities.verification_profile import VerificationProfile
from domain.entities.verification_rule import VerificationRule
from domain.enums import SeverityType
from infrastructure.secondary.database.models.profile_model import VerificationProfileModel
from infrastructure.secondary.database.models.rule_model import VerificationRuleModel
from infrastructure.secondary.database.get_async_session import get_async_session


class SqlProfileRepository(IProfileRepository):
    async def create(self, profile: VerificationProfile) -> VerificationProfile:
        session = await get_async_session().__anext__()

        try:
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
                id=profile_model.id,
                organization_id=profile_model.organization_id,
                name=profile_model.name,
                description=profile_model.description,
                is_default=profile_model.is_default,
                rules=[],
                created_at=profile_model.created_at,
                updated_at=profile_model.updated_at,
            )
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def get_by_id(self, profile_id: uuid.UUID) -> Optional[VerificationProfile]:
        session = await get_async_session().__anext__()

        try:
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

            return VerificationProfile(
                id=profile_row.id,
                organization_id=profile_row.organization_id,
                name=profile_row.name,
                description=profile_row.description,
                is_default=profile_row.is_default,
                rules=rules,
                created_at=profile_row.created_at,
                updated_at=profile_row.updated_at,
            )
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def get_default_for_organization(self, organization_id: uuid.UUID) -> Optional[VerificationProfile]:
        session = await get_async_session().__anext__()

        try:
            result = await session.execute(
                select(VerificationProfileModel)
                .where(VerificationProfileModel.organization_id == organization_id)
                .where(VerificationProfileModel.is_default == True)
            )
            profile_row = result.scalar_one_or_none()
            if not profile_row:
                return None

            return await self.get_by_id(profile_row.id)
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def update(self, profile: VerificationProfile) -> VerificationProfile:
        session = await get_async_session().__anext__()

        try:
            profile_model = await session.get(VerificationProfileModel, profile.id)
            if not profile_model:
                raise ValueError("Profile not found")

            profile_model.name = profile.name
            profile_model.description = profile.description
            profile_model.is_default = profile.is_default
            profile_model.updated_at = datetime.utcnow()

            await session.commit()
            await session.refresh(profile_model)

            return VerificationProfile(
                id=profile_model.id,
                organization_id=profile_model.organization_id,
                name=profile_model.name,
                description=profile_model.description,
                is_default=profile_model.is_default,
                rules=profile.rules,
                created_at=profile_model.created_at,
                updated_at=profile_model.updated_at,
            )
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def list_by_organization(self, organization_id: uuid.UUID, skip: int = 0, limit: int = 50) -> List[VerificationProfile]:
        session = await get_async_session().__anext__()

        try:
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
                        id=r.id,
                        profile_id=r.profile_id,
                        rule_template=r.rule_template,
                        severity=SeverityType(r.severity),
                        params=r.params or {},
                        connector_instance_id=r.connector_instance_id,
                        display_order=r.display_order,
                        is_active=r.is_active,
                        created_at=r.created_at,
                    )
                    for r in rule_rows
                ]
                profiles.append(
                    VerificationProfile(
                        id=row.id,
                        organization_id=row.organization_id,
                        name=row.name,
                        description=row.description,
                        is_default=row.is_default,
                        rules=rules,
                        created_at=row.created_at,
                        updated_at=row.updated_at,
                    )
                )

            return profiles
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def delete(self, profile_id: uuid.UUID) -> None:
        session = await get_async_session().__anext__()

        try:
            profile_model = await session.get(VerificationProfileModel, profile_id)
            if not profile_model:
                raise ValueError("Profile not found")

            await session.delete(profile_model)
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()
from uuid import UUID
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from domain.entities.verification_profile import VerificationProfile
from domain.entities.verification_rule import VerificationRule
from domain.ports.i_profile_repository import IProfileRepository
from infrastructure.database.models.verification_profile import VerificationProfileModel


class SqlProfileRepository(IProfileRepository):
    """Async SQLAlchemy adapter for IProfileRepository.

    Uses selectinload for the rules relationship to avoid MissingGreenlet errors
    in async context (lazy loading is not available with AsyncSession).
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, profile: VerificationProfile) -> VerificationProfile:
        model = VerificationProfileModel(
            id=profile.id,
            organization_id=profile.organization_id,
            name=profile.name,
            is_default=False,
        )
        self.session.add(model)
        await self.session.flush()
        return profile

    async def get_by_id(self, profile_id: UUID) -> Optional[VerificationProfile]:
        result = await self.session.execute(
            select(VerificationProfileModel)
            .options(selectinload(VerificationProfileModel.rules))
            .where(VerificationProfileModel.id == profile_id)
        )
        model = result.scalars().first()
        return self._to_entity(model) if model else None

    async def get_default_for_organization(self, organization_id: UUID) -> Optional[VerificationProfile]:
        result = await self.session.execute(
            select(VerificationProfileModel)
            .options(selectinload(VerificationProfileModel.rules))
            .where(
                VerificationProfileModel.organization_id == organization_id,
                VerificationProfileModel.is_default.is_(True),
            )
        )
        model = result.scalars().first()
        return self._to_entity(model) if model else None

    def _to_entity(self, model: VerificationProfileModel) -> VerificationProfile:
        rules = [
            VerificationRule(
                rule_id=r.rule_template,
                enabled=r.is_active,
                config=r.params or {},
            )
            for r in model.rules
        ]
        return VerificationProfile(
            id=model.id,
            organization_id=model.organization_id,
            name=model.name,
            rules=rules,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

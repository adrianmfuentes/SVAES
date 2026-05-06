from uuid import UUID
from sqlalchemy.orm import Session
from domain.entities.verification_profile import VerificationProfile
from domain.entities.verification_rule import VerificationRule
from domain.ports.i_profile_repository import IProfileRepository
from infrastructure.database.models.verification_profile import VerificationProfileModel

class SqlProfileRepository(IProfileRepository):
    def __init__(self, session: Session):
        self.session = session

    def save(self, profile: VerificationProfile) -> VerificationProfile:
        model = self.session.get(VerificationProfileModel, profile.id)
        if model is None:
            model = VerificationProfileModel(
                id=profile.id,
                organization_id=profile.organization_id,
                name=profile.name,
                is_default=False,
            )
            self.session.add(model)
        else:
            model.name = profile.name
        self.session.flush()
        return profile

    def find_by_id(self, profile_id: UUID) -> VerificationProfile | None:
        model = self.session.get(VerificationProfileModel, profile_id)
        return self._to_entity(model) if model else None

    def find_by_organization(self, organization_id: UUID) -> list[VerificationProfile]:
        models = (
            self.session.query(VerificationProfileModel)
            .filter_by(organization_id=organization_id)
            .all()
        )
        return [self._to_entity(m) for m in models]

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
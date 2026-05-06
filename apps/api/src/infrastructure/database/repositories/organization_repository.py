from uuid import UUID
from sqlalchemy.orm import Session
from domain.entities.organization import Organization
from domain.ports.i_organization_repository import IOrganizationRepository
from infrastructure.database.models.organization import OrganizationModel

class SqlOrganizationRepository(IOrganizationRepository):
    def __init__(self, session: Session):
        self.session = session

    def save(self, organization: Organization) -> Organization:
        model = self.session.get(OrganizationModel, organization.id)
        if model is None:
            model = OrganizationModel(
                id=organization.id,
                name=organization.name,
                slug=organization.slug,
                is_active=organization.is_active,
            )
            self.session.add(model)
        else:
            model.name = organization.name
            model.slug = organization.slug
            model.is_active = organization.is_active
        self.session.flush()
        return organization

    def find_by_id(self, organization_id: UUID) -> Organization | None:
        model = self.session.get(OrganizationModel, organization_id)
        return self._to_entity(model) if model else None

    def find_all(self) -> list[Organization]:
        models = self.session.query(OrganizationModel).all()
        return [self._to_entity(m) for m in models]

    def _to_entity(self, model: OrganizationModel) -> Organization:
        return Organization(
            id=model.id,
            name=model.name,
            slug=model.slug,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
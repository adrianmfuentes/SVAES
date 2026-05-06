from uuid import UUID
from sqlalchemy.orm import Session
from domain.entities.release import Release, ReleaseStatus
from domain.ports.i_release_repository import IReleaseRepository
from infrastructure.database.models.release import ReleaseModel

class SqlReleaseRepository(IReleaseRepository):
    def __init__(self, session: Session):
        self.session = session

    def save(self, release: Release) -> Release:
        model = self.session.get(ReleaseModel, release.id)
        if model is None:
            model = ReleaseModel(
                id=release.id,
                project_id=release.project_id,
                profile_id=release.profile_id,
                version=release.version,
                status=release.status.value,
                description=release.description,
            )
            self.session.add(model)
        else:
            model.status = release.status.value
            model.description = release.description
        self.session.flush()
        return release

    def find_by_id(self, release_id: UUID) -> Release | None:
        model = self.session.get(ReleaseModel, release_id)
        return self._to_entity(model) if model else None

    def find_by_organization(self, organization_id: UUID) -> list[Release]:
        models = (
            self.session.query(ReleaseModel)
            .join(ReleaseModel.project)
            .filter_by(organization_id=organization_id)
            .all()
        )
        return [self._to_entity(m) for m in models]

    def _to_entity(self, model: ReleaseModel) -> Release:
        return Release(
            id=model.id,
            project_id=model.project_id,
            profile_id=model.profile_id,
            version=model.version,
            created_by=model.created_by,
            status=ReleaseStatus(model.status),
            description=model.description,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
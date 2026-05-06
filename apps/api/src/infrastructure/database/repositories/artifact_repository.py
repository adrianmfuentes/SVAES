from uuid import UUID
from sqlalchemy.orm import Session
from domain.entities.artifact import Artifact
from domain.ports.i_artifact_repository import IArtifactRepository
from infrastructure.database.models.artifact import ArtifactModel

class SqlArtifactRepository(IArtifactRepository):
    def __init__(self, session: Session):
        self.session = session

    def save(self, artifact: Artifact) -> Artifact:
        model = self.session.get(ArtifactModel, artifact.id)
        if model is None:
            model = ArtifactModel(
                id=artifact.id,
                release_id=artifact.release_id,
                connector_instance_id=artifact.connector_instance_id,
                artifact_type=artifact.artifact_type,
                external_ref=artifact.external_ref,
                metadata_=artifact.metadata,
            )
            self.session.add(model)
        else:
            model.artifact_type = artifact.artifact_type
            model.external_ref = artifact.external_ref
            model.metadata_ = artifact.metadata
        self.session.flush()
        return artifact

    def find_by_id(self, artifact_id: UUID) -> Artifact | None:
        model = self.session.get(ArtifactModel, artifact_id)
        return self._to_entity(model) if model else None

    def find_by_release(self, release_id: UUID) -> list[Artifact]:
        models = (
            self.session.query(ArtifactModel)
            .filter_by(release_id=release_id)
            .all()
        )
        return [self._to_entity(m) for m in models]

    def _to_entity(self, model: ArtifactModel) -> Artifact:
        return Artifact(
            id=model.id,
            release_id=model.release_id,
            connector_instance_id=model.connector_instance_id,
            artifact_type=model.artifact_type,
            external_ref=model.external_ref,
            metadata=model.metadata_ or {},
            created_at=model.created_at,
        )
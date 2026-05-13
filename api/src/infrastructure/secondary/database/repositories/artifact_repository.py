from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from domain.entities.artifact import Artifact
from domain.ports.i_artifact_repository import IArtifactRepository
from api.src.infrastructure.secondary.database.models.artifact import ArtifactModel


class SqlArtifactRepository(IArtifactRepository):
    """Async SQLAlchemy adapter — used by FastAPI request handlers."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, artifact: Artifact) -> Artifact:
        model = await self.session.get(ArtifactModel, artifact.id)
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
        await self.session.flush()
        return artifact

    async def find_by_id(self, artifact_id: UUID) -> Optional[Artifact]:
        model = await self.session.get(ArtifactModel, artifact_id)
        return self._to_entity(model) if model else None

    async def find_by_release(self, release_id: UUID, skip: int = 0, limit: int = 100) -> List[Artifact]:
        result = await self.session.execute(
            select(ArtifactModel).where(ArtifactModel.release_id == release_id)
            .offset(skip).limit(limit)
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def delete(self, artifact_id: UUID) -> None:
        model = await self.session.get(ArtifactModel, artifact_id)
        if model:
            await self.session.delete(model)
            await self.session.flush()

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


class SyncSqlArtifactRepository:
    """Sync SQLAlchemy adapter — used by Celery workers (no event loop)."""

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

    def find_by_release(self, release_id: UUID) -> List[Artifact]:
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

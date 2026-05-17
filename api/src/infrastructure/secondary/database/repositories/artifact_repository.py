from sqlalchemy.future import select
from typing import List, Optional, cast
import uuid
from datetime import datetime
from application.ports.output.i_artifact_repository import IArtifactRepository
from domain.entities.artifact import Artifact
from domain.enums import ArtifactType
from infrastructure.secondary.database.models.artifact_model import ArtifactModel
from infrastructure.secondary.database.repositories.base_sql_repository import _session_scope


class SqlArtifactRepository(IArtifactRepository):
    async def save(self, artifact: Artifact) -> Artifact:
        async with _session_scope() as session:
            artifact_model = ArtifactModel(
                id=artifact.id,
                release_id=artifact.release_id,
                connector_instance_id=artifact.connector_instance_id,
                connector_implementation=artifact.connector_implementation,
                artifact_type=getattr(artifact.artifact_type, 'value', artifact.artifact_type),
                external_ref=artifact.external_ref,
                metadata=artifact.metadata,
                created_at=artifact.created_at,
            )
            session.add(artifact_model)
            await session.commit()
            await session.refresh(artifact_model)
            return Artifact(
                id=cast(uuid.UUID, artifact_model.id),
                release_id=cast(uuid.UUID, artifact_model.release_id),
                connector_instance_id=cast(uuid.UUID, artifact_model.connector_instance_id),
                connector_implementation=cast(str, artifact_model.connector_implementation),
                artifact_type=cast(str, artifact_model.artifact_type),
                external_ref=cast(str, artifact_model.external_ref),
                metadata=cast(dict, artifact_model.artifact_metadata) or {},
                created_at=cast(datetime, artifact_model.created_at),
            )

    async def find_by_id(self, artifact_id: uuid.UUID) -> Optional[Artifact]:
        async with _session_scope() as session:
            result = await session.execute(select(ArtifactModel).where(ArtifactModel.id == artifact_id))
            artifact_row = result.scalar_one_or_none()
            if not artifact_row:
                return None
            return Artifact(
                id=cast(uuid.UUID, artifact_row.id),
                release_id=cast(uuid.UUID, artifact_row.release_id),
                connector_instance_id=cast(uuid.UUID, artifact_row.connector_instance_id),
                connector_implementation=cast(str, artifact_row.connector_implementation),
                artifact_type=cast(str, artifact_row.artifact_type),
                external_ref=cast(str, artifact_row.external_ref),
                metadata=cast(dict, artifact_row.artifact_metadata) or {},
                created_at=cast(datetime, artifact_row.created_at),
            )

    async def find_by_release(self, release_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[Artifact]:
        async with _session_scope() as session:
            result = await session.execute(
                select(ArtifactModel)
                .where(ArtifactModel.release_id == release_id)
                .offset(skip)
                .limit(limit)
            )
            artifact_rows = result.scalars().all()
            return [
                Artifact(
                    id=cast(uuid.UUID, row.id),
                    release_id=cast(uuid.UUID, row.release_id),
                    connector_instance_id=cast(uuid.UUID, row.connector_instance_id),
                    connector_implementation=cast(str, row.connector_implementation),
                    artifact_type=cast(str, row.artifact_type),
                    external_ref=cast(str, row.external_ref),
                    metadata=cast(dict, row.artifact_metadata) or {},
                    created_at=cast(datetime, row.created_at),
                )
                for row in artifact_rows
            ]

    async def delete(self, artifact_id: uuid.UUID) -> None:
        async with _session_scope() as session:
            artifact_model = await session.get(ArtifactModel, artifact_id)
            if not artifact_model:
                raise ValueError("Artifact not found")
            await session.delete(artifact_model)
            await session.commit()
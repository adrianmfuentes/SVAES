from sqlalchemy.future import select
from typing import List, Optional
import uuid
from datetime import datetime
from application.ports.output.i_artifact_repository import IArtifactRepository
from domain.entities.artifact import Artifact
from domain.enums import ArtifactType
from infrastructure.secondary.database.models.artifact_model import ArtifactModel
from infrastructure.secondary.database.get_async_session import get_async_session


class SqlArtifactRepository(IArtifactRepository):
    async def save(self, artifact: Artifact) -> Artifact:
        session = await get_async_session().__anext__()

        try:
            artifact_model = ArtifactModel(
                id=artifact.id,
                release_id=artifact.release_id,
                connector_instance_id=artifact.connector_instance_id,
                artifact_type=artifact.artifact_type.value if hasattr(artifact.artifact_type, 'value') else artifact.artifact_type,
                external_ref=artifact.external_ref,
                metadata=artifact.metadata,
                created_at=artifact.created_at,
            )
            session.add(artifact_model)
            await session.commit()
            await session.refresh(artifact_model)

            return Artifact(
                id=artifact_model.id,
                release_id=artifact_model.release_id,
                connector_instance_id=artifact_model.connector_instance_id,
                artifact_type=artifact_model.artifact_type,
                external_ref=artifact_model.external_ref,
                metadata=artifact_model.metadata or {},
                created_at=artifact_model.created_at,
            )
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def find_by_id(self, artifact_id: uuid.UUID) -> Optional[Artifact]:
        session = await get_async_session().__anext__()

        try:
            result = await session.execute(select(ArtifactModel).where(ArtifactModel.id == artifact_id))
            artifact_row = result.scalar_one_or_none()
            if not artifact_row:
                return None

            return Artifact(
                id=artifact_row.id,
                release_id=artifact_row.release_id,
                connector_instance_id=artifact_row.connector_instance_id,
                artifact_type=artifact_row.artifact_type,
                external_ref=artifact_row.external_ref,
                metadata=artifact_row.metadata or {},
                created_at=artifact_row.created_at,
            )
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def find_by_release(self, release_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[Artifact]:
        session = await get_async_session().__anext__()

        try:
            result = await session.execute(
                select(ArtifactModel)
                .where(ArtifactModel.release_id == release_id)
                .offset(skip)
                .limit(limit)
            )
            artifact_rows = result.scalars().all()

            return [
                Artifact(
                    id=row.id,
                    release_id=row.release_id,
                    connector_instance_id=row.connector_instance_id,
                    artifact_type=row.artifact_type,
                    external_ref=row.external_ref,
                    metadata=row.metadata or {},
                    created_at=row.created_at,
                )
                for row in artifact_rows
            ]
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def delete(self, artifact_id: uuid.UUID) -> None:
        session = await get_async_session().__anext__()

        try:
            artifact_model = await session.get(ArtifactModel, artifact_id)
            if not artifact_model:
                raise ValueError("Artifact not found")

            await session.delete(artifact_model)
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()
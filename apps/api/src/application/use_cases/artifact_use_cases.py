import uuid
from dataclasses import dataclass, field
from typing import List, Optional

from domain.entities.artifact import Artifact
from domain.exceptions import EntityNotFoundError
from domain.ports.i_artifact_repository import IArtifactRepository
from domain.ports.i_release_repository import IReleaseRepository


@dataclass
class RegisterArtifactCommand:
    release_id: uuid.UUID
    artifact_type: str
    external_ref: str
    connector_instance_id: Optional[uuid.UUID] = None
    metadata: dict = field(default_factory=dict)


class RegisterArtifactUseCase:
    def __init__(self, artifact_repo: IArtifactRepository, release_repo: IReleaseRepository) -> None:
        self.artifact_repo = artifact_repo
        self.release_repo = release_repo

    async def execute(self, command: RegisterArtifactCommand) -> Artifact:
        release = await self.release_repo.get_by_id(command.release_id)
        if not release:
            raise EntityNotFoundError(f"Release not found with ID: {command.release_id}")

        artifact = Artifact(
            release_id=command.release_id,
            connector_instance_id=command.connector_instance_id,
            artifact_type=command.artifact_type,
            external_ref=command.external_ref,
            metadata=command.metadata,
        )
        return await self.artifact_repo.save(artifact)


class ListArtifactsUseCase:
    def __init__(self, artifact_repo: IArtifactRepository, release_repo: IReleaseRepository) -> None:
        self.artifact_repo = artifact_repo
        self.release_repo = release_repo

    async def execute(self, release_id: uuid.UUID) -> List[Artifact]:
        release = await self.release_repo.get_by_id(release_id)
        if not release:
            raise EntityNotFoundError(f"Release not found with ID: {release_id}")
        return await self.artifact_repo.find_by_release(release_id)


class GetArtifactUseCase:
    def __init__(self, artifact_repo: IArtifactRepository) -> None:
        self.artifact_repo = artifact_repo

    async def execute(self, release_id: uuid.UUID, artifact_id: uuid.UUID) -> Artifact:
        artifact = await self.artifact_repo.find_by_id(artifact_id)
        if not artifact or artifact.release_id != release_id:
            raise EntityNotFoundError(f"Artifact not found with ID: {artifact_id}")
        return artifact


class DeleteArtifactUseCase:
    def __init__(self, artifact_repo: IArtifactRepository) -> None:
        self.artifact_repo = artifact_repo

    async def execute(self, release_id: uuid.UUID, artifact_id: uuid.UUID) -> None:
        artifact = await self.artifact_repo.find_by_id(artifact_id)
        if not artifact or artifact.release_id != release_id:
            raise EntityNotFoundError(f"Artifact not found with ID: {artifact_id}")
        await self.artifact_repo.delete(artifact_id)

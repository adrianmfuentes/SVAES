from typing import List, Optional
from uuid import UUID
from application.ports.input.i_artifact_service import IArtifactService
from application.ports.output.i_artifact_repository import IArtifactRepository
from application.ports.output.i_release_repository import IReleaseRepository
from domain.entities.artifact import Artifact
from domain.enums import ArtifactType
from domain.exceptions import ValidationError


_RELEASE_NOT_FOUND = "Release no encontrada"

"""
Este módulo define el servicio de artefactos, que es responsable de gestionar los artefactos dentro del sistema. Incluye la lógica de negocio para 
listar artefactos, agregar nuevos artefactos, y eliminar artefactos.
"""
class ArtifactService(IArtifactService):
    def __init__(
        self,
        artifact_repository: IArtifactRepository,
        release_repository: IReleaseRepository,
    ):
        self._artifact_repo = artifact_repository
        self._release_repo = release_repository


    async def list_artifacts(self, release_id: UUID) -> List[Artifact]:
        release = await self._release_repo.get_by_id(release_id)
        if not release:
            raise ValidationError(_RELEASE_NOT_FOUND)
        return await self._artifact_repo.find_by_release(release_id)


    async def add_artifact(
        self,
        release_id: UUID,
        connector_instance_id: UUID,
        connector_implementation: str,
        artifact_type: ArtifactType,
        external_ref: str,
        metadata: Optional[dict] = None,
    ) -> Artifact:
        release = await self._release_repo.get_by_id(release_id)
        if not release:
            raise ValidationError(_RELEASE_NOT_FOUND)

        artifact = Artifact(
            release_id=release_id,
            connector_instance_id=connector_instance_id,
            connector_implementation=connector_implementation,
            artifact_type=artifact_type.value if hasattr(artifact_type, "value") else artifact_type,
            external_ref=external_ref,
            metadata=metadata or {},
        )
        return await self._artifact_repo.save(artifact)


    async def remove_artifact(self, release_id: UUID, artifact_id: UUID) -> None:
        release = await self._release_repo.get_by_id(release_id)
        if not release:
            raise ValidationError(_RELEASE_NOT_FOUND)

        artifact = await self._artifact_repo.find_by_id(artifact_id)
        if not artifact:
            raise ValidationError("Artifact no encontrado")

        if artifact.release_id != release_id:
            raise ValidationError("Artifact no pertenece a esta release")

        await self._artifact_repo.delete(artifact_id)
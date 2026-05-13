from typing import List, Optional
from uuid import UUID
from domain.entities.artifact import Artifact
from domain.enums import ArtifactType
from application.ports.output.i_artifact_repository import IArtifactRepository
from application.ports.output.i_release_repository import IReleaseRepository
from domain.exceptions import ValidationError

"""
Este módulo define el caso de uso para gestionar artefactos, que incluye la adición, listado y eliminación de artefactos asociados a una release.
La adición de un artefacto requiere el ID de la release, el ID de la instancia del conector, el tipo de artefacto, una referencia externa y opcionalmente
metadatos adicionales. El listado devuelve todos los artefactos asociados a una release específica, y la eliminación permite eliminar un artefacto 
específico de una release.
"""
class ManageArtifactsUseCase:
    def __init__(
        self,
        artifact_repository: IArtifactRepository,
        release_repository: IReleaseRepository,
    ) -> None:
        self._artifact_repo = artifact_repository
        self._release_repo = release_repository

    async def add_artifact(
        self,
        release_id: UUID,
        connector_instance_id: UUID,
        artifact_type: ArtifactType,
        external_ref: str,
        metadata: Optional[dict] = None,
    ) -> Artifact:
        release = await self._release_repo.get_by_id(release_id)
        if not release:
            raise ValidationError("Release no encontrada")

        artifact = Artifact(
            release_id=release_id,
            connector_instance_id=connector_instance_id,
            artifact_type=artifact_type.value if hasattr(artifact_type, "value") else artifact_type,
            external_ref=external_ref,
            metadata=metadata or {},
        )
        return await self._artifact_repo.save(artifact)

    async def list_artifacts(self, release_id: UUID) -> List[Artifact]:
        release = await self._release_repo.get_by_id(release_id)
        if not release:
            raise ValidationError("Release no encontrada")
        return await self._artifact_repo.find_by_release(release_id)

    async def remove_artifact(self, release_id: UUID, artifact_id: UUID) -> None:
        release = await self._release_repo.get_by_id(release_id)
        if not release:
            raise ValidationError("Release no encontrada")

        artifact = await self._artifact_repo.find_by_id(artifact_id)
        if not artifact:
            raise ValidationError("Artifact no encontrado")

        if artifact.release_id != release_id:
            raise ValidationError("Artifact no pertenece a esta release")

        await self._artifact_repo.delete(artifact_id)
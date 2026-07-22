from typing import List, Optional
from uuid import UUID
from application.ports.input.i_artifact_service import IArtifactService
from application.ports.output.i_artifact_repository import IArtifactRepository
from application.ports.output.i_release_repository import IReleaseRepository
from application.ports.output.i_connector_repository import IConnectorRepository
from domain.entities.artifact import Artifact
from domain.enums import ArtifactType, ConnectorType
from domain.exceptions import ValidationError


_RELEASE_NOT_FOUND = "Release no encontrada"

_ARTIFACT_TYPE_TO_CONNECTOR_TYPE = {
    ArtifactType.TAREA: ConnectorType.GESTOR_TAREAS,
    ArtifactType.CODIGO: ConnectorType.REPO_CODIGO,
    ArtifactType.DOCUMENTO: ConnectorType.SISTEMA_DOCUMENTAL,
    ArtifactType.PLAN: ConnectorType.HERRAMIENTA_PLANIFICACION,
    ArtifactType.CAMBIO: ConnectorType.GESTION_CAMBIOS,
}


def _connector_implementation_matches_type(implementation: str, expected_type: str) -> bool:
    from infrastructure.secondary.connectors import create_registered_connector_registry
    registry = create_registered_connector_registry()
    try:
        impl = registry.get_by_implementation(implementation)
        return impl.get_connector_type() == expected_type
    except KeyError:
        return False


class ArtifactService(IArtifactService):
    def __init__(
        self,
        artifact_repository: IArtifactRepository,
        release_repository: IReleaseRepository,
        connector_repository: IConnectorRepository,
    ):
        self._artifact_repo = artifact_repository
        self._release_repo = release_repository
        self._connector_repo = connector_repository


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
        description: str = "",
        metadata: Optional[dict] = None,
    ) -> Artifact:
        release = await self._release_repo.get_by_id(release_id)
        if not release:
            raise ValidationError(_RELEASE_NOT_FOUND)

        connector = await self._connector_repo.get_by_id(connector_instance_id)
        if not connector:
            raise ValidationError(f"Conector {connector_instance_id} no encontrado")

        if release.organization_id and connector.organization_id != release.organization_id:
            raise ValidationError(f"Conector {connector_instance_id} no pertenece a la organización de esta release")

        expected_connector_type = _ARTIFACT_TYPE_TO_CONNECTOR_TYPE.get(artifact_type)
        if expected_connector_type and connector.connector_type != expected_connector_type.value:
            if not _connector_implementation_matches_type(
                connector.connector_implementation, expected_connector_type.value
            ):
                raise ValidationError(
                    f"Tipo de artefacto '{artifact_type.value}' no es compatible con conector de tipo '{connector.connector_type}'. "
                    f"Expected: {expected_connector_type.value}"
                )

        artifact = Artifact(
            release_id=release_id,
            connector_instance_id=connector_instance_id,
            connector_implementation=connector_implementation,
            artifact_type=artifact_type.value if hasattr(artifact_type, "value") else artifact_type,
            external_ref=external_ref,
            description=description,
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
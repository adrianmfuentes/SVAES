import re
from typing import Optional
from uuid import UUID, uuid4
from application.ports.input.i_release_service import IReleaseService
from application.ports.output.i_release_repository import IReleaseRepository
from application.ports.output.i_project_repository import IProjectRepository
from domain.entities.release import Release
from domain.entities.artifact import Artifact
from domain.enums import ReleaseStatus
from domain.exceptions import ValidationError
from core.audit import AuditEntry, AuditEvent, get_audit_logger
from core.logger import get_logger

_log = get_logger(__name__) 

"""
Clase de servicio (Use Case) que implementa la lógica de negocio para gestionar releases y sus artifacts.
Se encarga de validar datos, interactuar con los repositorios para persistencia y aplicar las reglas de negocio relacionadas con releases.

Recibe datos desde el controlador (API) y utiliza los repositorios para acceder a la base de datos
Implementa el puerto de entrada IReleaseService, que define las operaciones disponibles para gestionar releases.
"""
class CreateReleaseUseCase(IReleaseService):
    def __init__(self, release_repository: IReleaseRepository, project_repository: IProjectRepository):
        self.release_repository = release_repository
        self.project_repository = project_repository
        
    async def create_release(
        self,
        name: str,
        version: str,
        project_id: UUID,      
        user_id: UUID,         
        description: str = "",
    ) -> Release:
        if not self._is_valid_semver(version):
            raise ValidationError("La versión debe cumplir SemVer 2.0.0") # Semver es un estándar de versionado
        
        project = await self.project_repository.get_by_id(project_id)
        if not project:
            raise ValidationError("El proyecto indicado no existe.")
            
        new_release = Release(
            name=name,
            version=version,
            project_id=project_id,
            profile_id=project.profile_id,
            created_by=user_id,
            status=ReleaseStatus.BORRADOR
        )

        created = await self.release_repository.create(new_release)

        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.RELEASE_CREATED,
            user_id=user_id,
            organization_id=project.organization_id,
            resource_type="release",
            resource_id=created.id,
            details={"name": name, "version": version},
        ))
        _log.info("Release created: id=%s project=%s name=%s v=%s", created.id, project_id, name, version)

        return created
           

    async def get_release(self, release_id: UUID) -> Release | None:
        return await self.release_repository.get_by_id(release_id)
    

    async def list_releases(self, project_id: UUID, skip: int = 0, limit: int = 50) -> list[Release]:
        return await self.release_repository.list_by_project(project_id, skip, limit)
    

    async def update_release(
        self,
        release_id: UUID,
        name: str,
        version: str,
        description: str = "",
    ) -> Release:
        if not self._is_valid_semver(version):
            raise ValidationError("La versión debe cumplir SemVer 2.0.0")
        release = await self.release_repository.get_by_id(release_id)
        if not release:
            raise ValidationError("No se encontró el release para actualizar.")
        release.name = name
        release.version = version
        release.description = description
        await self.release_repository.update(release)
        return release

    async def update_status(self, release_id: UUID, status: ReleaseStatus) -> Release:
        release = await self.release_repository.update_status(release_id, status)
        if not release:
            raise ValidationError("No se encontró el release para actualizar su estado.")
        return release
    
    
    async def add_artifact(
        self,
        release_id: UUID,
        connector_instance_id: UUID,
        artifact_type: str,
        external_ref: str,
        metadata: Optional[dict] = None,
    ) -> Artifact:
        release = await self.release_repository.get_by_id(release_id)
        if not release:
            raise ValidationError("No se encontró el release para agregar el artifact.")
        
        artifact = Artifact(
            id=uuid4(),
            release_id=release_id,
            connector_instance_id=connector_instance_id,
            artifact_type=artifact_type,
            external_ref=external_ref,
            metadata=metadata or {}
        )
        
        release.artifacts.append(artifact)
        await self.release_repository.update(release)
        return artifact
    

    async def remove_artifact(self, artifact_id: UUID) -> None:
        artifact = await self.release_repository.get_artifact_by_id(artifact_id)
        if not artifact:
            raise ValidationError("No se encontró el artifact para eliminar.")
        
        release_id = artifact["release_id"] if isinstance(artifact, dict) else artifact.release_id
        release = await self.release_repository.get_by_id(release_id)
        if not release:
            raise ValidationError("No se encontró el release asociado al artifact.")
        
        release.artifacts = [a for a in release.artifacts if a.id != artifact_id] # Creamos una nueva lista sin el artifact a eliminar
        await self.release_repository.update(release)
        await self.release_repository.delete_artifact(artifact_id)
    

    async def list_artifacts(self, release_id: UUID, skip: int = 0, limit: int = 100) -> list[Artifact]:
        release = await self.release_repository.get_by_id(release_id)
        if not release:
            raise ValidationError("No se encontró el release para listar sus artifacts.")
        return release.artifacts[skip:skip+limit]
    

    async def delete_release(self, release_id: UUID) -> None:
        release = await self.release_repository.get_by_id(release_id)
        if not release:
            raise ValidationError("No se encontró el release para eliminar.")
        await self.release_repository.delete(release_id)

    async def restore_release(self, release_id: UUID) -> None:
        release = await self.release_repository.get_by_id(release_id)
        if not release:
            raise ValidationError("No se encontró el release para restaurar.")
        if release.status != ReleaseStatus.ARCHIVADA:
            raise ValidationError("Solo se pueden restaurar releases archivadas.")
        release.status = ReleaseStatus.BORRADOR
        await self.release_repository.update(release)
        _log.info("Release restored: id=%s", release_id)

    ## -- Helpers ---

    _SEMVER = r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)'
    _PRE_RELEASE = r'(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?'
    _BUILD = r'(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?'
    _SEMVER_RE = rf'^{_SEMVER}{_PRE_RELEASE}{_BUILD}$'

    def _is_valid_semver(self, version: str) -> bool:
        return re.match(self._SEMVER_RE, version) is not None
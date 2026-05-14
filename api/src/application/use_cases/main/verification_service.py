from typing import List, Optional
from uuid import UUID
from application.ports.input.i_verification_service import IVerificationService
from application.ports.output.i_verification_result_repository import IVerificationResultRepository
from application.ports.output.i_release_repository import IReleaseRepository
from application.ports.output.i_task_queue import ITaskQueue
from application.ports.output.i_connector_registry import IConnectorRegistry
from application.ports.output.i_connector import IConnector
from domain.entities.verification_result import VerificationResult
from domain.enums import ReleaseStatus
from domain.exceptions import ValidationError
from core.audit import AuditEntry, AuditEvent, get_audit_logger
from core.logger import get_logger


_RELEASE_NOT_FOUND = "Release no encontrada"

_log = get_logger(__name__)


class VerificationService(IVerificationService):
    def __init__(
        self,
        release_repository: IReleaseRepository,
        verification_repository: IVerificationResultRepository,
        task_queue: ITaskQueue,
        connector_registry: IConnectorRegistry,
    ):
        self._release_repo = release_repository
        self._verification_repo = verification_repository
        self._task_queue = task_queue
        self._connector_registry = connector_registry


    async def launch_verification(self, release_id: UUID) -> str:
        release = await self._release_repo.get_by_id(release_id)
        if not release:
            raise ValidationError(_RELEASE_NOT_FOUND)

        valid_statuses = (
            ReleaseStatus.PENDIENTE,
            ReleaseStatus.VALIDA,
            ReleaseStatus.NO_VALIDA,
            ReleaseStatus.CON_ADVERTENCIAS,
        )

        if release.status not in valid_statuses:
            raise ValidationError(
                f"No se puede iniciar verificación desde estado {release.status.value}. "
                "Debe estar en PENDIENTE o tener un resultado previo."
            )

        if not release.artifacts or len(release.artifacts) == 0:
            raise ValidationError("No se puede verificar una release sin artefactos asociados.")

        await self._release_repo.update_status(release_id, ReleaseStatus.EN_VERIFICACION)
        task_id = await self._task_queue.enqueue_verification_task(release_id)

        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.RELEASE_VERIFIED,
            user_id=UUID(),
            organization_id=None,
            resource_type="release",
            resource_id=release_id,
            details={"task_id": task_id},
        ))
        _log.info("Verification launched: release=%s task=%s", release_id, task_id)

        return task_id


    async def fetch_artifacts_via_connectors(self, release_id: UUID) -> List[dict]:
        release = await self._release_repo.get_by_id(release_id)
        if not release or not release.artifacts:
            return []

        results = []
        for artifact in release.artifacts:
            try:
                connector_impl = self._connector_registry.get_by_implementation(artifact.connector_implementation)
                if connector_impl:
                    config = {}
                    data = await connector_impl.fetch_artifact(artifact.external_ref, config)
                    results.append({
                        "artifact_id": str(artifact.id),
                        "type": artifact.artifact_type,
                        "external_ref": artifact.external_ref,
                        "connector_implementation": artifact.connector_implementation,
                        "data": data,
                    })
            except Exception:
                pass
        return results


    async def get_verification_result(
        self, release_id: UUID, result_id: UUID
    ) -> Optional[VerificationResult]:
        release = await self._release_repo.get_by_id(release_id)
        if not release:
            raise ValidationError(_RELEASE_NOT_FOUND)

        result = await self._verification_repo.find_by_id(result_id)
        if result and result.release_id != release_id:
            raise ValidationError("Resultado no pertenece a esta release")
        return result


    async def get_verification_history(self, release_id: UUID) -> List[VerificationResult]:
        release = await self._release_repo.get_by_id(release_id)
        if not release:
            raise ValidationError(_RELEASE_NOT_FOUND)
        return await self._verification_repo.find_by_release(release_id)


    async def get_latest_verification(self, release_id: UUID) -> Optional[VerificationResult]:
        results = await self._verification_repo.find_by_release(release_id)
        return results[0] if results else None
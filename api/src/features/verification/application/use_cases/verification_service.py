import logging
import ast
from typing import List, Optional
from uuid import UUID
from features.verification.application.ports.i_verification_service import IVerificationService
from features.verification.application.ports.i_verification_result_repository import IVerificationResultRepository
from features.projects_releases.application.ports.i_release_repository import IReleaseRepository
from shared.application.i_credential_encryptor import ICredentialEncryptor
from features.connectors.application.ports.i_connector_repository import IConnectorRepository
from shared.application.i_task_queue import ITaskQueue
from features.connectors.application.ports.i_connector_registry import IConnectorRegistry
from features.connectors.application.ports.i_connector import IConnector
from features.verification.domain.verification_result import VerificationResult
from shared.domain.enums import ReleaseStatus
from shared.domain.exceptions import ValidationError
from shared.application.i_audit_logger import IAuditLogger
from shared.domain.audit import AuditEntry, AuditEvent


_RELEASE_NOT_FOUND = "Release no encontrada"

_log = logging.getLogger(__name__)


class VerificationService(IVerificationService):
    def __init__(
        self,
        release_repository: IReleaseRepository,
        verification_repository: IVerificationResultRepository,
        task_queue: ITaskQueue,
        connector_registry: IConnectorRegistry,
        connector_repository: Optional[IConnectorRepository] = None,
        *,
        credential_encryptor: ICredentialEncryptor,
        audit_logger: IAuditLogger,
    ):
        self._release_repo = release_repository
        self._verification_repo = verification_repository
        self._task_queue = task_queue
        self._connector_registry = connector_registry
        self._connector_repo = connector_repository
        self._credential_encryptor = credential_encryptor
        self._audit_logger = audit_logger


    async def launch_verification(self, release_id: UUID, requested_by: UUID, triggered_by: str = "manual") -> str:
        release = await self._release_repo.get_by_id(release_id)
        if not release:
            raise ValidationError(_RELEASE_NOT_FOUND)

        valid_statuses = (
            ReleaseStatus.BORRADOR,
            ReleaseStatus.PENDIENTE,
            ReleaseStatus.VALIDA,
            ReleaseStatus.NO_VALIDA,
            ReleaseStatus.CON_ADVERTENCIAS,
        )

        if release.status not in valid_statuses:
            raise ValidationError(
                f"No se puede iniciar verificación desde estado {release.status.value}. "
                "La release debe estar en BORRADOR, PENDIENTE o tener un resultado previo."
            )

        if not release.artifacts or len(release.artifacts) == 0:
            raise ValidationError("No se puede verificar una release sin artefactos asociados.")

        previous_status = release.status
        await self._release_repo.update_pending_task(release_id, None, previous_status)
        await self._release_repo.update_status(release_id, ReleaseStatus.EN_VERIFICACION)
        task_id = await self._task_queue.enqueue_verification_task(release_id, triggered_by=triggered_by)
        await self._release_repo.update_pending_task(release_id, task_id, None)

        self._audit_logger.log(AuditEntry(
            event=AuditEvent.RELEASE_VERIFIED,
            user_id=requested_by,
            organization_id=None,
            resource_type="release",
            resource_id=release_id,
            details={"task_id": task_id, "triggered_by": triggered_by},
        ))
        _log.info("Verification launched: release=%s task=%s triggered_by=%s", release_id, task_id, triggered_by)

        return task_id


    async def cancel_verification(self, release_id: UUID) -> bool:
        release = await self._release_repo.get_by_id(release_id)
        if not release:
            raise ValidationError(_RELEASE_NOT_FOUND)

        if release.status != ReleaseStatus.EN_VERIFICACION:
            raise ValidationError(
                f"No se puede cancelar la verificación. La release está en estado {release.status.value}."
            )

        task_id = release.pending_task_id
        if task_id:
            await self._task_queue.cancel_task(task_id)

        previous_status = release.previous_status or ReleaseStatus.PENDIENTE
        await self._release_repo.update_status(release_id, previous_status)
        await self._release_repo.update_pending_task(release_id, None, None)

        _log.info("Verification cancelled: release=%s", release_id)
        return True


    async def fetch_artifacts_via_connectors(self, release_id: UUID) -> List[dict]:
        release = await self._release_repo.get_by_id(release_id)
        if not release or not release.artifacts:
            return []

        results = []
        for artifact in release.artifacts:
            try:
                connector_impl = self._connector_registry.get_by_implementation(artifact.connector_implementation)
                if not connector_impl:
                    continue

                config: dict = {}
                if self._connector_repo:
                    connector_instance = await self._connector_repo.get_by_id(artifact.connector_instance_id)
                    if connector_instance:
                        config = ast.literal_eval(
                            self._credential_encryptor.decrypt(
                                connector_instance.encrypted_credentials, connector_instance.id,
                            )
                        )

                data = await connector_impl.fetch_artifact(artifact.external_ref, config)
                results.append({
                    "artifact_id": str(artifact.id),
                    "type": artifact.artifact_type,
                    "external_ref": artifact.external_ref,
                    "connector_implementation": artifact.connector_implementation,
                    "data": data,
                })
            except Exception:
                _log.warning(
                    "fetch_artifacts_via_connectors: artifact %s failed (release=%s, impl=%s)",
                    artifact.id, release_id, artifact.connector_implementation,
                )
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
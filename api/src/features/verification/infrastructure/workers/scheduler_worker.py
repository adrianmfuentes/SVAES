"""Verificaciones programadas: dispara `EN_VERIFICACION` sin intervención manual
para releases cuyo perfil tiene una expresión cron en `VerificationProfile.schedule`.

Se apoya en el mismo `VerificationService.launch_verification` que usa el
endpoint on-demand (`POST /releases/{id}/verify`), pasando
`triggered_by="scheduled"` para que `verification_worker._notify_user`
pueda distinguir una re-verificación automática de una manual y así detectar
"drift" (una release que era VALIDA/CON_ADVERTENCIAS cae a NO_VALIDA sin que
nadie haya cambiado nada a mano).

Corre como tarea periódica de Celery Beat (ver `celery_app.py`), no como
respuesta a un evento: por eso re-computa "¿toca ya?" en cada tick en vez de
programar un `apply_async(eta=...)` por perfil, que se perdería si el proceso
de beat se reinicia entre medias.
"""

from shared.infrastructure.fernet_encryptor import create_credential_encryptor
from features.verification.application.use_cases.check_scheduled_verifications import CheckScheduledVerifications
from features.verification.infrastructure.gateways.cron_schedule import _is_due
from shared.infrastructure.audit_db import get_audit_logger
from shared.infrastructure.system_clock import SystemClock
from shared.infrastructure.queue.celery_app import celery_app
from shared.infrastructure.queue.worker_loop import run_worker_coroutine
from shared.infrastructure.queue.celery_task_queue import CeleryTaskQueue
from features.verification.infrastructure.persistence.profile_repository import SqlProfileRepository
from bootstrap.repositories import get_release_repository
from features.verification.infrastructure.persistence.verification_result_repository import SqlVerificationResultRepository
from bootstrap.repositories import get_connector_repository
from bootstrap.repositories import get_connector_registry
from features.verification.application.use_cases.verification_service import VerificationService

def _build_verification_service() -> VerificationService:
    return VerificationService(
        release_repository=get_release_repository(),
        verification_repository=SqlVerificationResultRepository(),
        task_queue=CeleryTaskQueue(),
        connector_registry=get_connector_registry(),
        connector_repository=get_connector_repository(),
        credential_encryptor=create_credential_encryptor(),
        audit_logger=get_audit_logger(),
    )


async def _trigger_due_profiles_async() -> dict:
    return await CheckScheduledVerifications(
        profiles=SqlProfileRepository(),
        releases=get_release_repository(),
        verifications=_build_verification_service(),
        clock=SystemClock(),
        is_due=_is_due,
    ).execute()


@celery_app.task(name="infrastructure.workers.scheduler_worker.check_scheduled_verifications")
def check_scheduled_verifications() -> dict:
    return run_worker_coroutine(_trigger_due_profiles_async())

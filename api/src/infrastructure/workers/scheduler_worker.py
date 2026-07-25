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
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from croniter import croniter

from infrastructure.secondary.queue.celery_app import celery_app
from infrastructure.secondary.queue.celery_task_queue import CeleryTaskQueue
from infrastructure.secondary.database.repositories.profile_repository import SqlProfileRepository
from infrastructure.secondary.database.repositories.release_repository import SqlReleaseRepository
from infrastructure.secondary.database.repositories.verification_result_repository import SqlVerificationResultRepository
from infrastructure.secondary.database.repositories.connector_repository import SqlConnectorRepository
from infrastructure.secondary.connectors import create_registered_connector_registry
from application.use_cases.main.verification_service import VerificationService
from domain.enums import ReleaseStatus
from domain.exceptions import ValidationError

_slog = logging.getLogger(__name__)

_RE_VERIFIABLE_STATUSES = [ReleaseStatus.VALIDA, ReleaseStatus.CON_ADVERTENCIAS, ReleaseStatus.NO_VALIDA]
_SYSTEM_ACTOR = UUID(int=0)


def _is_due(profile: Any, now: datetime) -> bool:
    if not profile.schedule:
        return False
    reference = profile.schedule_last_run_at or profile.created_at
    try:
        cron = croniter(profile.schedule, reference)
    except (ValueError, KeyError):
        _slog.warning("Profile %s has an invalid schedule '%s', skipping", profile.id, profile.schedule)
        return False
    next_fire = cron.get_next(datetime)
    return next_fire <= now


def _build_verification_service() -> VerificationService:
    return VerificationService(
        release_repository=SqlReleaseRepository(),
        verification_repository=SqlVerificationResultRepository(),
        task_queue=CeleryTaskQueue(),
        connector_registry=create_registered_connector_registry(),
        connector_repository=SqlConnectorRepository(),
    )


async def _trigger_due_profiles_async() -> dict:
    profile_repo = SqlProfileRepository()
    release_repo = SqlReleaseRepository()
    verification_service = _build_verification_service()

    now = datetime.now(timezone.utc)
    profiles = await profile_repo.list_scheduled()

    triggered = 0
    skipped = 0
    errors = 0

    for profile in profiles:
        if not _is_due(profile, now):
            continue

        await profile_repo.update_schedule_last_run(profile.id, now)

        releases = await release_repo.list_by_profile(profile.id, statuses=_RE_VERIFIABLE_STATUSES)
        for release in releases:
            try:
                await verification_service.launch_verification(
                    release.id, requested_by=_SYSTEM_ACTOR, triggered_by="scheduled"
                )
                triggered += 1
            except ValidationError:
                # p.ej. la release ya no tiene artefactos o cambió de estado entre
                # la consulta y el lanzamiento: no es un fallo del scheduler.
                skipped += 1
            except Exception:
                errors += 1
                _slog.exception(
                    "Scheduled verification failed to launch: release=%s profile=%s", release.id, profile.id
                )

    result = {"profiles_checked": len(profiles), "triggered": triggered, "skipped": skipped, "errors": errors}
    _slog.info("Scheduled verification sweep: %s", result)
    return result


@celery_app.task(name="infrastructure.workers.scheduler_worker.check_scheduled_verifications")
def check_scheduled_verifications() -> dict:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_trigger_due_profiles_async())
    finally:
        loop.close()

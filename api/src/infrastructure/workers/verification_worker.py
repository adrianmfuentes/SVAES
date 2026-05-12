import time
import uuid
import logging

from celery.exceptions import MaxRetriesExceededError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from infrastructure.config import settings
from infrastructure.queue.celery_app import celery_app

_log = logging.getLogger(__name__)


def _make_sync_url(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql+psycopg2://")


_engine = create_engine(
    _make_sync_url(settings.database_url),
    pool_size=2,
    max_overflow=2,
    pool_pre_ping=True,
)
_SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False)


@celery_app.task(
    name="infrastructure.workers.verification_worker.run_verification",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="verification",
)
def run_verification(self, release_id_str: str) -> dict:
    release_id = uuid.UUID(release_id_str)
    _log.info("Starting verification for release %s", release_id)
    started_at = time.monotonic()

    try:
        verdict = _execute(release_id, started_at)
        duration_ms = int((time.monotonic() - started_at) * 1000)
        _log.info("Verification finished for release %s — verdict=%s (%dms)", release_id, verdict, duration_ms)
        return {"release_id": release_id_str, "verdict": verdict, "duration_ms": duration_ms}

    except MaxRetriesExceededError:
        _set_release_status(release_id, "PENDIENTE")
        raise

    except Exception as exc:
        _log.exception("Verification failed for release %s: %s", release_id, exc)
        raise self.retry(exc=exc)


def _execute(release_id: uuid.UUID, started_at: float) -> str:
    from infrastructure.database.models.release import ReleaseModel
    from infrastructure.database.models.verification_result import VerificationResultModel

    with _SessionFactory() as session:
        with session.begin():
            release = session.get(ReleaseModel, release_id)
            if not release:
                raise ValueError(f"Release {release_id} not found")

            # TODO: replace with IVerificationEngine.execute_verification(release)
            verdict = "VALIDO"
            rule_results: dict = {}
            profile_snapshot: dict = {}

            duration_ms = int((time.monotonic() - started_at) * 1000)
            session.add(VerificationResultModel(
                release_id=release_id,
                verdict=verdict,
                rule_results=rule_results,
                profile_snapshot=profile_snapshot,
                duration_ms=duration_ms,
            ))
            release.status = "VALIDA"

    return verdict


def _set_release_status(release_id: uuid.UUID, status: str) -> None:
    from infrastructure.database.models.release import ReleaseModel

    try:
        with _SessionFactory() as session:
            with session.begin():
                release = session.get(ReleaseModel, release_id)
                if release:
                    release.status = status
    except Exception:
        _log.exception("Failed to reset status for release %s to %s", release_id, status)
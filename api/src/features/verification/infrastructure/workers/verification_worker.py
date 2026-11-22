import uuid
from typing import Any, Dict

from features.verification.container import get_run_verification
from shared.infrastructure.queue.celery_app import celery_app
from shared.infrastructure.queue.worker_loop import run_worker_coroutine



def _report_progress(celery_task: Any, current: int, total: int, stage: str) -> None:
    pct = min(99, int(current / total * 100)) if total > 0 else 0
    celery_task.update_state(state='PROGRESS', meta={
        'current': current,
        'total': total,
        'stage': stage,
        'pct': pct,
    })


@celery_app.task(name="infrastructure.workers.verification_worker.run_verification", bind=True)
def run_verification(self, release_id: str, triggered_by: str = "manual") -> Dict[str, Any]:
    release_uuid = uuid.UUID(release_id)

    _report_progress(self, current=0, total=1, stage='loading')

    return run_worker_coroutine(
        _run_verification_async(release_uuid, self.request.id, self, triggered_by)
    )


async def _run_verification_async(
    release_id: uuid.UUID, task_id: str, celery_task: Any, triggered_by: str = "manual",
) -> dict[str, Any]:
    def report_progress(current: int, total: int, stage: str) -> None:
        _report_progress(celery_task, current, total, stage)

    return await get_run_verification().execute(release_id, task_id, triggered_by, report_progress)

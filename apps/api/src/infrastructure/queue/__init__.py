from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from celery import Celery

celery_app: Celery | None = None
CeleryTaskQueue = None

try:
    from celery import Celery

    celery_app = Celery("svaes")
except Exception:
    pass

try:
    from celery_task_queue import CeleryTaskQueue
except Exception:
    pass

__all__ = ["celery_app", "CeleryTaskQueue"]

from celery import Celery
from infrastructure.config import settings

celery_app = Celery(
    "svaes",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["infrastructure.workers.verification_worker"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,   # estado STARTED antes de SUCCESS/FAILURE
    task_acks_late=True,       # ACK solo después de completar (evita pérdida si el worker muere)
    worker_prefetch_multiplier=1,  # el worker solo coge 1 tarea a la vez
)
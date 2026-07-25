from celery import Celery
from celery.schedules import crontab
from core.config import settings

celery_app = Celery(
    "svaes",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "infrastructure.workers.verification_worker",
        "infrastructure.workers.scheduler_worker",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
)

# El sweep corre cada 5 minutos y decide por sí mismo (via croniter) si algún
# perfil "toca" ya, en vez de programar un `apply_async(eta=...)` por perfil:
# así una `schedule` cron de "cada hora" no requiere reprogramar nada si el
# proceso de beat se reinicia entre medias.
celery_app.conf.beat_schedule = {
    "check-scheduled-verifications": {
        "task": "infrastructure.workers.scheduler_worker.check_scheduled_verifications",
        "schedule": crontab(minute="*/5"),
    },
}
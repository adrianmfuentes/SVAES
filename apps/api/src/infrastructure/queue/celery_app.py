from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from celery import Celery


def _get_celery_app() -> "Celery":
    from celery import Celery

    return Celery(
        "svaes",
        broker_url=None,
        result_backend=None,
    )


try:
    from celery import Celery

    celery_app = Celery("svaes")
except Exception:
    celery_app = _get_celery_app()

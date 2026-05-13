from celery import Celery
from core.config import settings

"""
Este archivo configura la aplicación Celery para manejar tareas asíncronas en el proyecto SVAES. 
Celery es una biblioteca de Python que permite ejecutar tareas en segundo plano, como la verificación de releases.
"""
celery_app = Celery(
    "svaes",
    broker=settings.celery_broker_url, # Configura el broker de mensajes (Redis)
    backend=settings.celery_result_backend, # Configura el backend para almacenar resultados de tareas
    include=["infrastructure.workers.verification_worker"], # Asegura que el worker de verificación se registre al iniciar Celery
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,                                        # Estado STARTED antes de SUCCESS/FAILURE
    task_acks_late=True,                                            # ACK solo después de completar (evita pérdida si el worker muere)
    worker_prefetch_multiplier=1,                                   # El worker solo coge 1 tarea a la vez
)
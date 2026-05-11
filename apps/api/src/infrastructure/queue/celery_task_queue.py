# Intentionally empty — implement manually.
#
# Placeholder for ITaskQueue implementation using Celery.
#
# When implementing, ensure:
# - Implements ITaskQueue from domain/ports/i_task_queue.py
# - Uses redis via CELERY_BROKER_URL / CELERY_RESULT_BACKEND
# - Task serialization: JSON
# - Queue name: "verification"
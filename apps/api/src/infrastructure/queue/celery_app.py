from celery import Celery

# NOTE: You must implement the celery_app instance manually.
# It should be configured with:
#   - broker_url from settings.celery_broker_url
#   - result_backend from settings.celery_result_backend
#   - task_serializer = "json"
#   - accept_content = ["json"]
#   - result_serializer = "json"
#   - timezone = "UTC"
#   - enable_utc = True
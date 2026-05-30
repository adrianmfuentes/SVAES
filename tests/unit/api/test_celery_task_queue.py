import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from domain.enums import TaskStatus

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_celery_app():
    app = MagicMock()
    app.send_task = MagicMock()
    app.AsyncResult = MagicMock()
    return app


@pytest.fixture
def task_queue(mock_celery_app):
    with patch(
        "infrastructure.secondary.queue.celery_task_queue.celery_app",
        mock_celery_app,
    ):
        from infrastructure.secondary.queue.celery_task_queue import CeleryTaskQueue
        yield CeleryTaskQueue()


class TestEnqueueVerificationTask:
    async def test_enqueue_verification_task_returns_task_id(self, task_queue, mock_celery_app):
        task_id = "abc-123-def"
        mock_result = MagicMock()
        mock_result.id = task_id
        mock_celery_app.send_task.return_value = mock_result

        release_id = uuid4()
        result = await task_queue.enqueue_verification_task(release_id)

        assert result == task_id
        mock_celery_app.send_task.assert_called_once()
        args = mock_celery_app.send_task.call_args
        assert args[1]["args"] == [str(release_id)]
        assert args[1]["queue"] == "verification"


class TestGetTaskStatus:
    async def test_get_task_status_success(self, task_queue, mock_celery_app):
        mock_result = MagicMock()
        mock_result.status = "SUCCESS"
        mock_celery_app.AsyncResult.return_value = mock_result

        status = await task_queue.get_task_status("task-123")

        assert status == TaskStatus.SUCCESS
        mock_celery_app.AsyncResult.assert_called_once_with("task-123")

    async def test_get_task_status_pending(self, task_queue, mock_celery_app):
        mock_result = MagicMock()
        mock_result.status = "PENDING"
        mock_celery_app.AsyncResult.return_value = mock_result

        status = await task_queue.get_task_status("task-456")

        assert status == TaskStatus.PENDING

    async def test_get_task_status_failure(self, task_queue, mock_celery_app):
        mock_result = MagicMock()
        mock_result.status = "FAILURE"
        mock_celery_app.AsyncResult.return_value = mock_result

        status = await task_queue.get_task_status("task-789")

        assert status == TaskStatus.FAILURE

    async def test_get_task_status_started(self, task_queue, mock_celery_app):
        mock_result = MagicMock()
        mock_result.status = "STARTED"
        mock_celery_app.AsyncResult.return_value = mock_result

        status = await task_queue.get_task_status("task-started")

        assert status == TaskStatus.STARTED

    async def test_get_task_status_unknown_falls_back_to_pending(self, task_queue, mock_celery_app):
        mock_result = MagicMock()
        mock_result.status = "WEIRD_STATE"
        mock_celery_app.AsyncResult.return_value = mock_result

        status = await task_queue.get_task_status("task-weird")

        assert status == TaskStatus.PENDING


class TestCancelTask:
    async def test_cancel_task_returns_true(self, task_queue, mock_celery_app):
        mock_result = MagicMock()
        mock_result.revoke = MagicMock()
        mock_celery_app.AsyncResult.return_value = mock_result

        result = await task_queue.cancel_task("task-to-cancel")

        assert result is True
        mock_result.revoke.assert_called_once_with(terminate=True)
        mock_celery_app.AsyncResult.assert_called_once_with("task-to-cancel")

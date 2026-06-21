import uuid
from unittest.mock import MagicMock, patch

import pytest

from infrastructure.secondary.queue.celery_task_queue import CeleryTaskQueue
from application.ports.output.i_task_queue import TaskStatus


class TestCeleryTaskQueue:
    @pytest.mark.asyncio
    async def test_enqueue_verification_task(self):
        release_id = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.id = "task-abc-123"
        mock_celery_app = MagicMock()
        mock_celery_app.send_task.return_value = mock_result

        queue = CeleryTaskQueue()

        with patch(
            "infrastructure.secondary.queue.celery_task_queue.celery_app",
            mock_celery_app,
        ):
            task_id = await queue.enqueue_verification_task(release_id)

        assert task_id == "task-abc-123"
        mock_celery_app.send_task.assert_called_once_with(
            "infrastructure.workers.verification_worker.run_verification",
            args=[str(release_id)],
        )

    @pytest.mark.asyncio
    async def test_get_task_status_pending(self):
        mock_result = MagicMock()
        mock_result.status = "PENDING"
        mock_celery_app = MagicMock()
        mock_celery_app.AsyncResult.return_value = mock_result

        queue = CeleryTaskQueue()

        with patch(
            "infrastructure.secondary.queue.celery_task_queue.celery_app",
            mock_celery_app,
        ):
            status = await queue.get_task_status("task-1")

        assert status == TaskStatus.PENDING
        mock_celery_app.AsyncResult.assert_called_once_with("task-1")

    @pytest.mark.asyncio
    async def test_get_task_status_success(self):
        mock_result = MagicMock()
        mock_result.status = "SUCCESS"
        mock_celery_app = MagicMock()
        mock_celery_app.AsyncResult.return_value = mock_result

        queue = CeleryTaskQueue()

        with patch(
            "infrastructure.secondary.queue.celery_task_queue.celery_app",
            mock_celery_app,
        ):
            status = await queue.get_task_status("task-2")

        assert status == TaskStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_get_task_status_started(self):
        mock_result = MagicMock()
        mock_result.status = "STARTED"
        mock_celery_app = MagicMock()
        mock_celery_app.AsyncResult.return_value = mock_result

        queue = CeleryTaskQueue()

        with patch(
            "infrastructure.secondary.queue.celery_task_queue.celery_app",
            mock_celery_app,
        ):
            status = await queue.get_task_status("task-3")

        assert status == TaskStatus.STARTED

    @pytest.mark.asyncio
    async def test_get_task_status_failure(self):
        mock_result = MagicMock()
        mock_result.status = "FAILURE"
        mock_celery_app = MagicMock()
        mock_celery_app.AsyncResult.return_value = mock_result

        queue = CeleryTaskQueue()

        with patch(
            "infrastructure.secondary.queue.celery_task_queue.celery_app",
            mock_celery_app,
        ):
            status = await queue.get_task_status("task-4")

        assert status == TaskStatus.FAILURE

    @pytest.mark.asyncio
    async def test_get_task_status_unknown(self):
        mock_result = MagicMock()
        mock_result.status = "NONEXISTENT_STATUS"
        mock_celery_app = MagicMock()
        mock_celery_app.AsyncResult.return_value = mock_result

        queue = CeleryTaskQueue()

        with patch(
            "infrastructure.secondary.queue.celery_task_queue.celery_app",
            mock_celery_app,
        ):
            status = await queue.get_task_status("task-unknown")

        assert status == TaskStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_task_status_exception(self):
        mock_result = MagicMock()
        type(mock_result).status = property(fget=lambda self: (_ for _ in ()).throw(Exception("boom")))
        mock_celery_app = MagicMock()
        mock_celery_app.AsyncResult.return_value = mock_result

        queue = CeleryTaskQueue()

        with patch(
            "infrastructure.secondary.queue.celery_task_queue.celery_app",
            mock_celery_app,
        ):
            status = await queue.get_task_status("task-error")

        assert status == TaskStatus.PENDING

    @pytest.mark.asyncio
    async def test_cancel_task(self):
        mock_result = MagicMock()
        mock_celery_app = MagicMock()
        mock_celery_app.AsyncResult.return_value = mock_result

        queue = CeleryTaskQueue()

        with patch(
            "infrastructure.secondary.queue.celery_task_queue.celery_app",
            mock_celery_app,
        ):
            result = await queue.cancel_task("task-cancel")

        assert result is True
        mock_celery_app.AsyncResult.assert_called_once_with("task-cancel")
        mock_result.revoke.assert_called_once_with(terminate=True)

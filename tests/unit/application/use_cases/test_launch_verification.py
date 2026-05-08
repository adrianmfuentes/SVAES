"""
Test suite for ``LaunchVerificationUseCase``.

``LaunchVerificationUseCase`` is the critical state machine transition for a
release: it moves a release from ``PENDIENTE`` to ``EN_VERIFICACION`` and enqueues
the asynchronous verification task in the job queue.

Relevant state diagram:
    BORRADOR → PENDIENTE → **EN_VERIFICACION** → COMPLETADA
                                ↑
                         (this use case)

This use case enforces two domain preconditions:
    1. The release must exist.
    2. The release must be in state ``PENDIENTE`` (not any other state).

The operation order is also a domain invariant: state is persisted **before**
enqueueing the task, avoiding race conditions where a worker processes a release
that still shows as ``PENDIENTE`` in the database.

Testing strategy:
    Unit tests. The repository (``IReleaseRepository``) and task queue
    (``ITaskQueue``) are replaced by ``AsyncMock``. The call-order test uses
    instrumented side effects to record the actual execution sequence.

Key invariants verified:
    - Launching verification on a non-existent release raises ``EntityNotFoundError``.
    - Any state other than ``PENDIENTE`` raises ``ReleaseInvalidStateError``.
    - The release is updated to ``EN_VERIFICACION`` before returning control.
    - The task ID returned by the queue is propagated to the caller.
    - ``repo.update`` executes before ``task_queue.enqueue_verification_task``.
"""

import uuid
import pytest
from unittest.mock import AsyncMock

from application.use_cases.launch_verification import LaunchVerificationUseCase, LaunchVerificationCommand
from domain.entities.release import Release
from domain.entities.enums import ReleaseStatus
from domain.exceptions import EntityNotFoundError, ReleaseInvalidStateError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_release(status: ReleaseStatus = ReleaseStatus.PENDIENTE) -> Release:
    """Builds a test ``Release`` with the specified status."""
    return Release(
        project_id=uuid.uuid4(),
        profile_id=uuid.uuid4(),
        version="1.0.0",
        created_by=uuid.uuid4(),
        status=status,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def task_queue():
    """Task queue stub that returns a predictable task ID."""
    queue = AsyncMock()
    queue.enqueue_verification_task.return_value = "task-abc-123"
    return queue


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestLaunchVerificationUseCase:
    """
    Unit tests for ``LaunchVerificationUseCase``.

    Covers domain error conditions, the complete happy path, and the
    operation-order guarantee (persist before enqueue).
    """

    async def test_release_not_found_raises_entity_not_found(self, task_queue):
        """
        A non-existent release raises ``EntityNotFoundError`` before any operation.

        Given:  A repository that returns ``None`` for any release ID.
        When:   ``LaunchVerificationUseCase`` is executed with a random ID.
        Then:   ``EntityNotFoundError`` is raised, preventing any attempt to change
                state or enqueue a task for an entity that does not exist.
        """
        repo = AsyncMock()
        repo.get_by_id.return_value = None

        with pytest.raises(EntityNotFoundError):
            await LaunchVerificationUseCase(repo, task_queue).execute(
                LaunchVerificationCommand(release_id=uuid.uuid4(), user_id=uuid.uuid4())
            )

    async def test_release_not_pendiente_raises_invalid_state(self, task_queue):
        """
        All states other than ``PENDIENTE`` produce ``ReleaseInvalidStateError``.

        Given:  Releases in states ``BORRADOR``, ``EN_VERIFICACION``, and ``COMPLETADA``.
        When:   Verification launch is attempted for each of them.
        Then:   Each attempt raises ``ReleaseInvalidStateError``, enforcing the domain
                state machine and preventing duplicate or out-of-order verifications
                that could corrupt the audit history.
        """
        for bad_status in (
            ReleaseStatus.BORRADOR,
            ReleaseStatus.EN_VERIFICACION,
            ReleaseStatus.COMPLETADA,
        ):
            repo = AsyncMock()
            repo.get_by_id.return_value = _make_release(status=bad_status)

            with pytest.raises(ReleaseInvalidStateError):
                await LaunchVerificationUseCase(repo, task_queue).execute(
                    LaunchVerificationCommand(release_id=uuid.uuid4(), user_id=uuid.uuid4())
                )

    async def test_happy_path_updates_status_to_en_verificacion(self, task_queue):
        """
        A release in ``PENDIENTE`` transitions to ``EN_VERIFICACION`` after execution.

        Given:  A release with status ``PENDIENTE`` and a repository that persists the change.
        When:   The use case executes successfully.
        Then:   The returned release object has status ``EN_VERIFICACION``,
                reflecting the state transition targeted by this use case.
        """
        release = _make_release(ReleaseStatus.PENDIENTE)
        repo = AsyncMock()
        repo.get_by_id.return_value = release
        repo.update.side_effect = lambda r: r

        updated, _ = await LaunchVerificationUseCase(repo, task_queue).execute(
            LaunchVerificationCommand(release_id=release.id, user_id=uuid.uuid4())
        )

        assert updated.status == ReleaseStatus.EN_VERIFICACION

    async def test_happy_path_enqueues_task_and_returns_task_id(self, task_queue):
        """
        The task ID returned by the queue is propagated as the second tuple element.

        Given:  A release in state ``PENDIENTE`` and a queue that returns ``"task-abc-123"``.
        When:   The use case executes successfully.
        Then:   The second element of the resulting tuple is ``"task-abc-123"`` and
                ``enqueue_verification_task`` is called exactly once with the release ID,
                guaranteeing that each launch generates a single task.
        """
        release = _make_release(ReleaseStatus.PENDIENTE)
        repo = AsyncMock()
        repo.get_by_id.return_value = release
        repo.update.side_effect = lambda r: r

        _, task_id = await LaunchVerificationUseCase(repo, task_queue).execute(
            LaunchVerificationCommand(release_id=release.id, user_id=uuid.uuid4())
        )

        assert task_id == "task-abc-123"
        task_queue.enqueue_verification_task.assert_called_once_with(release.id)

    async def test_repo_update_called_before_enqueue(self, task_queue):
        """
        State persistence occurs before the task is enqueued.

        Given:  Instrumented side effects on ``repo.update`` and
                ``task_queue.enqueue_verification_task`` that record the call order.
        When:   The use case is executed on a release in state ``PENDIENTE``.
        Then:   The recorded order is ``["update", "enqueue"]``, guaranteeing that
                no worker can process the task before the state change is committed
                to the database.

        Note:
            This ordering invariant is critical for consistency: if the task were
            enqueued first, a worker could find the release still in ``PENDIENTE``
            and reject it or process it in the wrong state.
        """
        call_order = []
        release = _make_release(ReleaseStatus.PENDIENTE)

        repo = AsyncMock()
        repo.get_by_id.return_value = release

        def mock_update(r):
            call_order.append("update")
            return r

        def mock_enqueue(rid):
            call_order.append("enqueue")
            return "task-id"

        repo.update.side_effect = mock_update
        task_queue.enqueue_verification_task.side_effect = mock_enqueue

        await LaunchVerificationUseCase(repo, task_queue).execute(
            LaunchVerificationCommand(release_id=release.id, user_id=uuid.uuid4())
        )

        assert call_order == ["update", "enqueue"]

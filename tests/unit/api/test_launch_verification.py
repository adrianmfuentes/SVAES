import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from application.use_cases.main.launch_verification import LaunchVerificationUseCase
from domain.entities.release import Release
from domain.entities.artifact import Artifact
from domain.enums import ReleaseStatus
from domain.exceptions import ValidationError

pytestmark = pytest.mark.unit


@pytest.fixture
def release_repo():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.update_status = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def task_queue():
    queue = AsyncMock()
    queue.enqueue_verification_task = AsyncMock(return_value="task-123")
    return queue


@pytest.fixture
def use_case(release_repo, task_queue):
    return LaunchVerificationUseCase(release_repo, task_queue)


@pytest.fixture
def sample_release():
    release = MagicMock()
    release.id = uuid4()
    release.status = ReleaseStatus.PENDIENTE
    release.artifacts = [MagicMock()]
    return release


def make_release(status, has_artifacts=True):
    release = MagicMock()
    release.id = uuid4()
    release.status = status
    release.artifacts = [MagicMock()] if has_artifacts else []
    return release


class TestLaunchVerification:
    async def test_launch_from_pendiente_success(self, use_case, release_repo, task_queue, sample_release):
        """Verifica el lanzamiento exitoso desde estado PENDIENTE."""
        release_repo.get_by_id.return_value = sample_release
        release_repo.update_status.return_value = sample_release

        task_id = await use_case.execute(sample_release.id)

        assert task_id == "task-123"
        release_repo.get_by_id.assert_called_once_with(sample_release.id)
        release_repo.update_status.assert_called_once_with(
            sample_release.id, ReleaseStatus.EN_VERIFICACION
        )
        task_queue.enqueue_verification_task.assert_called_once_with(sample_release.id)

    async def test_launch_from_valida_success(self, use_case, release_repo, task_queue):
        """Verifica el lanzamiento desde estado VALIDA (re-verificación)."""
        release = make_release(ReleaseStatus.VALIDA)
        release_repo.get_by_id.return_value = release

        task_id = await use_case.execute(release.id)

        assert task_id == "task-123"
        release_repo.update_status.assert_called_once_with(
            release.id, ReleaseStatus.EN_VERIFICACION
        )

    async def test_launch_from_no_valida_success(self, use_case, release_repo, task_queue):
        """Verifica el lanzamiento desde estado NO_VALIDA (re-verificación)."""
        release = make_release(ReleaseStatus.NO_VALIDA)
        release_repo.get_by_id.return_value = release

        task_id = await use_case.execute(release.id)

        assert task_id == "task-123"

    async def test_launch_from_con_advertencias_success(self, use_case, release_repo, task_queue):
        """Verifica el lanzamiento desde estado CON_ADVERTENCIAS (re-verificación)."""
        release = make_release(ReleaseStatus.CON_ADVERTENCIAS)
        release_repo.get_by_id.return_value = release

        task_id = await use_case.execute(release.id)

        assert task_id == "task-123"

    async def test_release_not_found(self, use_case, release_repo):
        """Verifica que se lance ValidationError cuando la release no existe."""
        release_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError, match="Release no encontrada"):
            await use_case.execute(uuid4())

    async def test_launch_from_invalid_status(self, use_case, release_repo):
        """Verifica que se lance ValidationError desde un estado no válido."""
        release = make_release(ReleaseStatus.ARCHIVADA)
        release_repo.get_by_id.return_value = release

        with pytest.raises(ValidationError, match="No se puede iniciar verificación"):
            await use_case.execute(release.id)

    async def test_launch_from_borrador_fails(self, use_case, release_repo):
        """Verifica que no se pueda lanzar desde estado BORRADOR."""
        release = make_release(ReleaseStatus.BORRADOR)
        release_repo.get_by_id.return_value = release

        with pytest.raises(ValidationError, match="No se puede iniciar verificación"):
            await use_case.execute(release.id)

    async def test_launch_without_artifacts(self, use_case, release_repo):
        """Verifica que se lance ValidationError cuando la release no tiene artefactos."""
        release = make_release(ReleaseStatus.PENDIENTE, has_artifacts=False)
        release_repo.get_by_id.return_value = release

        with pytest.raises(ValidationError, match="sin artefactos"):
            await use_case.execute(release.id)

    async def test_launch_from_en_verificacion_fails(self, use_case, release_repo):
        """Verifica que no se pueda lanzar cuando ya está en verificación."""
        release = make_release(ReleaseStatus.EN_VERIFICACION)
        release_repo.get_by_id.return_value = release

        with pytest.raises(ValidationError, match="No se puede iniciar verificación"):
            await use_case.execute(release.id)

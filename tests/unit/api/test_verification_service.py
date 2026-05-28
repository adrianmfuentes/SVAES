import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from application.use_cases.main.verification_service import VerificationService
from domain.entities.release import Release
from domain.entities.verification_result import VerificationResult
from domain.entities.artifact import Artifact
from domain.enums import ReleaseStatus, VerdictType
from domain.exceptions import ValidationError

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_audit_logger():
    logger = MagicMock()
    logger.log = MagicMock()
    return logger


@pytest.fixture
def release_repo():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.update_status = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def verification_repo():
    repo = AsyncMock()
    repo.find_by_id = AsyncMock(return_value=None)
    repo.find_by_release = AsyncMock(return_value=[])
    repo.save = AsyncMock()
    return repo


@pytest.fixture
def task_queue():
    queue = AsyncMock()
    queue.enqueue_verification_task = AsyncMock(return_value="task-123")
    return queue


@pytest.fixture
def connector_registry():
    registry = MagicMock()
    registry.get_by_implementation = MagicMock(return_value=None)
    return registry


@pytest.fixture
def service(release_repo, verification_repo, task_queue, connector_registry, mock_audit_logger):
    with patch(
        "application.use_cases.main.verification_service.get_audit_logger",
        return_value=mock_audit_logger,
    ):
        yield VerificationService(release_repo, verification_repo, task_queue, connector_registry)


@pytest.fixture
def sample_release():
    release = MagicMock()
    release.id = uuid4()
    release.status = ReleaseStatus.BORRADOR
    release.artifacts = [MagicMock()]
    return release


def make_release(status, has_artifacts=True):
    release = MagicMock()
    release.id = uuid4()
    release.status = status
    release.artifacts = [MagicMock()] if has_artifacts else []
    return release


class TestLaunchVerification:
    async def test_launch_from_borrador_success(self, service, release_repo, task_queue, sample_release):
        """Verifica el lanzamiento exitoso de verificación desde BORRADOR."""
        release_repo.get_by_id.return_value = sample_release
        release_repo.update_status.return_value = sample_release

        task_id = await service.launch_verification(sample_release.id, uuid4())

        assert task_id == "task-123"
        release_repo.get_by_id.assert_called_once_with(sample_release.id)
        release_repo.update_status.assert_called_once_with(
            sample_release.id, ReleaseStatus.EN_VERIFICACION
        )
        task_queue.enqueue_verification_task.assert_called_once_with(sample_release.id)

    async def test_launch_from_pendiente_success(self, service, release_repo, task_queue):
        """Verifica el lanzamiento desde PENDIENTE."""
        release = make_release(ReleaseStatus.PENDIENTE)
        release_repo.get_by_id.return_value = release

        task_id = await service.launch_verification(release.id, uuid4())

        assert task_id == "task-123"

    async def test_launch_from_valida_success(self, service, release_repo, task_queue):
        """Verifica el lanzamiento desde VALIDA (re-verificación)."""
        release = make_release(ReleaseStatus.VALIDA)
        release_repo.get_by_id.return_value = release

        task_id = await service.launch_verification(release.id, uuid4())

        assert task_id == "task-123"

    async def test_launch_from_no_valida_success(self, service, release_repo, task_queue):
        """Verifica el lanzamiento desde NO_VALIDA (re-verificación)."""
        release = make_release(ReleaseStatus.NO_VALIDA)
        release_repo.get_by_id.return_value = release

        task_id = await service.launch_verification(release.id, uuid4())

        assert task_id == "task-123"

    async def test_release_not_found(self, service, release_repo):
        """Verifica que se lance ValidationError cuando la release no existe."""
        release_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError, match="Release no encontrada"):
            await service.launch_verification(uuid4(), uuid4())

    async def test_launch_from_archivada_fails(self, service, release_repo):
        """Verifica que no se pueda lanzar desde ARCHIVADA."""
        release = make_release(ReleaseStatus.ARCHIVADA)
        release_repo.get_by_id.return_value = release

        with pytest.raises(ValidationError, match="No se puede iniciar verificación"):
            await service.launch_verification(release.id, uuid4())

    async def test_launch_from_en_verificacion_fails(self, service, release_repo):
        """Verifica que no se pueda lanzar desde EN_VERIFICACION."""
        release = make_release(ReleaseStatus.EN_VERIFICACION)
        release_repo.get_by_id.return_value = release

        with pytest.raises(ValidationError, match="No se puede iniciar verificación"):
            await service.launch_verification(release.id, uuid4())

    async def test_launch_without_artifacts(self, service, release_repo):
        """Verifica que se lance ValidationError cuando no hay artefactos."""
        release = make_release(ReleaseStatus.BORRADOR, has_artifacts=False)
        release_repo.get_by_id.return_value = release

        with pytest.raises(ValidationError, match="sin artefactos"):
            await service.launch_verification(release.id, uuid4())


class TestFetchArtifacts:
    async def test_fetch_artifacts_success(self, service, release_repo, connector_registry):
        """Verifica la obtención exitosa de artefactos a través de conectores."""
        release = MagicMock()
        release.id = uuid4()
        artifact = Artifact(
            release_id=release.id,
            connector_instance_id=uuid4(),
            connector_implementation="GITLAB",
            artifact_type="CODIGO",
            external_ref="https://gitlab.com/repo/commit/abc",
        )
        release.artifacts = [artifact]
        release_repo.get_by_id.return_value = release

        mock_connector = AsyncMock()
        mock_connector.fetch_artifact = AsyncMock(return_value={"key": "value"})
        connector_registry.get_by_implementation.return_value = mock_connector

        result = await service.fetch_artifacts_via_connectors(release.id)

        assert len(result) == 1
        assert result[0]["artifact_id"] == str(artifact.id)
        assert result[0]["type"] == "CODIGO"
        assert result[0]["connector_implementation"] == "GITLAB"
        assert result[0]["data"] == {"key": "value"}
        connector_registry.get_by_implementation.assert_called_once_with("GITLAB")

    async def test_fetch_artifacts_no_release(self, service, release_repo):
        """Verifica que se retorne lista vacía cuando la release no existe."""
        release_repo.get_by_id.return_value = None

        result = await service.fetch_artifacts_via_connectors(uuid4())

        assert result == []

    async def test_fetch_artifacts_no_artifacts(self, service, release_repo):
        """Verifica que se retorne lista vacía cuando la release no tiene artefactos."""
        release = MagicMock()
        release.artifacts = []
        release_repo.get_by_id.return_value = release

        result = await service.fetch_artifacts_via_connectors(release.id)

        assert result == []

    async def test_fetch_artifacts_connector_not_found(self, service, release_repo, connector_registry):
        """Verifica que se omitan artefactos cuyo conector no se encuentra."""
        release = MagicMock()
        release.id = uuid4()
        artifact = Artifact(
            release_id=release.id,
            connector_instance_id=uuid4(),
            connector_implementation="UNKNOWN",
            artifact_type="CODIGO",
            external_ref="ref",
        )
        release.artifacts = [artifact]
        release_repo.get_by_id.return_value = release
        connector_registry.get_by_implementation.return_value = None

        result = await service.fetch_artifacts_via_connectors(release.id)

        assert result == []

    async def test_fetch_artifacts_connector_exception_swallowed(self, service, release_repo, connector_registry):
        """Verifica que los errores del conector se traguen silenciosamente."""
        release = MagicMock()
        release.id = uuid4()
        artifact = Artifact(
            release_id=release.id,
            connector_instance_id=uuid4(),
            connector_implementation="GITLAB",
            artifact_type="CODIGO",
            external_ref="ref",
        )
        release.artifacts = [artifact]
        release_repo.get_by_id.return_value = release

        mock_connector = AsyncMock()
        mock_connector.fetch_artifact = AsyncMock(side_effect=Exception("Boom"))
        connector_registry.get_by_implementation.return_value = mock_connector

        result = await service.fetch_artifacts_via_connectors(release.id)

        assert result == []


class TestGetVerificationHistory:
    async def test_get_history_success(self, service, release_repo, verification_repo):
        """Verifica que se retorne el historial de verificaciones."""
        release = make_release(ReleaseStatus.VALIDA)
        release_repo.get_by_id.return_value = release
        results = [
            VerificationResult(
                release_id=release.id,
                verdict=VerdictType.VALID,
            ),
        ]
        verification_repo.find_by_release.return_value = results

        history = await service.get_verification_history(release.id)

        assert history == results
        verification_repo.find_by_release.assert_called_once_with(release.id)

    async def test_get_history_release_not_found(self, service, release_repo):
        """Verifica que se lance ValidationError cuando la release no existe."""
        release_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError, match="Release no encontrada"):
            await service.get_verification_history(uuid4())


class TestGetVerificationResult:
    async def test_get_result_success(self, service, release_repo, verification_repo):
        """Verifica que se obtenga un resultado de verificación correctamente."""
        release_id = uuid4()
        result_id = uuid4()
        release = make_release(ReleaseStatus.VALIDA)
        release.id = release_id
        release_repo.get_by_id.return_value = release

        result = VerificationResult(
            id=result_id,
            release_id=release_id,
            verdict=VerdictType.VALID,
        )
        verification_repo.find_by_id.return_value = result

        obtained = await service.get_verification_result(release_id, result_id)

        assert obtained == result
        verification_repo.find_by_id.assert_called_once_with(result_id)

    async def test_get_result_release_not_found(self, service, release_repo):
        """Verifica que se lance ValidationError cuando la release no existe."""
        release_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError, match="Release no encontrada"):
            await service.get_verification_result(uuid4(), uuid4())

    async def test_get_result_wrong_release(self, service, release_repo, verification_repo):
        """Verifica que se lance ValidationError cuando el resultado no pertenece a la release."""
        release_id = uuid4()
        result = VerificationResult(
            id=uuid4(),
            release_id=uuid4(),  # Diferente
            verdict=VerdictType.VALID,
        )
        release_repo.get_by_id.return_value = make_release(ReleaseStatus.VALIDA)
        verification_repo.find_by_id.return_value = result

        with pytest.raises(ValidationError, match="Resultado no pertenece"):
            await service.get_verification_result(release_id, result.id)

    async def test_get_result_not_found(self, service, release_repo, verification_repo):
        """Verifica que se retorne None cuando el resultado no existe."""
        release_repo.get_by_id.return_value = make_release(ReleaseStatus.VALIDA)
        verification_repo.find_by_id.return_value = None

        result = await service.get_verification_result(uuid4(), uuid4())

        assert result is None


class TestGetLatestVerification:
    async def test_get_latest_returns_first(self, service, verification_repo):
        """Verifica que se retorne el primer (más reciente) resultado."""
        latest = VerificationResult(
            release_id=uuid4(),
            verdict=VerdictType.VALID,
        )
        older = VerificationResult(
            release_id=uuid4(),
            verdict=VerdictType.INVALID,
        )
        verification_repo.find_by_release.return_value = [latest, older]

        result = await service.get_latest_verification(uuid4())

        assert result == latest

    async def test_get_latest_empty(self, service, verification_repo):
        """Verifica que se retorne None cuando no hay resultados."""
        verification_repo.find_by_release.return_value = []

        result = await service.get_latest_verification(uuid4())

        assert result is None

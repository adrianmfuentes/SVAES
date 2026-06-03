import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from application.use_cases.main.artifact_service import ArtifactService
from domain.entities.artifact import Artifact
from domain.enums import ArtifactType
from domain.exceptions import ValidationError

pytestmark = pytest.mark.unit


@pytest.fixture
def artifact_repo():
    repo = AsyncMock()
    repo.save = AsyncMock(side_effect=lambda a: a)
    repo.find_by_release = AsyncMock(return_value=[])
    repo.find_by_id = AsyncMock(return_value=None)
    repo.delete = AsyncMock()
    return repo


@pytest.fixture
def release_repo():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def use_case(artifact_repo, release_repo):
    return ArtifactService(artifact_repo, release_repo)


@pytest.fixture
def sample_release():
    release = MagicMock()
    release.id = uuid4()
    return release


class TestAddArtifact:
    async def test_add_artifact_success(self, use_case, artifact_repo, release_repo, sample_release):
        release_repo.get_by_id.return_value = sample_release
        conn_instance_id = uuid4()

        result = await use_case.add_artifact(
            release_id=sample_release.id,
            connector_instance_id=conn_instance_id,
            connector_implementation="GITLAB",
            artifact_type=ArtifactType.CODIGO,
            external_ref="https://gitlab.com/repo/mr/1",
        )

        assert result.release_id == sample_release.id
        assert result.connector_instance_id == conn_instance_id
        assert result.connector_implementation == "GITLAB"
        assert result.external_ref == "https://gitlab.com/repo/mr/1"
        assert result.metadata == {}
        artifact_repo.save.assert_called_once()

    async def test_add_artifact_with_metadata(self, use_case, artifact_repo, release_repo, sample_release):
        release_repo.get_by_id.return_value = sample_release
        metadata = {"key": "value", "priority": "high"}

        result = await use_case.add_artifact(
            release_id=sample_release.id,
            connector_instance_id=uuid4(),
            connector_implementation="JIRA",
            artifact_type=ArtifactType.TAREA,
            external_ref="PROJ-123",
            metadata=metadata,
        )

        assert result.metadata == metadata

    async def test_add_artifact_release_not_found(self, use_case, release_repo):
        release_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError, match="Release no encontrada"):
            await use_case.add_artifact(
                release_id=uuid4(),
                connector_instance_id=uuid4(),
                connector_implementation="GITLAB",
                artifact_type=ArtifactType.CODIGO,
                external_ref="ref",
            )

    async def test_add_artifact_queried_release(self, use_case, release_repo, sample_release):
        release_repo.get_by_id.return_value = sample_release

        await use_case.add_artifact(
            release_id=sample_release.id,
            connector_instance_id=uuid4(),
            connector_implementation="TEST",
            artifact_type=ArtifactType.TAREA,
            external_ref="T-1",
        )

        release_repo.get_by_id.assert_called_once_with(sample_release.id)


class TestListArtifacts:
    async def test_list_artifacts_returns_items(self, use_case, artifact_repo, release_repo, sample_release):
        artifacts = [
            Artifact(
                release_id=sample_release.id,
                connector_instance_id=uuid4(),
                connector_implementation="GITLAB",
                artifact_type="CODIGO",
                external_ref="ref1",
            ),
            Artifact(
                release_id=sample_release.id,
                connector_instance_id=uuid4(),
                connector_implementation="JIRA",
                artifact_type="TAREA",
                external_ref="ref2",
            ),
        ]
        release_repo.get_by_id.return_value = sample_release
        artifact_repo.find_by_release.return_value = artifacts

        result = await use_case.list_artifacts(sample_release.id)

        assert len(result) == 2
        assert result == artifacts
        artifact_repo.find_by_release.assert_called_once_with(sample_release.id)

    async def test_list_artifacts_empty(self, use_case, artifact_repo, release_repo, sample_release):
        release_repo.get_by_id.return_value = sample_release
        artifact_repo.find_by_release.return_value = []

        result = await use_case.list_artifacts(sample_release.id)

        assert result == []

    async def test_list_artifacts_release_not_found(self, use_case, release_repo):
        release_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError, match="Release no encontrada"):
            await use_case.list_artifacts(uuid4())


class TestRemoveArtifact:
    async def test_remove_artifact_success(self, use_case, artifact_repo, release_repo, sample_release):
        artifact = Artifact(
            release_id=sample_release.id,
            connector_instance_id=uuid4(),
            connector_implementation="GITLAB",
            artifact_type="CODIGO",
            external_ref="ref",
        )
        release_repo.get_by_id.return_value = sample_release
        artifact_repo.find_by_id.return_value = artifact

        await use_case.remove_artifact(sample_release.id, artifact.id)

        artifact_repo.delete.assert_called_once_with(artifact.id)

    async def test_remove_artifact_release_not_found(self, use_case, release_repo):
        release_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError, match="Release no encontrada"):
            await use_case.remove_artifact(uuid4(), uuid4())

    async def test_remove_artifact_not_found(self, use_case, artifact_repo, release_repo, sample_release):
        release_repo.get_by_id.return_value = sample_release
        artifact_repo.find_by_id.return_value = None

        with pytest.raises(ValidationError, match="Artifact no encontrado"):
            await use_case.remove_artifact(sample_release.id, uuid4())

    async def test_remove_artifact_wrong_release(self, use_case, artifact_repo, release_repo, sample_release):
        other_release_id = uuid4()
        artifact = Artifact(
            release_id=other_release_id,
            connector_instance_id=uuid4(),
            connector_implementation="GITLAB",
            artifact_type="CODIGO",
            external_ref="ref",
        )
        release_repo.get_by_id.return_value = sample_release
        artifact_repo.find_by_id.return_value = artifact

        with pytest.raises(ValidationError, match="Artifact no pertenece"):
            await use_case.remove_artifact(sample_release.id, artifact.id)

        artifact_repo.delete.assert_not_called()

    async def test_remove_artifact_does_not_delete_on_wrong_release(self, use_case, artifact_repo, release_repo, sample_release):
        other_release_id = uuid4()
        artifact = Artifact(
            release_id=other_release_id,
            connector_instance_id=uuid4(),
            connector_implementation="GITLAB",
            artifact_type="CODIGO",
            external_ref="ref",
        )
        release_repo.get_by_id.return_value = sample_release
        artifact_repo.find_by_id.return_value = artifact

        with pytest.raises(ValidationError, match="Artifact no pertenece"):
            await use_case.remove_artifact(sample_release.id, artifact.id)

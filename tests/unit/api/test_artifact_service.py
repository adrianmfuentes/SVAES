import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from domain.entities.artifact import Artifact
from domain.entities.release import Release
from domain.enums import ArtifactType, ReleaseStatus
from domain.exceptions import ValidationError

pytestmark = pytest.mark.unit


@pytest.fixture
def artifact_repo():
    repo = AsyncMock()
    repo.save = AsyncMock()
    repo.find_by_id = AsyncMock(return_value=None)
    repo.find_by_release = AsyncMock(return_value=[])
    repo.delete = AsyncMock()
    return repo


@pytest.fixture
def release_repo():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def service(artifact_repo, release_repo):
    from application.use_cases.main.artifact_service import ArtifactService
    return ArtifactService(artifact_repo, release_repo)


class TestListArtifacts:
    async def test_list_artifacts_success(self, service, artifact_repo, release_repo):
        release_id = uuid4()
        release = Release(
            id=release_id,
            name="Test",
            project_id=uuid4(),
            profile_id=uuid4(),
            version="1.0.0",
            created_by=uuid4(),
        )
        release_repo.get_by_id.return_value = release

        artifacts = [
            Artifact(
                id=uuid4(),
                release_id=release_id,
                connector_instance_id=uuid4(),
                connector_implementation="GITLAB",
                artifact_type="CODIGO",
                external_ref="ref1",
                created_at=datetime.now(timezone.utc),
            )
        ]
        artifact_repo.find_by_release.return_value = artifacts

        result = await service.list_artifacts(release_id)
        assert len(result) == 1
        artifact_repo.find_by_release.assert_called_once_with(release_id)

    async def test_list_artifacts_release_not_found(self, service, release_repo):
        release_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="Release no encontrada"):
            await service.list_artifacts(uuid4())


class TestAddArtifact:
    async def test_add_artifact_success(self, service, artifact_repo, release_repo):
        release_id = uuid4()
        connector_id = uuid4()
        release = Release(
            id=release_id,
            name="Test",
            project_id=uuid4(),
            profile_id=uuid4(),
            version="1.0.0",
            created_by=uuid4(),
        )
        release_repo.get_by_id.return_value = release

        saved_artifact = Artifact(
            id=uuid4(),
            release_id=release_id,
            connector_instance_id=connector_id,
            connector_implementation="GITLAB",
            artifact_type="CODIGO",
            external_ref="https://gitlab.com/mr/1",
            metadata={"key": "value"},
            created_at=datetime.now(timezone.utc),
        )
        artifact_repo.save.return_value = saved_artifact

        result = await service.add_artifact(
            release_id=release_id,
            connector_instance_id=connector_id,
            connector_implementation="GITLAB",
            artifact_type=ArtifactType.CODIGO,
            external_ref="https://gitlab.com/mr/1",
            metadata={"key": "value"},
        )

        assert result is not None
        assert result.connector_implementation == "GITLAB"
        artifact_repo.save.assert_called_once()

    async def test_add_artifact_release_not_found(self, service, release_repo):
        release_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="Release no encontrada"):
            await service.add_artifact(
                release_id=uuid4(),
                connector_instance_id=uuid4(),
                connector_implementation="GITLAB",
                artifact_type=ArtifactType.CODIGO,
                external_ref="ref",
            )


class TestRemoveArtifact:
    async def test_remove_artifact_success(self, service, artifact_repo, release_repo):
        release_id = uuid4()
        artifact_id = uuid4()

        release = Release(
            id=release_id,
            name="Test",
            project_id=uuid4(),
            profile_id=uuid4(),
            version="1.0.0",
            created_by=uuid4(),
        )
        release_repo.get_by_id.return_value = release

        artifact = Artifact(
            id=artifact_id,
            release_id=release_id,
            connector_instance_id=uuid4(),
            connector_implementation="GITLAB",
            artifact_type="CODIGO",
            external_ref="ref",
            created_at=datetime.now(timezone.utc),
        )
        artifact_repo.find_by_id.return_value = artifact

        await service.remove_artifact(release_id, artifact_id)

        artifact_repo.delete.assert_called_once_with(artifact_id)

    async def test_remove_artifact_release_not_found(self, service, release_repo):
        release_repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="Release no encontrada"):
            await service.remove_artifact(uuid4(), uuid4())

    async def test_remove_artifact_not_found(self, service, artifact_repo, release_repo):
        release_id = uuid4()
        release = Release(
            id=release_id,
            name="Test",
            project_id=uuid4(),
            profile_id=uuid4(),
            version="1.0.0",
            created_by=uuid4(),
        )
        release_repo.get_by_id.return_value = release
        artifact_repo.find_by_id.return_value = None

        with pytest.raises(ValidationError, match="Artifact no encontrado"):
            await service.remove_artifact(release_id, uuid4())

    async def test_remove_artifact_wrong_release(self, service, artifact_repo, release_repo):
        release_id = uuid4()
        other_release_id = uuid4()

        release = Release(
            id=release_id,
            name="Test",
            project_id=uuid4(),
            profile_id=uuid4(),
            version="1.0.0",
            created_by=uuid4(),
        )
        release_repo.get_by_id.return_value = release

        artifact = Artifact(
            id=uuid4(),
            release_id=other_release_id,
            connector_instance_id=uuid4(),
            connector_implementation="GITLAB",
            artifact_type="CODIGO",
            external_ref="ref",
            created_at=datetime.now(timezone.utc),
        )
        artifact_repo.find_by_id.return_value = artifact

        with pytest.raises(ValidationError, match="no pertenece a esta release"):
            await service.remove_artifact(release_id, artifact.id)

import pytest
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from domain.entities.artifact import Artifact

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    session.get = AsyncMock(return_value=None)
    session.execute = AsyncMock()
    return session


@pytest.fixture
def repo(mock_session):
    @asynccontextmanager
    async def _scope():
        yield mock_session

    with patch(
        "infrastructure.secondary.database.repositories.artifact_repository._session_scope",
        new=_scope,
    ):
        from infrastructure.secondary.database.repositories.artifact_repository import (
            SqlArtifactRepository,
        )
        yield SqlArtifactRepository()


class TestSave:
    async def test_save_artifact_success(self, repo, mock_session):
        artifact = Artifact(
            id=uuid4(),
            release_id=uuid4(),
            connector_instance_id=uuid4(),
            connector_implementation="GITLAB",
            artifact_type="CODIGO",
            external_ref="https://gitlab.com/mr/1",
            metadata={"key": "value"},
            created_at=datetime.now(timezone.utc),
        )
        result = await repo.save(artifact)
        assert result is not None
        assert result.connector_implementation == "GITLAB"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()


class TestFindById:
    async def test_find_by_id_returns_artifact(self, repo, mock_session):
        row = MagicMock()
        row.id = uuid4()
        row.release_id = uuid4()
        row.connector_instance_id = uuid4()
        row.connector_implementation = "JIRA"
        row.artifact_type = "TAREA"
        row.external_ref = "JIRA-123"
        row.artifact_metadata = {"priority": "high"}
        row.created_at = datetime.now(timezone.utc)

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = row
        mock_session.execute.return_value = result_mock

        artifact = await repo.find_by_id(uuid4())
        assert artifact is not None
        assert artifact.external_ref == "JIRA-123"

    async def test_find_by_id_returns_none(self, repo, mock_session):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result_mock

        artifact = await repo.find_by_id(uuid4())
        assert artifact is None


class TestFindByRelease:
    async def test_find_by_release_returns_artifacts(self, repo, mock_session):
        row = MagicMock()
        row.id = uuid4()
        row.release_id = uuid4()
        row.connector_instance_id = uuid4()
        row.connector_implementation = "GITLAB"
        row.artifact_type = "CODIGO"
        row.external_ref = "ref1"
        row.artifact_metadata = {}
        row.created_at = datetime.now(timezone.utc)

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [row]
        mock_session.execute.return_value = result_mock

        artifacts = await repo.find_by_release(uuid4())
        assert len(artifacts) == 1


class TestDelete:
    async def test_delete_artifact_success(self, repo, mock_session):
        model = MagicMock()
        mock_session.get.return_value = model

        await repo.delete(uuid4())

        mock_session.delete.assert_called_once_with(model)
        mock_session.commit.assert_called_once()

    async def test_delete_not_found(self, repo, mock_session):
        mock_session.get.return_value = None
        with pytest.raises(ValueError, match="Artifact not found"):
            await repo.delete(uuid4())

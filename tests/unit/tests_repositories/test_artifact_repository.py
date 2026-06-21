import uuid
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from infrastructure.secondary.database.repositories.artifact_repository import (
    _artifact_from_row,
    SqlArtifactRepository,
)
from domain.entities.artifact import Artifact


def _make_mock_row(**overrides):
    row = MagicMock()
    row.id = overrides.get("id", uuid.uuid4())
    row.release_id = overrides.get("release_id", uuid.uuid4())
    row.connector_instance_id = overrides.get("connector_instance_id", uuid.uuid4())
    row.connector_implementation = overrides.get("connector_implementation", "test-impl")
    row.artifact_type = overrides.get("artifact_type", "DOCUMENT")
    row.external_ref = overrides.get("external_ref", "ref-123")
    row.description = overrides.get("description", "a description")
    row.artifact_metadata = overrides.get("artifact_metadata", {"key": "value"})
    row.created_at = overrides.get("created_at", datetime(2025, 1, 1, tzinfo=timezone.utc))
    return row


class TestArtifactFromRow:
    def test_all_fields_populated(self):
        row = _make_mock_row()
        artifact = _artifact_from_row(row)

        assert isinstance(artifact, Artifact)
        assert artifact.id == row.id
        assert artifact.release_id == row.release_id
        assert artifact.connector_instance_id == row.connector_instance_id
        assert artifact.connector_implementation == row.connector_implementation
        assert artifact.artifact_type == row.artifact_type
        assert artifact.external_ref == row.external_ref
        assert artifact.description == row.description
        assert artifact.metadata == row.artifact_metadata
        assert artifact.created_at == row.created_at

    def test_empty_description_returns_empty_string(self):
        row = _make_mock_row(description="")
        artifact = _artifact_from_row(row)

        assert artifact.description == ""

    def test_none_description_returns_empty_string(self):
        row = _make_mock_row(description=None)
        artifact = _artifact_from_row(row)

        assert artifact.description == ""

    def test_none_metadata_returns_empty_dict(self):
        row = _make_mock_row(artifact_metadata=None)
        artifact = _artifact_from_row(row)

        assert artifact.metadata == {}

    def test_empty_metadata_returns_empty_dict(self):
        row = _make_mock_row(artifact_metadata={})
        artifact = _artifact_from_row(row)

        assert artifact.metadata == {}


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    session.get = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def sample_artifact():
    return Artifact(
        release_id=uuid.uuid4(),
        connector_instance_id=uuid.uuid4(),
        connector_implementation="test-impl",
        artifact_type="DOCUMENT",
        external_ref="ref-abc",
        description="test description",
        metadata={"key": "val"},
    )


class TestSqlArtifactRepository:
    @pytest.mark.asyncio
    async def test_save(self, mock_session, sample_artifact):
        @asynccontextmanager
        async def _mock_scope():
            yield mock_session

        repo = SqlArtifactRepository()

        with patch(
            "infrastructure.secondary.database.repositories.artifact_repository._session_scope",
            side_effect=_mock_scope,
        ):
            result = await repo.save(sample_artifact)

        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()
        mock_session.refresh.assert_awaited_once()
        assert isinstance(result, Artifact)
        assert result.release_id == sample_artifact.release_id
        assert result.connector_instance_id == sample_artifact.connector_instance_id
        assert result.connector_implementation == sample_artifact.connector_implementation
        assert result.external_ref == sample_artifact.external_ref
        assert result.description == sample_artifact.description
        assert result.metadata == sample_artifact.metadata

    @pytest.mark.asyncio
    async def test_find_by_id_found(self, mock_session):
        artifact_id = uuid.uuid4()
        mock_row = _make_mock_row(id=artifact_id)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_row
        mock_session.execute.return_value = mock_result

        @asynccontextmanager
        async def _mock_scope():
            yield mock_session

        repo = SqlArtifactRepository()

        with patch(
            "infrastructure.secondary.database.repositories.artifact_repository._session_scope",
            side_effect=_mock_scope,
        ):
            result = await repo.find_by_id(artifact_id)

        assert result is not None
        assert isinstance(result, Artifact)
        assert result.id == artifact_id

    @pytest.mark.asyncio
    async def test_find_by_id_not_found(self, mock_session):
        artifact_id = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        @asynccontextmanager
        async def _mock_scope():
            yield mock_session

        repo = SqlArtifactRepository()

        with patch(
            "infrastructure.secondary.database.repositories.artifact_repository._session_scope",
            side_effect=_mock_scope,
        ):
            result = await repo.find_by_id(artifact_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_find_by_release(self, mock_session):
        release_id = uuid.uuid4()
        mock_row = _make_mock_row(release_id=release_id)
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_row]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        @asynccontextmanager
        async def _mock_scope():
            yield mock_session

        repo = SqlArtifactRepository()

        with patch(
            "infrastructure.secondary.database.repositories.artifact_repository._session_scope",
            side_effect=_mock_scope,
        ):
            results = await repo.find_by_release(release_id)

        assert isinstance(results, list)
        assert len(results) == 1
        assert isinstance(results[0], Artifact)
        assert results[0].release_id == release_id

    @pytest.mark.asyncio
    async def test_find_by_release_with_pagination(self, mock_session):
        release_id = uuid.uuid4()
        mock_row = _make_mock_row(release_id=release_id)
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_row]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        @asynccontextmanager
        async def _mock_scope():
            yield mock_session

        repo = SqlArtifactRepository()

        with patch(
            "infrastructure.secondary.database.repositories.artifact_repository._session_scope",
            side_effect=_mock_scope,
        ):
            results = await repo.find_by_release(release_id, skip=10, limit=5)

        assert isinstance(results, list)
        assert len(results) == 1
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_find_by_release_empty(self, mock_session):
        release_id = uuid.uuid4()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        @asynccontextmanager
        async def _mock_scope():
            yield mock_session

        repo = SqlArtifactRepository()

        with patch(
            "infrastructure.secondary.database.repositories.artifact_repository._session_scope",
            side_effect=_mock_scope,
        ):
            results = await repo.find_by_release(release_id)

        assert isinstance(results, list)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_delete_success(self, mock_session):
        artifact_id = uuid.uuid4()
        mock_model = MagicMock()
        mock_session.get.return_value = mock_model

        @asynccontextmanager
        async def _mock_scope():
            yield mock_session

        repo = SqlArtifactRepository()

        with patch(
            "infrastructure.secondary.database.repositories.artifact_repository._session_scope",
            side_effect=_mock_scope,
        ):
            await repo.delete(artifact_id)

        mock_session.get.assert_awaited_once()
        mock_session.delete.assert_awaited_once_with(mock_model)
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, mock_session):
        artifact_id = uuid.uuid4()
        mock_session.get.return_value = None

        @asynccontextmanager
        async def _mock_scope():
            yield mock_session

        repo = SqlArtifactRepository()

        with patch(
            "infrastructure.secondary.database.repositories.artifact_repository._session_scope",
            side_effect=_mock_scope,
        ):
            with pytest.raises(ValueError, match="Artifact not found"):
                await repo.delete(artifact_id)

        mock_session.get.assert_awaited_once()
        mock_session.delete.assert_not_awaited()
        mock_session.commit.assert_not_awaited()

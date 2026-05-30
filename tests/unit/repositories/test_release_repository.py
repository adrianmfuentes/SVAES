import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
from datetime import datetime, timezone

from domain.entities.release import Release
from domain.enums import ReleaseStatus
from domain.exceptions import EntityNotFoundError

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
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_session)
    ctx.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "infrastructure.secondary.database.repositories.release_repository.select",
        return_value=MagicMock(),
    ):
        with patch(
            "infrastructure.secondary.database.repositories.release_repository.AsyncSessionLocal",
            return_value=ctx,
        ):
            with patch(
                "infrastructure.secondary.database.repositories.release_repository.ReleaseModel",
                side_effect=lambda **kw: (lambda m: (m.configure_mock(**kw), m)[1])(MagicMock()) if kw else MagicMock(),
            ):
                with patch(
                    "infrastructure.secondary.database.repositories.release_repository.ArtifactModel",
                    side_effect=lambda **kw: (lambda m: (m.configure_mock(**kw), m)[1])(MagicMock()) if kw else MagicMock(),
                ):
                    with patch(
                        "infrastructure.secondary.database.repositories.release_repository.ProjectModel",
                        side_effect=lambda **kw: (lambda m: (m.configure_mock(**kw), m)[1])(MagicMock()) if kw else MagicMock(),
                    ):
                        from infrastructure.secondary.database.repositories.release_repository import (
                            SqlReleaseRepository,
                        )
                        yield SqlReleaseRepository()


class TestCreate:
    async def test_create_release_success(self, repo, mock_session):
        release = Release(
            id=uuid4(),
            name="v1.0.0",
            version="1.0.0",
            project_id=uuid4(),
            profile_id=uuid4(),
            created_by=uuid4(),
            status=ReleaseStatus.BORRADOR,
        )
        await repo.create(release)
        assert mock_session.add.called
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()


class TestGetById:
    async def test_get_by_id_returns_release(self, repo, mock_session):
        release_id = uuid4()
        row = MagicMock()
        row.id = release_id
        row.name = "v1.0.0"
        row.version = "1.0.0"
        row.project_id = uuid4()
        row.status = ReleaseStatus.VALIDA.value
        row.profile_id = uuid4()
        row.created_by = uuid4()

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = row
        artifact_result = MagicMock()
        artifact_result.scalars.return_value.all.return_value = []
        mock_session.execute.side_effect = [result_mock, artifact_result]

        release = await repo.get_by_id(release_id)

        assert release is not None
        assert release.name == "v1.0.0"
        assert release.status == ReleaseStatus.VALIDA

    async def test_get_by_id_returns_none(self, repo, mock_session):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result_mock

        release = await repo.get_by_id(uuid4())

        assert release is None


class TestListByProject:
    async def test_list_by_project_returns_releases(self, repo, mock_session):
        row = MagicMock()
        row.id = uuid4()
        row.name = "v1.0.0"
        row.version = "1.0.0"
        row.project_id = uuid4()
        row.status = ReleaseStatus.BORRADOR.value
        row.profile_id = uuid4()
        row.created_by = uuid4()

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [row]
        mock_session.execute.return_value = result_mock

        releases = await repo.list_by_project(uuid4())

        assert len(releases) == 1
        assert releases[0].name == "v1.0.0"


class TestListByOrganization:
    async def test_list_by_organization_returns_releases(self, repo, mock_session):
        row = MagicMock()
        row.id = uuid4()
        row.name = "v1.0.0"
        row.version = "1.0.0"
        row.project_id = uuid4()
        row.status = ReleaseStatus.BORRADOR.value
        row.profile_id = uuid4()
        row.created_by = uuid4()

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [row]
        mock_session.execute.return_value = result_mock

        releases = await repo.list_by_organization(uuid4())

        assert len(releases) == 1


class TestUpdate:
    async def test_update_release_success(self, repo, mock_session):
        from domain.enums import ReleaseStatus
        release_id = uuid4()
        row = MagicMock()
        row.id = release_id
        row.name = "updated"
        row.version = "2.0.0"
        row.project_id = uuid4()
        row.status = ReleaseStatus.VALIDA.value
        row.profile_id = uuid4()
        row.created_by = uuid4()
        mock_session.get.return_value = None
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = row
        mock_session.execute.return_value = result_mock

        release = Release(
            id=release_id,
            name="updated",
            version="2.0.0",
            project_id=uuid4(),
            profile_id=uuid4(),
            created_by=uuid4(),
            status=ReleaseStatus.VALIDA,
        )
        result = await repo.update(release)

        assert result is not None
        mock_session.commit.assert_called_once()

    async def test_update_not_found_raises_error(self, repo, mock_session):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result_mock

        release = Release(
            id=uuid4(),
            name="updated",
            version="2.0.0",
            project_id=uuid4(),
            profile_id=uuid4(),
            created_by=uuid4(),
            status=ReleaseStatus.VALIDA,
        )
        with pytest.raises(EntityNotFoundError):
            await repo.update(release)


class TestUpdateStatus:
    async def test_update_status_success(self, repo, mock_session):
        release_id = uuid4()
        row = MagicMock()
        row.id = release_id
        row.name = "v1.0.0"
        row.version = "1.0.0"
        row.project_id = uuid4()
        row.status = ReleaseStatus.VALIDA.value
        row.profile_id = uuid4()
        row.created_by = uuid4()

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = row
        mock_session.execute.return_value = result_mock

        result = await repo.update_status(release_id, ReleaseStatus.VALIDA)

        assert result is not None
        mock_session.commit.assert_called_once()

    async def test_update_status_returns_none_when_not_found(self, repo, mock_session):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result_mock

        result = await repo.update_status(uuid4(), ReleaseStatus.VALIDA)

        assert result is None


class TestDelete:
    async def test_delete_release_success(self, repo, mock_session):
        release_id = uuid4()
        row = MagicMock()
        row.id = release_id
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = row
        mock_session.execute.return_value = result_mock

        await repo.delete(release_id)

        mock_session.delete.assert_called_once_with(row)
        mock_session.commit.assert_called_once()

    async def test_delete_not_found_raises_error(self, repo, mock_session):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result_mock

        with pytest.raises(EntityNotFoundError):
            await repo.delete(uuid4())


class TestArtifactOperations:
    async def test_delete_artifact_success(self, repo, mock_session):
        artifact_id = uuid4()
        artifact_row = MagicMock()
        artifact_row.id = artifact_id

        release_row = MagicMock()
        release_row.artifacts = [artifact_row]

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = release_row
        mock_session.execute.return_value = result_mock

        await repo.delete_artifact(artifact_id)

        mock_session.commit.assert_called_once()

    async def test_delete_artifact_not_found(self, repo, mock_session):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result_mock

        with pytest.raises(EntityNotFoundError):
            await repo.delete_artifact(uuid4())

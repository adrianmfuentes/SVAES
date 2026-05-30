import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from domain.entities.project import Project

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
        "infrastructure.secondary.database.repositories.project_repository.select",
        return_value=MagicMock(),
    ):
        with patch(
            "infrastructure.secondary.database.repositories.project_repository.AsyncSessionLocal",
            return_value=ctx,
        ):
            with patch(
                "infrastructure.secondary.database.repositories.project_repository.ProjectModel",
                side_effect=lambda **kw: (lambda m: (m.configure_mock(**kw), m)[1])(MagicMock()) if kw else MagicMock(),
            ):
                from infrastructure.secondary.database.repositories.project_repository import (
                    SqlProjectRepository,
                )
                yield SqlProjectRepository()


class TestCreate:
    async def test_create_project_success(self, repo, mock_session):
        project = Project(
            id=uuid4(),
            name="My Project",
            description="Test project",
            organization_id=uuid4(),
            profile_id=uuid4(),
            is_archived=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        result = await repo.create(project)
        assert result is not None
        assert result.name == "My Project"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()


class TestGetById:
    async def test_get_by_id_returns_project(self, repo, mock_session):
        row = MagicMock()
        row.id = uuid4()
        row.name = "Project X"
        row.description = "Desc"
        row.organization_id = uuid4()
        row.profile_id = uuid4()
        row.is_archived = False
        row.created_at = datetime.now(timezone.utc)
        row.updated_at = datetime.now(timezone.utc)

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = row
        mock_session.execute.return_value = result_mock

        project = await repo.get_by_id(uuid4())
        assert project is not None
        assert project.name == "Project X"

    async def test_get_by_id_returns_none(self, repo, mock_session):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result_mock

        project = await repo.get_by_id(uuid4())
        assert project is None


class TestListByOrganization:
    async def test_list_by_organization_returns_projects(self, repo, mock_session):
        row = MagicMock()
        row.id = uuid4()
        row.name = "Proj 1"
        row.description = ""
        row.organization_id = uuid4()
        row.profile_id = uuid4()
        row.is_archived = False
        row.created_at = datetime.now(timezone.utc)
        row.updated_at = datetime.now(timezone.utc)

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [row]
        mock_session.execute.return_value = result_mock

        projects = await repo.list_by_organization(uuid4())
        assert len(projects) == 1


class TestUpdate:
    async def test_update_project_success(self, repo, mock_session):
        project_id = uuid4()
        model = MagicMock()
        model.id = project_id
        mock_session.get.return_value = model

        project = Project(
            id=project_id,
            name="Updated Project",
            description="New desc",
            organization_id=uuid4(),
            profile_id=uuid4(),
            is_archived=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        result = await repo.update(project)
        assert result is not None
        mock_session.commit.assert_called_once()

    async def test_update_not_found(self, repo, mock_session):
        mock_session.get.return_value = None
        project = Project(
            id=uuid4(),
            name="Nope",
            description="",
            organization_id=uuid4(),
            profile_id=uuid4(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        with pytest.raises(ValueError, match="Project not found"):
            await repo.update(project)


class TestDelete:
    async def test_delete_project_success(self, repo, mock_session):
        model = MagicMock()
        mock_session.get.return_value = model

        await repo.delete(uuid4())

        mock_session.delete.assert_called_once_with(model)
        mock_session.commit.assert_called_once()

    async def test_delete_not_found(self, repo, mock_session):
        mock_session.get.return_value = None
        with pytest.raises(ValueError, match="Project not found"):
            await repo.delete(uuid4())

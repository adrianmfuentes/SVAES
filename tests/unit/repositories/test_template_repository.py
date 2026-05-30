import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from domain.entities.template import Template

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
        "infrastructure.secondary.database.repositories.template_repository.select",
        return_value=MagicMock(),
    ):
        with patch(
            "infrastructure.secondary.database.repositories.template_repository.AsyncSessionLocal",
            return_value=ctx,
        ):
            with patch(
                "infrastructure.secondary.database.repositories.template_repository.TemplateModel",
                side_effect=lambda **kw: (lambda m: (m.configure_mock(**kw), m)[1])(MagicMock()) if kw else MagicMock(),
            ):
                from infrastructure.secondary.database.repositories.template_repository import (
                    SqlTemplateRepository,
                )
                yield SqlTemplateRepository()


class TestCreate:
    async def test_create_template_success(self, repo, mock_session):
        template = Template(
            id=uuid4(),
            organization_id=uuid4(),
            name="Release Template",
            description="A template for releases",
            profile_id=uuid4(),
            created_by=uuid4(),
            project_name_template="PROJ-{name}",
            is_archived=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        result = await repo.create(template)
        assert result is not None
        assert result.name == "Release Template"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()


class TestGetById:
    async def test_get_by_id_returns_template(self, repo, mock_session):
        row = MagicMock()
        row.id = uuid4()
        row.organization_id = uuid4()
        row.name = "Template 1"
        row.description = "Desc"
        row.profile_id = uuid4()
        row.created_by = uuid4()
        row.project_name_template = None
        row.is_archived = False
        row.created_at = datetime.now(timezone.utc)
        row.updated_at = datetime.now(timezone.utc)

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = row
        mock_session.execute.return_value = result_mock

        tmpl = await repo.get_by_id(uuid4())
        assert tmpl is not None
        assert tmpl.name == "Template 1"

    async def test_get_by_id_returns_none(self, repo, mock_session):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result_mock

        tmpl = await repo.get_by_id(uuid4())
        assert tmpl is None


class TestListByOrganization:
    async def test_list_by_organization_returns_templates(self, repo, mock_session):
        row = MagicMock()
        row.id = uuid4()
        row.organization_id = uuid4()
        row.name = "Template A"
        row.description = ""
        row.profile_id = uuid4()
        row.created_by = uuid4()
        row.project_name_template = None
        row.is_archived = False
        row.created_at = datetime.now(timezone.utc)
        row.updated_at = datetime.now(timezone.utc)

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [row]
        mock_session.execute.return_value = result_mock

        tmpls = await repo.list_by_organization(uuid4())
        assert len(tmpls) == 1

    async def test_list_by_organization_include_archived(self, repo, mock_session):
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = result_mock

        tmpls = await repo.list_by_organization(uuid4(), include_archived=True)
        assert len(tmpls) == 0


class TestUpdate:
    async def test_update_template_success(self, repo, mock_session):
        template_id = uuid4()
        model = MagicMock()
        model.id = template_id
        mock_session.get.return_value = model

        template = Template(
            id=template_id,
            organization_id=uuid4(),
            name="Updated Template",
            description="New desc",
            profile_id=uuid4(),
            created_by=uuid4(),
            project_name_template="PROJ-{name}",
            is_archived=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        result = await repo.update(template)
        assert result is not None
        mock_session.commit.assert_called_once()

    async def test_update_not_found(self, repo, mock_session):
        mock_session.get.return_value = None
        template = Template(
            id=uuid4(),
            organization_id=uuid4(),
            name="Nope",
            description="",
            profile_id=uuid4(),
            created_by=uuid4(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        with pytest.raises(ValueError, match="Template not found"):
            await repo.update(template)


class TestDelete:
    async def test_delete_template_success(self, repo, mock_session):
        model = MagicMock()
        mock_session.get.return_value = model

        await repo.delete(uuid4())

        mock_session.delete.assert_called_once_with(model)
        mock_session.commit.assert_called_once()

    async def test_delete_not_found(self, repo, mock_session):
        mock_session.get.return_value = None
        with pytest.raises(ValueError, match="Template not found"):
            await repo.delete(uuid4())

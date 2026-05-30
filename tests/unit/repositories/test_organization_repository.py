import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from domain.entities.organization import Organization

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
        "infrastructure.secondary.database.repositories.organization_repository.select",
        return_value=MagicMock(),
    ):
        with patch(
            "infrastructure.secondary.database.repositories.organization_repository.AsyncSessionLocal",
            return_value=ctx,
        ):
            with patch(
                "infrastructure.secondary.database.repositories.organization_repository.OrganizationModel",
                side_effect=lambda **kw: (lambda m: (m.configure_mock(**kw), m)[1])(MagicMock()) if kw else MagicMock(),
            ):
                from infrastructure.secondary.database.repositories.organization_repository import (
                    SqlOrganizationRepository,
                )
                yield SqlOrganizationRepository()


class TestCreate:
    async def test_create_organization_success(self, repo, mock_session):
        org = Organization(
            id=uuid4(),
            name="Test Org",
            slug="test-org",
            owner_id=uuid4(),
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        result = await repo.create(org)

        assert result is not None
        assert result.name == "Test Org"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()


class TestGetById:
    async def test_get_by_id_returns_organization(self, repo, mock_session):
        org_id = uuid4()
        row = MagicMock()
        row.id = org_id
        row.name = "Test Org"
        row.slug = "test-org"
        row.owner_id = uuid4()
        row.is_active = True
        row.created_at = datetime.now(timezone.utc)
        row.updated_at = datetime.now(timezone.utc)

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = row
        mock_session.execute.return_value = result_mock

        org = await repo.get_by_id(org_id)
        assert org is not None
        assert org.slug == "test-org"

    async def test_get_by_id_returns_none(self, repo, mock_session):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result_mock

        org = await repo.get_by_id(uuid4())
        assert org is None


class TestGetBySlug:
    async def test_get_by_slug_returns_organization(self, repo, mock_session):
        row = MagicMock()
        row.id = uuid4()
        row.name = "My Org"
        row.slug = "my-org"
        row.owner_id = uuid4()
        row.is_active = True
        row.created_at = datetime.now(timezone.utc)
        row.updated_at = datetime.now(timezone.utc)

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = row
        mock_session.execute.return_value = result_mock

        org = await repo.get_by_slug("my-org")
        assert org is not None

    async def test_get_by_slug_returns_none(self, repo, mock_session):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result_mock

        org = await repo.get_by_slug("nope")
        assert org is None


class TestListAll:
    async def test_list_all_returns_organizations(self, repo, mock_session):
        row = MagicMock()
        row.id = uuid4()
        row.name = "Org 1"
        row.slug = "org-1"
        row.owner_id = uuid4()
        row.is_active = True
        row.created_at = datetime.now(timezone.utc)
        row.updated_at = datetime.now(timezone.utc)

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [row]
        mock_session.execute.return_value = result_mock

        orgs = await repo.list_all()
        assert len(orgs) == 1

    async def test_list_all_inactive_only(self, repo, mock_session):
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = result_mock

        orgs = await repo.list_all(active_only=False, skip=0, limit=10)
        assert len(orgs) == 0


class TestUpdate:
    async def test_update_organization_success(self, repo, mock_session):
        org_id = uuid4()
        model = MagicMock()
        model.id = org_id
        mock_session.get.return_value = model

        org = Organization(
            id=org_id,
            name="Updated Org",
            slug="updated-org",
            owner_id=uuid4(),
            is_active=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        result = await repo.update(org)
        assert result is not None
        mock_session.commit.assert_called_once()

    async def test_update_not_found_raises_error(self, repo, mock_session):
        mock_session.get.return_value = None

        org = Organization(
            id=uuid4(),
            name="Nope",
            slug="nope",
            owner_id=uuid4(),
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        with pytest.raises(ValueError, match="Organization not found"):
            await repo.update(org)

import pytest
from unittest.mock import AsyncMock, MagicMock
from application.use_cases.others.create_organization import CreateOrganizationUseCase
from domain.entities.organization import Organization
from domain.exceptions import DuplicateEntityError

pytestmark = pytest.mark.unit


@pytest.fixture
def org_repo():
    repo = AsyncMock()
    repo.get_by_slug = AsyncMock(return_value=None)
    repo.create = AsyncMock(side_effect=lambda org: org)
    return repo


@pytest.fixture
def use_case(org_repo):
    return CreateOrganizationUseCase(org_repo)


class TestCreateOrganizationSuccess:
    async def test_creates_organization(self, use_case, org_repo):
        result = await use_case.execute(name="Test Org", slug="test-org")

        assert isinstance(result, Organization)
        assert result.name == "Test Org"
        assert result.slug == "test-org"
        org_repo.get_by_slug.assert_called_once_with("test-org")
        org_repo.create.assert_called_once()

    async def test_checks_slug_uniqueness(self, use_case, org_repo):
        await use_case.execute(name="Org", slug="unique-slug")
        org_repo.get_by_slug.assert_called_once_with("unique-slug")


class TestCreateOrganizationFailure:
    async def test_duplicate_slug_raises(self, use_case, org_repo):
        existing = Organization(name="Existing Org", slug="duplicate-slug")
        org_repo.get_by_slug.return_value = existing

        with pytest.raises(DuplicateEntityError, match="duplicate-slug"):
            await use_case.execute(name="New Org", slug="duplicate-slug")

    async def test_duplicate_slug_does_not_create(self, use_case, org_repo):
        org_repo.get_by_slug.return_value = Organization(name="Exists", slug="taken")

        with pytest.raises(DuplicateEntityError):
            await use_case.execute(name="Another", slug="taken")

        org_repo.create.assert_not_called()

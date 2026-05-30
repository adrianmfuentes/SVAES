import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from domain.entities.verification_profile import VerificationProfile

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
        "infrastructure.secondary.database.repositories.profile_repository.select",
        return_value=MagicMock(),
    ):
        with patch(
            "infrastructure.secondary.database.repositories.profile_repository.AsyncSessionLocal",
            return_value=ctx,
        ):
            with patch(
                "infrastructure.secondary.database.repositories.profile_repository.VerificationProfileModel",
                side_effect=lambda **kw: (lambda m: (m.configure_mock(**kw), m)[1])(MagicMock()) if kw else MagicMock(),
            ):
                with patch(
                    "infrastructure.secondary.database.repositories.profile_repository.VerificationRuleModel",
                    side_effect=lambda **kw: (lambda m: (m.configure_mock(**kw), m)[1])(MagicMock()) if kw else MagicMock(),
                ):
                    from infrastructure.secondary.database.repositories.profile_repository import (
                        SqlProfileRepository,
                    )
                    yield SqlProfileRepository()


class TestCreate:
    async def test_create_profile_success(self, repo, mock_session):
        profile = VerificationProfile(
            id=uuid4(),
            organization_id=uuid4(),
            name="Default Profile",
            description="Test profile",
            is_default=False,
            rules=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        result = await repo.create(profile)
        assert result is not None
        assert result.name == "Default Profile"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()


class TestGetById:
    async def test_get_by_id_returns_profile(self, repo, mock_session):
        profile_id = uuid4()
        profile_row = MagicMock()
        profile_row.id = profile_id
        profile_row.organization_id = uuid4()
        profile_row.name = "My Profile"
        profile_row.description = "Desc"
        profile_row.is_default = False
        profile_row.created_at = datetime.now(timezone.utc)
        profile_row.updated_at = datetime.now(timezone.utc)

        # First execute returns profile, second returns rules (empty)
        profile_result = MagicMock()
        profile_result.scalar_one_or_none.return_value = profile_row
        rules_result = MagicMock()
        rules_result.scalars.return_value.all.return_value = []
        mock_session.execute.side_effect = [profile_result, rules_result]

        profile = await repo.get_by_id(profile_id)
        assert profile is not None
        assert profile.name == "My Profile"

    async def test_get_by_id_returns_none(self, repo, mock_session):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result_mock

        profile = await repo.get_by_id(uuid4())
        assert profile is None


class TestGetDefaultForOrganization:
    async def test_get_default_returns_profile(self, repo, mock_session):
        profile_row = MagicMock()
        profile_row.id = uuid4()
        profile_row.organization_id = uuid4()
        profile_row.name = "Default"
        profile_row.description = ""
        profile_row.is_default = True
        profile_row.created_at = datetime.now(timezone.utc)
        profile_row.updated_at = datetime.now(timezone.utc)

        result1 = MagicMock()
        result1.scalar_one_or_none.return_value = profile_row
        result2 = MagicMock()
        result2.scalar_one_or_none.return_value = MagicMock()
        result2_rules = MagicMock()
        result2_rules.scalars.return_value.all.return_value = []
        mock_session.execute.side_effect = [result1, result2, result2_rules]

        profile = await repo.get_default_for_organization(uuid4())
        assert profile is not None

    async def test_get_default_returns_none(self, repo, mock_session):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result_mock

        profile = await repo.get_default_for_organization(uuid4())
        assert profile is None


class TestUpdate:
    async def test_update_profile_success(self, repo, mock_session):
        profile_id = uuid4()
        model = MagicMock()
        model.id = profile_id
        mock_session.get.return_value = model

        profile = VerificationProfile(
            id=profile_id,
            organization_id=uuid4(),
            name="Updated",
            description="Updated desc",
            is_default=True,
            rules=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        result = await repo.update(profile)
        assert result is not None
        mock_session.commit.assert_called_once()

    async def test_update_not_found(self, repo, mock_session):
        mock_session.get.return_value = None
        profile = VerificationProfile(
            id=uuid4(),
            organization_id=uuid4(),
            name="Nope",
            description="",
            rules=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        with pytest.raises(ValueError, match="Profile not found"):
            await repo.update(profile)


class TestListByOrganization:
    async def test_list_by_organization_returns_profiles(self, repo, mock_session):
        row = MagicMock()
        row.id = uuid4()
        row.organization_id = uuid4()
        row.name = "Profile 1"
        row.description = ""
        row.is_default = False
        row.created_at = datetime.now(timezone.utc)
        row.updated_at = datetime.now(timezone.utc)

        profiles_result = MagicMock()
        profiles_result.scalars.return_value.all.return_value = [row]
        rules_result = MagicMock()
        rules_result.scalars.return_value.all.return_value = []
        mock_session.execute.side_effect = [profiles_result, rules_result]

        profiles = await repo.list_by_organization(uuid4())
        assert len(profiles) == 1


class TestDelete:
    async def test_delete_profile_success(self, repo, mock_session):
        profile_id = uuid4()
        model = MagicMock()
        mock_session.get.return_value = model

        await repo.delete(profile_id)

        mock_session.delete.assert_called_once_with(model)
        mock_session.commit.assert_called_once()

    async def test_delete_not_found(self, repo, mock_session):
        mock_session.get.return_value = None
        with pytest.raises(ValueError, match="Profile not found"):
            await repo.delete(uuid4())

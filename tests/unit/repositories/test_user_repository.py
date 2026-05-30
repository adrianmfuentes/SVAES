import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from domain.entities.user import User
from domain.enums import UserRole

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
        "infrastructure.secondary.database.repositories.user_repository.select",
        return_value=MagicMock(),
    ):
        with patch(
            "infrastructure.secondary.database.repositories.user_repository.AsyncSessionLocal",
            return_value=ctx,
        ):
            with patch(
                "infrastructure.secondary.database.repositories.user_repository.UserModel",
                side_effect=lambda **kw: (lambda m: (m.configure_mock(**kw), m)[1])(MagicMock()) if kw else MagicMock(),
            ):
                from infrastructure.secondary.database.repositories.user_repository import (
                    SqlUserRepository,
                )
                yield SqlUserRepository()


class TestCreate:
    async def test_create_user_success(self, repo, mock_session):
        user = User(
            id=uuid4(),
            email="test@example.com",
            hashed_password="hashed_abc",
            display_name="Test User",
            role=UserRole.U2,
            organization_ids=[uuid4()],
            is_active=True,
            failed_login_attempts=0,
            locked_until=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        result = await repo.create(user)
        assert result is not None
        assert result.email == "test@example.com"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()


class TestGetById:
    async def test_get_by_id_returns_user(self, repo, mock_session):
        org_id = uuid4()
        row = MagicMock()
        row.id = uuid4()
        row.email = "user@test.com"
        row.hashed_password = "hash"
        row.display_name = "User"
        row.role = UserRole.U2.value
        row.organization_id = org_id
        row.is_active = True
        row.failed_login_attempts = 0
        row.locked_until = None
        row.created_at = datetime.now(timezone.utc)
        row.updated_at = datetime.now(timezone.utc)
        row.terms_accepted_at = None
        row.privacy_accepted_at = None

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = row
        mock_session.execute.return_value = result_mock

        user = await repo.get_by_id(uuid4())
        assert user is not None
        assert user.email == "user@test.com"

    async def test_get_by_id_returns_none(self, repo, mock_session):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result_mock

        user = await repo.get_by_id(uuid4())
        assert user is None


class TestGetByEmail:
    async def test_get_by_email_returns_user(self, repo, mock_session):
        org_id = uuid4()
        row = MagicMock()
        row.id = uuid4()
        row.email = "test@example.com"
        row.hashed_password = "hash"
        row.display_name = "Tester"
        row.role = UserRole.U3.value
        row.organization_id = org_id
        row.is_active = True
        row.failed_login_attempts = 0
        row.locked_until = None
        row.created_at = datetime.now(timezone.utc)
        row.updated_at = datetime.now(timezone.utc)
        row.terms_accepted_at = None
        row.privacy_accepted_at = None

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = row
        mock_session.execute.return_value = result_mock

        user = await repo.get_by_email("test@example.com")
        assert user is not None
        assert user.email == "test@example.com"

    async def test_get_by_email_returns_none(self, repo, mock_session):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result_mock

        user = await repo.get_by_email("nope@test.com")
        assert user is None


class TestListAll:
    async def test_list_all_returns_users(self, repo, mock_session):
        org_id = uuid4()
        row = MagicMock()
        row.id = uuid4()
        row.email = "user@test.com"
        row.hashed_password = "hash"
        row.display_name = "User"
        row.role = UserRole.U2.value
        row.organization_id = org_id
        row.is_active = True
        row.failed_login_attempts = 0
        row.locked_until = None
        row.created_at = datetime.now(timezone.utc)
        row.updated_at = datetime.now(timezone.utc)
        row.terms_accepted_at = None
        row.privacy_accepted_at = None

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [row]
        mock_session.execute.return_value = result_mock

        users = await repo.list_all()
        assert len(users) == 1

    async def test_list_all_with_org_filter(self, repo, mock_session):
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = result_mock

        users = await repo.list_all(organization_id=uuid4(), active_only=False)
        assert len(users) == 0


class TestUpdate:
    async def test_update_user_success(self, repo, mock_session):
        user_id = uuid4()
        model = MagicMock()
        model.id = user_id
        mock_session.get.return_value = model

        user = User(
            id=user_id,
            email="updated@test.com",
            hashed_password="newhash",
            display_name="Updated",
            role=UserRole.U4,
            organization_ids=[uuid4()],
            is_active=False,
            failed_login_attempts=1,
            locked_until=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        result = await repo.update(user)
        assert result is not None
        mock_session.commit.assert_called_once()

    async def test_update_not_found(self, repo, mock_session):
        mock_session.get.return_value = None
        user = User(
            id=uuid4(),
            email="nope@test.com",
            hashed_password="hash",
            display_name="Nope",
            role=UserRole.U2,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        with pytest.raises(ValueError, match="User not found"):
            await repo.update(user)


class TestDelete:
    async def test_delete_user_success(self, repo, mock_session):
        model = MagicMock()
        mock_session.get.return_value = model

        await repo.delete(uuid4())

        mock_session.delete.assert_called_once_with(model)
        mock_session.commit.assert_called_once()

    async def test_delete_not_found(self, repo, mock_session):
        mock_session.get.return_value = None
        with pytest.raises(ValueError, match="User not found"):
            await repo.delete(uuid4())

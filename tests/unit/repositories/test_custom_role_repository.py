import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from domain.entities.custom_role import CustomRole
from domain.enums import Permission

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
        "infrastructure.secondary.database.repositories.custom_role_repository.select",
        return_value=MagicMock(),
    ):
        with patch(
            "infrastructure.secondary.database.repositories.custom_role_repository.AsyncSessionLocal",
            return_value=ctx,
        ):
            with patch(
                "infrastructure.secondary.database.repositories.custom_role_repository.CustomRoleModel",
                side_effect=lambda **kw: (lambda m: (m.configure_mock(**kw), m)[1])(MagicMock()) if kw else MagicMock(),
            ):
                from infrastructure.secondary.database.repositories.custom_role_repository import (
                    SqlCustomRoleRepository,
                )
                yield SqlCustomRoleRepository()


class TestCreate:
    async def test_create_role_success(self, repo, mock_session):
        role = CustomRole(
            id=uuid4(),
            organization_id=uuid4(),
            name="Developer",
            permissions=[Permission.VIEW_DASHBOARD, Permission.CREATE_RELEASE],
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        result = await repo.create(role)
        assert result is not None
        assert result.name == "Developer"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()


class TestGetById:
    async def test_get_by_id_returns_role(self, repo, mock_session):
        row = MagicMock()
        row.id = uuid4()
        row.organization_id = uuid4()
        row.name = "Reviewer"
        row.permissions = [
            Permission.VIEW_DASHBOARD.value,
            Permission.EXECUTE_VERIFICATION.value,
        ]
        row.is_active = True
        row.created_at = datetime.now(timezone.utc)
        row.updated_at = datetime.now(timezone.utc)

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = row
        mock_session.execute.return_value = result_mock

        role = await repo.get_by_id(uuid4())
        assert role is not None
        assert role.name == "Reviewer"

    async def test_get_by_id_returns_none(self, repo, mock_session):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result_mock

        role = await repo.get_by_id(uuid4())
        assert role is None


class TestListByOrganization:
    async def test_list_by_organization_returns_roles(self, repo, mock_session):
        row = MagicMock()
        row.id = uuid4()
        row.organization_id = uuid4()
        row.name = "Admin"
        row.permissions = [Permission.MANAGE_ROLES.value]
        row.is_active = True
        row.created_at = datetime.now(timezone.utc)
        row.updated_at = datetime.now(timezone.utc)

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [row]
        mock_session.execute.return_value = result_mock

        roles = await repo.list_by_organization(uuid4())
        assert len(roles) == 1


class TestUpdate:
    async def test_update_role_success(self, repo, mock_session):
        role_id = uuid4()
        model = MagicMock()
        model.id = role_id
        mock_session.get.return_value = model

        role = CustomRole(
            id=role_id,
            organization_id=uuid4(),
            name="Updated Role",
            permissions=[Permission.INVITE_USERS],
            is_active=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        result = await repo.update(role)
        assert result is not None
        mock_session.commit.assert_called_once()

    async def test_update_not_found(self, repo, mock_session):
        mock_session.get.return_value = None
        role = CustomRole(
            id=uuid4(),
            organization_id=uuid4(),
            name="Nope",
            permissions=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        with pytest.raises(ValueError, match="Custom role not found"):
            await repo.update(role)


class TestDelete:
    async def test_delete_role_success(self, repo, mock_session):
        model = MagicMock()
        mock_session.get.return_value = model

        await repo.delete(uuid4())

        mock_session.delete.assert_called_once_with(model)
        mock_session.commit.assert_called_once()

    async def test_delete_not_found(self, repo, mock_session):
        mock_session.get.return_value = None
        with pytest.raises(ValueError, match="Custom role not found"):
            await repo.delete(uuid4())

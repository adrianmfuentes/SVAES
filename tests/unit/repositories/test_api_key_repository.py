import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from domain.entities.api_key import APIKey

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
        "infrastructure.secondary.database.repositories.api_key_repository.AsyncSessionLocal",
        return_value=ctx,
    ):
        from infrastructure.secondary.database.repositories.api_key_repository import (
            SqlAPIKeyRepository,
        )
        yield SqlAPIKeyRepository()


class TestSave:
    async def test_save_api_key_success(self, repo, mock_session):
        api_key = APIKey(
            id=uuid4(),
            user_id=uuid4(),
            organization_id=uuid4(),
            name="My API Key",
            key_hash="abc123hash",
            prefix="svk_test",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            expires_at=None,
            last_used_at=None,
        )
        result = await repo.save(api_key)
        assert result is not None
        assert result.name == "My API Key"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()


class TestGetById:
    async def test_get_by_id_returns_key(self, repo, mock_session):
        row = MagicMock()
        row.id = uuid4()
        row.user_id = uuid4()
        row.organization_id = uuid4()
        row.name = "Test Key"
        row.key_hash = "hash"
        row.prefix = "svk_pref"
        row.is_active = True
        row.created_at = datetime.now(timezone.utc)
        row.expires_at = None
        row.last_used_at = None

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = row
        mock_session.execute.return_value = result_mock

        key = await repo.get_by_id(uuid4())
        assert key is not None
        assert key.name == "Test Key"

    async def test_get_by_id_returns_none(self, repo, mock_session):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result_mock

        key = await repo.get_by_id(uuid4())
        assert key is None


class TestGetByHash:
    async def test_get_by_hash_returns_key(self, repo, mock_session):
        row = MagicMock()
        row.id = uuid4()
        row.user_id = uuid4()
        row.organization_id = uuid4()
        row.name = "Hashed Key"
        row.key_hash = "myhash"
        row.prefix = "svk_pref"
        row.is_active = True
        row.created_at = datetime.now(timezone.utc)
        row.expires_at = None
        row.last_used_at = None

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = row
        mock_session.execute.return_value = result_mock

        key = await repo.get_by_hash("myhash")
        assert key is not None

    async def test_get_by_hash_returns_none(self, repo, mock_session):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result_mock

        key = await repo.get_by_hash("nohash")
        assert key is None


class TestListByOrganization:
    async def test_list_by_organization_returns_keys(self, repo, mock_session):
        row = MagicMock()
        row.id = uuid4()
        row.user_id = uuid4()
        row.organization_id = uuid4()
        row.name = "Key 1"
        row.key_hash = "hash1"
        row.prefix = "svk_a"
        row.is_active = True
        row.created_at = datetime.now(timezone.utc)
        row.expires_at = None
        row.last_used_at = None

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [row]
        mock_session.execute.return_value = result_mock

        keys = await repo.list_by_organization(uuid4())
        assert len(keys) == 1


class TestListByUser:
    async def test_list_by_user_returns_keys(self, repo, mock_session):
        row = MagicMock()
        row.id = uuid4()
        row.user_id = uuid4()
        row.organization_id = uuid4()
        row.name = "User Key"
        row.key_hash = "hash2"
        row.prefix = "svk_b"
        row.is_active = True
        row.created_at = datetime.now(timezone.utc)
        row.expires_at = None
        row.last_used_at = None

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [row]
        mock_session.execute.return_value = result_mock

        keys = await repo.list_by_user(uuid4())
        assert len(keys) == 1


class TestUpdate:
    async def test_update_api_key_success(self, repo, mock_session):
        key_id = uuid4()
        model = MagicMock()
        model.id = key_id
        mock_session.get.return_value = model

        api_key = APIKey(
            id=key_id,
            user_id=uuid4(),
            organization_id=uuid4(),
            name="Updated Key",
            key_hash="hash",
            prefix="svk_pref",
            is_active=False,
            created_at=datetime.now(timezone.utc),
            expires_at=None,
            last_used_at=None,
        )
        result = await repo.update(api_key)
        assert result is not None
        assert result.name == "Updated Key"
        mock_session.commit.assert_called_once()

    async def test_update_not_found(self, repo, mock_session):
        mock_session.get.return_value = None
        api_key = APIKey(
            id=uuid4(),
            user_id=uuid4(),
            organization_id=uuid4(),
            name="Nope",
            key_hash="hash",
            prefix="svk_test",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        with pytest.raises(ValueError, match="API key not found"):
            await repo.update(api_key)


class TestDelete:
    async def test_delete_api_key_success(self, repo, mock_session):
        model = MagicMock()
        mock_session.get.return_value = model

        await repo.delete(uuid4())

        mock_session.delete.assert_called_once_with(model)
        mock_session.commit.assert_called_once()

    async def test_delete_not_found(self, repo, mock_session):
        mock_session.get.return_value = None
        with pytest.raises(ValueError, match="API key not found"):
            await repo.delete(uuid4())


class TestHashKey:
    def test_hash_key_returns_sha256(self):
        from infrastructure.secondary.database.repositories.api_key_repository import (
            SqlAPIKeyRepository,
        )
        repo = SqlAPIKeyRepository()
        result = repo.hash_key("test-key-123")
        assert len(result) == 64
        assert isinstance(result, str)

    def test_hash_key_consistent(self):
        from infrastructure.secondary.database.repositories.api_key_repository import (
            SqlAPIKeyRepository,
        )
        repo = SqlAPIKeyRepository()
        key = "consistent-key"
        result1 = repo.hash_key(key)
        result2 = repo.hash_key(key)
        assert result1 == result2

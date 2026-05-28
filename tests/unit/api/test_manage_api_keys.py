import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timedelta, timezone

from application.use_cases.others.manage_api_keys import ManageApiKeysUseCase
from domain.entities.api_key import APIKey
from domain.exceptions import EntityNotFoundError, ValidationError

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_audit_logger():
    logger = MagicMock()
    logger.log = MagicMock()
    return logger


@pytest.fixture
def api_key_repo():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.get_by_hash = AsyncMock(return_value=None)
    repo.save = AsyncMock()
    repo.update = AsyncMock()
    repo.list_by_user = AsyncMock(return_value=[])
    repo.list_by_organization = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def use_case(api_key_repo, mock_audit_logger):
    with patch(
        "application.use_cases.others.manage_api_keys.get_audit_logger",
        return_value=mock_audit_logger,
    ):
        yield ManageApiKeysUseCase(api_key_repo)


@pytest.fixture
def sample_api_key():
    return APIKey(
        id=uuid4(),
        user_id=uuid4(),
        organization_id=uuid4(),
        name="Test Key",
        key_hash="hash123",
        prefix="svk_abc12345",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


class TestCreateApiKey:
    async def test_create_api_key_success(self, use_case, api_key_repo):
        """Verifica la creación exitosa de una API key."""
        user_id = uuid4()
        org_id = uuid4()
        saved_key = APIKey(
            id=uuid4(),
            user_id=user_id,
            organization_id=org_id,
            name="My Key",
            key_hash="hash123",
            prefix="svk_abc12345",
            is_active=True,
            expires_at=None,
            created_at=datetime.now(timezone.utc),
        )
        api_key_repo.save.return_value = saved_key
        api_key_repo.list_by_user.return_value = []

        result = await use_case.create_api_key(
            user_id=user_id,
            organization_id=org_id,
            name="My Key",
        )

        assert result["name"] == "My Key"
        assert result["user_id"] == str(user_id)
        assert result["organization_id"] == str(org_id)
        assert result["key"].startswith("svk_")
        assert result["prefix"] == "svk_abc12345"
        assert result["is_active"] is True
        assert result["expires_at"] is None
        api_key_repo.save.assert_called_once()

    async def test_create_api_key_with_expiry(self, use_case, api_key_repo):
        """Verifica la creación de una API key con fecha de expiración."""
        user_id = uuid4()
        org_id = uuid4()
        saved_key = APIKey(
            id=uuid4(),
            user_id=user_id,
            organization_id=org_id,
            name="Expiring Key",
            key_hash="hash",
            prefix="svk_abc12345",
            is_active=True,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            created_at=datetime.now(timezone.utc),
        )
        api_key_repo.save.return_value = saved_key
        api_key_repo.list_by_user.return_value = []

        result = await use_case.create_api_key(
            user_id=user_id,
            organization_id=org_id,
            name="Expiring Key",
            expires_in_days=30,
        )

        assert result["expires_at"] is not None
        assert result["name"] == "Expiring Key"

    async def test_create_api_key_empty_name(self, use_case):
        """Verifica que se lance ValidationError cuando el nombre está vacío."""
        with pytest.raises(ValidationError, match="nombre"):
            await use_case.create_api_key(
                user_id=uuid4(),
                organization_id=uuid4(),
                name="",
            )

    async def test_create_api_key_none_name(self, use_case):
        """Verifica que se lance ValidationError cuando el nombre es None."""
        with pytest.raises(ValidationError, match="nombre"):
            await use_case.create_api_key(
                user_id=uuid4(),
                organization_id=uuid4(),
                name=None,
            )

    async def test_create_api_key_max_active_keys(self, use_case, api_key_repo):
        """Verifica que se lance ValidationError cuando hay 5 keys activas."""
        active_keys = [
            APIKey(
                id=uuid4(),
                user_id=uuid4(),
                organization_id=uuid4(),
                name=f"Key {i}",
                key_hash=f"hash{i}",
                prefix=f"pfx{i}",
                is_active=True,
                created_at=datetime.now(timezone.utc),
            )
            for i in range(5)
        ]
        api_key_repo.list_by_user.return_value = active_keys

        with pytest.raises(ValidationError, match="límite máximo"):
            await use_case.create_api_key(
                user_id=uuid4(),
                organization_id=uuid4(),
                name="Over Limit",
            )

    async def test_create_api_key_ignores_inactive_keys(self, use_case, api_key_repo):
        """Verifica que las keys inactivas no cuenten para el límite."""
        inactive_keys = [
            APIKey(
                id=uuid4(),
                user_id=uuid4(),
                organization_id=uuid4(),
                name=f"Key {i}",
                key_hash=f"hash{i}",
                prefix=f"pfx{i}",
                is_active=False,
                created_at=datetime.now(timezone.utc),
            )
            for i in range(10)
        ]
        api_key_repo.list_by_user.return_value = inactive_keys
        saved_key = APIKey(
            id=uuid4(),
            user_id=uuid4(),
            organization_id=uuid4(),
            name="New Active",
            key_hash="hash",
            prefix="prefix123",
            is_active=True,
            expires_at=None,
            created_at=datetime.now(timezone.utc),
        )
        api_key_repo.save.return_value = saved_key

        result = await use_case.create_api_key(
            user_id=uuid4(),
            organization_id=uuid4(),
            name="New Active",
        )

        assert result["name"] == "New Active"


class TestListApiKeys:
    async def test_list_api_keys(self, use_case, sample_api_key, api_key_repo):
        """Verifica el listado de API keys de un usuario."""
        api_key_repo.list_by_user.return_value = [sample_api_key]

        result = await use_case.list_api_keys(sample_api_key.user_id)

        assert len(result) == 1
        assert result[0]["name"] == "Test Key"
        assert result[0]["prefix"] == "svk_abc12345"
        api_key_repo.list_by_user.assert_called_once_with(sample_api_key.user_id)

    async def test_list_api_keys_empty(self, use_case, api_key_repo):
        """Verifica que se retorne una lista vacía cuando no hay keys."""
        result = await use_case.list_api_keys(uuid4())
        assert result == []

    async def test_list_api_keys_shows_expires_at(self, use_case, api_key_repo):
        """Verifica que expires_at se muestre correctamente."""
        key = APIKey(
            id=uuid4(),
            user_id=uuid4(),
            organization_id=uuid4(),
            name="Key",
            key_hash="hash",
            prefix="pfx",
            is_active=True,
            expires_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
        )
        api_key_repo.list_by_user.return_value = [key]

        result = await use_case.list_api_keys(uuid4())

        assert result[0]["expires_at"] is not None


class TestRevokeApiKey:
    async def test_revoke_api_key_success(self, use_case, sample_api_key, api_key_repo):
        """Verifica la revocación exitosa de una API key."""
        api_key_repo.get_by_id.return_value = sample_api_key
        api_key_repo.update.return_value = sample_api_key

        result = await use_case.revoke_api_key(sample_api_key.id, sample_api_key.user_id)

        assert result["is_active"] is False
        assert sample_api_key.is_active is False
        api_key_repo.update.assert_called_once_with(sample_api_key)

    async def test_revoke_api_key_empty_id(self, use_case):
        """Verifica que se lance ValidationError cuando key_id está vacío."""
        with pytest.raises(ValidationError, match="key_id es requerido"):
            await use_case.revoke_api_key(None, uuid4())

    async def test_revoke_api_key_not_found(self, use_case, api_key_repo):
        """Verifica que se lance EntityNotFoundError cuando la key no existe."""
        api_key_repo.get_by_id.return_value = None

        with pytest.raises(EntityNotFoundError, match="API key no encontrado"):
            await use_case.revoke_api_key(uuid4(), uuid4())

    async def test_revoke_api_key_wrong_user(self, use_case, api_key_repo, sample_api_key):
        """Verifica que se lance EntityNotFoundError cuando la key pertenece a otro usuario."""
        api_key_repo.get_by_id.return_value = sample_api_key

        with pytest.raises(EntityNotFoundError, match="API key no encontrado"):
            await use_case.revoke_api_key(sample_api_key.id, uuid4())


class TestValidateApiKey:
    async def test_validate_api_key_success(self, use_case, api_key_repo):
        """Verifica la validación exitosa de una API key."""
        key = APIKey(
            id=uuid4(),
            user_id=uuid4(),
            organization_id=uuid4(),
            name="Valid Key",
            key_hash="hash123",
            prefix="svk_abc",
            is_active=True,
            expires_at=None,
            created_at=datetime.now(timezone.utc),
        )
        api_key_repo.get_by_hash.return_value = key

        result = await use_case.validate_api_key("svk_validkey123")

        assert result == key
        assert key.last_used_at is not None
        api_key_repo.update.assert_called_once_with(key)

    async def test_validate_api_key_not_found(self, use_case, api_key_repo):
        """Verifica que se retorne None cuando la key no existe por hash."""
        api_key_repo.get_by_hash.return_value = None

        result = await use_case.validate_api_key("invalid-key")

        assert result is None

    async def test_validate_api_key_inactive(self, use_case, api_key_repo):
        """Verifica que se retorne None cuando la key está inactiva."""
        key = APIKey(
            id=uuid4(),
            user_id=uuid4(),
            organization_id=uuid4(),
            name="Inactive Key",
            key_hash="hash",
            prefix="svk_abc",
            is_active=False,
            created_at=datetime.now(timezone.utc),
        )
        api_key_repo.get_by_hash.return_value = key

        result = await use_case.validate_api_key("svk_inactive")

        assert result is None

    async def test_validate_api_key_expired(self, use_case, api_key_repo):
        """Verifica que se retorne None cuando la key está expirada."""
        key = APIKey(
            id=uuid4(),
            user_id=uuid4(),
            organization_id=uuid4(),
            name="Expired Key",
            key_hash="hash",
            prefix="svk_abc",
            is_active=True,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
            created_at=datetime.now(timezone.utc),
        )
        api_key_repo.get_by_hash.return_value = key

        result = await use_case.validate_api_key("svk_expired")

        assert result is None

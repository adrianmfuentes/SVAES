import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from cryptography.fernet import Fernet
from application.use_cases.main.connector_service import ConnectorService
from domain.entities.connector_instance import ConnectorInstance
from domain.enums import ConnectorStatus, ConnectorType, ConnectorImplementation
from domain.exceptions import EntityNotFoundError, ValidationError, DuplicateEntityError, ConnectorConnectionFailedError
from core.audit import AuditEvent

_VALID_KEY = Fernet.generate_key()
_VALID_KEY_STR = _VALID_KEY.decode()


def _make_connector(**overrides) -> ConnectorInstance:
    defaults = {
        "id": uuid4(),
        "organization_id": uuid4(),
        "connector_type": ConnectorType.REPO_CODIGO.value,
        "connector_implementation": ConnectorImplementation.GITLAB.value,
        "name": "GitLab Test",
        "encrypted_credentials": b"fake-encrypted",
        "status": ConnectorStatus.ACTIVO,
    }
    defaults.update(overrides)
    return ConnectorInstance(**defaults)


@pytest.fixture
def mock_audit_logger():
    logger = MagicMock()
    logger.log = MagicMock()
    return logger


@pytest.fixture
def connector_repo():
    repo = AsyncMock()
    repo.save = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.update = AsyncMock()
    repo.delete = AsyncMock()
    repo.list_by_organization = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def connector_registry():
    registry = MagicMock()
    registry.get_by_implementation = MagicMock(return_value=None)
    return registry


@pytest.fixture
def service(connector_repo, connector_registry, mock_audit_logger):
    with patch(
        "application.use_cases.main.connector_service.get_audit_logger",
        return_value=mock_audit_logger,
    ), patch(
        "core.config.settings.encryption_key",
        _VALID_KEY_STR,
    ):
        yield ConnectorService(connector_repo, connector_registry)


pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Tests: list_connectors
# ---------------------------------------------------------------------------

class TestListConnectors:
    async def test_list_connectors_returns_items(self, service, connector_repo):
        """Verifica que se listen correctamente los conectores de una organizacion."""
        org_id = uuid4()
        connector = _make_connector(organization_id=org_id)
        connector_repo.list_by_organization.return_value = [connector]

        result = await service.list_connectors(org_id, active_only=True)

        assert len(result) == 1
        assert result[0] == connector
        connector_repo.list_by_organization.assert_called_once_with(
            org_id, active_only=True, skip=0, limit=50
        )

    async def test_list_connectors_empty(self, service, connector_repo):
        """Verifica que se retorne una lista vacia cuando no hay conectores."""
        org_id = uuid4()
        connector_repo.list_by_organization.return_value = []

        result = await service.list_connectors(org_id)

        assert result == []
        connector_repo.list_by_organization.assert_called_once_with(
            org_id, active_only=True, skip=0, limit=50
        )

    async def test_list_connectors_inactive_only(self, service, connector_repo):
        """Verifica que active_only=False delegue correctamente al repositorio."""
        org_id = uuid4()
        connector_repo.list_by_organization.return_value = []

        await service.list_connectors(org_id, active_only=False)

        connector_repo.list_by_organization.assert_called_once_with(
            org_id, active_only=False, skip=0, limit=50
        )


# ---------------------------------------------------------------------------
# Tests: get_connector
# ---------------------------------------------------------------------------

class TestGetConnector:
    async def test_get_connector_found(self, service, connector_repo):
        """Verifica que al buscar un conector existente se retorne el objeto correcto."""
        connector = _make_connector()
        connector_repo.get_by_id.return_value = connector

        result = await service.get_connector(connector.id)

        assert result == connector
        connector_repo.get_by_id.assert_called_once_with(connector.id)

    async def test_get_connector_not_found(self, service, connector_repo):
        """Verifica que se retorne None cuando el conector solicitado no existe."""
        connector_id = uuid4()
        connector_repo.get_by_id.return_value = None

        result = await service.get_connector(connector_id)

        assert result is None
        connector_repo.get_by_id.assert_called_once_with(connector_id)


# ---------------------------------------------------------------------------
# Tests: register_connector
# ---------------------------------------------------------------------------

class TestRegisterConnector:
    async def test_register_connector_success(self, service, connector_repo, mock_audit_logger):
        """Verifica el registro exitoso de un conector con credenciales encriptadas y auditoria."""
        org_id = uuid4()
        user_id = uuid4()
        config = {"url": "https://gitlab.com/api/v4", "token": "secret-token"}
        connector_repo.list_by_organization.return_value = []
        connector_repo.save.side_effect = lambda c: c

        result = await service.register_connector(
            organization_id=org_id,
            connector_type=ConnectorType.REPO_CODIGO.value,
            connector_implementation=ConnectorImplementation.GITLAB.value,
            name="GitLab Production",
            config=config,
            requested_by=user_id,
        )

        assert result.organization_id == org_id
        assert result.connector_type == ConnectorType.REPO_CODIGO.value
        assert result.connector_implementation == ConnectorImplementation.GITLAB.value
        assert result.name == "GitLab Production"
        assert result.status == ConnectorStatus.ACTIVO
        assert result.encrypted_credentials != b""

        fernet = Fernet(_VALID_KEY)
        decrypted = eval(fernet.decrypt(result.encrypted_credentials).decode())
        assert decrypted == config

        connector_repo.save.assert_called_once()
        mock_audit_logger.log.assert_called_once()
        call_arg = mock_audit_logger.log.call_args[0][0]
        assert call_arg.event == AuditEvent.CONNECTOR_CREATED
        assert call_arg.user_id == user_id
        assert call_arg.organization_id == org_id
        assert call_arg.resource_type == "connector"
        assert call_arg.resource_id == result.id
        assert call_arg.details["name"] == "GitLab Production"

    async def test_register_connector_duplicate_same_implementation(self, service, connector_repo):
        """Verifica que se lance DuplicateEntityError al registrar un conector duplicado."""
        org_id = uuid4()
        user_id = uuid4()
        existing = _make_connector(
            organization_id=org_id,
            connector_implementation=ConnectorImplementation.GITLAB.value,
        )
        connector_repo.list_by_organization.return_value = [existing]

        with pytest.raises(DuplicateEntityError, match="Ya existe un conector"):
            await service.register_connector(
                organization_id=org_id,
                connector_type=ConnectorType.REPO_CODIGO.value,
                connector_implementation=ConnectorImplementation.GITLAB.value,
                name="Another GitLab",
                config={"url": "https://example.com"},
                requested_by=user_id,
            )

    async def test_register_connector_no_duplicate_different_implementation(self, service, connector_repo):
        """Verifica que no se considere duplicado un conector de distinta implementacion."""
        org_id = uuid4()
        user_id = uuid4()
        existing = _make_connector(
            organization_id=org_id,
            connector_implementation=ConnectorImplementation.GITLAB.value,
        )
        connector_repo.list_by_organization.return_value = [existing]
        connector_repo.save.side_effect = lambda c: c

        result = await service.register_connector(
            organization_id=org_id,
            connector_type=ConnectorType.REPO_CODIGO.value,
            connector_implementation=ConnectorImplementation.GITHUB.value,
            name="GitHub Main",
            config={"url": "https://api.github.com"},
            requested_by=user_id,
        )

        assert result.connector_implementation == ConnectorImplementation.GITHUB.value
        connector_repo.save.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: update_connector
# ---------------------------------------------------------------------------

class TestUpdateConnector:
    async def test_update_connector_both_name_and_config(self, service, connector_repo, mock_audit_logger):
        """Verifica la actualizacion de nombre y configuracion simultaneamente."""
        connector = _make_connector()
        connector_repo.get_by_id.return_value = connector
        connector_repo.update.side_effect = lambda c: c
        user_id = uuid4()
        new_config = {"url": "https://gitlab.new.com", "token": "new-token"}

        result = await service.update_connector(
            connector_id=connector.id,
            name="GitLab Updated",
            config=new_config,
            requested_by=user_id,
        )

        assert result.name == "GitLab Updated"

        fernet = Fernet(_VALID_KEY)
        decrypted = eval(fernet.decrypt(result.encrypted_credentials).decode())
        assert decrypted == new_config

        connector_repo.update.assert_called_once_with(connector)
        mock_audit_logger.log.assert_called_once()
        call_arg = mock_audit_logger.log.call_args[0][0]
        assert call_arg.event == AuditEvent.CONNECTOR_UPDATED
        assert call_arg.user_id == user_id
        assert call_arg.details["name"] == "GitLab Updated"

    async def test_update_connector_name_only(self, service, connector_repo, mock_audit_logger):
        """Verifica que solo se actualice el nombre sin modificar las credenciales."""
        connector = _make_connector()
        original_creds = connector.encrypted_credentials
        connector_repo.get_by_id.return_value = connector
        connector_repo.update.side_effect = lambda c: c
        user_id = uuid4()

        result = await service.update_connector(
            connector_id=connector.id,
            name="New Name Only",
            requested_by=user_id,
        )

        assert result.name == "New Name Only"
        assert result.encrypted_credentials == original_creds
        connector_repo.update.assert_called_once_with(connector)
        mock_audit_logger.log.assert_called_once()

    async def test_update_connector_config_only(self, service, connector_repo, mock_audit_logger):
        """Verifica que solo se actualicen las credenciales sin modificar el nombre."""
        connector = _make_connector()
        original_name = connector.name
        connector_repo.get_by_id.return_value = connector
        connector_repo.update.side_effect = lambda c: c
        user_id = uuid4()
        new_config = {"url": "https://new.example.com", "api_key": "abc123"}

        result = await service.update_connector(
            connector_id=connector.id,
            config=new_config,
            requested_by=user_id,
        )

        assert result.name == original_name

        fernet = Fernet(_VALID_KEY)
        decrypted = eval(fernet.decrypt(result.encrypted_credentials).decode())
        assert decrypted == new_config

        connector_repo.update.assert_called_once_with(connector)

    async def test_update_connector_not_found(self, service, connector_repo):
        """Verifica que se lance EntityNotFoundError al actualizar un conector inexistente."""
        connector_repo.get_by_id.return_value = None

        with pytest.raises(EntityNotFoundError, match="Conector no encontrado"):
            await service.update_connector(
                connector_id=uuid4(),
                name="Does not exist",
                requested_by=uuid4(),
            )

    async def test_update_connector_no_requested_by_uses_new_uuid(self, service, connector_repo, mock_audit_logger):
        """Verifica que cuando no se provee requested_by se genere un UUID nuevo para auditoria."""
        connector = _make_connector()
        connector_repo.get_by_id.return_value = connector
        connector_repo.update.side_effect = lambda c: c

        await service.update_connector(
            connector_id=connector.id,
            name="No User Specified",
        )

        mock_audit_logger.log.assert_called_once()
        call_arg = mock_audit_logger.log.call_args[0][0]
        assert call_arg.user_id is not None
        assert call_arg.event == AuditEvent.CONNECTOR_UPDATED


# ---------------------------------------------------------------------------
# Tests: test_connector_connection
# ---------------------------------------------------------------------------

class TestConnectorConnection:
    async def test_connection_success(self, service, connector_repo, connector_registry, mock_audit_logger):
        """Verifica que una conexion exitosa marque el conector como ACTIVO y registre auditoria."""
        config = {"url": "https://gitlab.example.com", "token": "test-token"}
        fernet = Fernet(_VALID_KEY)
        encrypted = fernet.encrypt(str(config).encode())

        connector = _make_connector(
            encrypted_credentials=encrypted,
            status=ConnectorStatus.ERROR,
        )
        connector_repo.get_by_id.return_value = connector
        connector_repo.update.side_effect = lambda c: c

        mock_impl = MagicMock()
        mock_impl.test_connection = MagicMock(return_value=True)
        connector_registry.get_by_implementation.return_value = mock_impl

        user_id = uuid4()
        result = await service.test_connector_connection(connector.id, user_id)

        assert result is True
        assert connector.status == ConnectorStatus.ACTIVO
        connector_repo.update.assert_called_once_with(connector)
        connector_registry.get_by_implementation.assert_called_once_with(connector.connector_implementation)
        mock_impl.test_connection.assert_called_once_with(config)

        mock_audit_logger.log.assert_called_once()
        call_arg = mock_audit_logger.log.call_args[0][0]
        assert call_arg.event == AuditEvent.CONNECTOR_TESTED
        assert call_arg.user_id == user_id
        assert call_arg.details["success"] is True

    async def test_connection_failure_preserves_status(self, service, connector_repo, connector_registry, mock_audit_logger):
        """Verifica que una conexion fallida no modifique el estado y aun registre auditoria."""
        config = {"url": "https://gitlab.example.com", "token": "bad-token"}
        fernet = Fernet(_VALID_KEY)
        encrypted = fernet.encrypt(str(config).encode())

        connector = _make_connector(
            encrypted_credentials=encrypted,
            status=ConnectorStatus.ACTIVO,
        )
        connector_repo.get_by_id.return_value = connector

        mock_impl = MagicMock()
        mock_impl.test_connection = MagicMock(return_value=False)
        connector_registry.get_by_implementation.return_value = mock_impl

        user_id = uuid4()
        result = await service.test_connector_connection(connector.id, user_id)

        assert result is False
        assert connector.status == ConnectorStatus.ACTIVO
        connector_repo.update.assert_not_called()
        mock_audit_logger.log.assert_called_once()
        call_arg = mock_audit_logger.log.call_args[0][0]
        assert call_arg.details["success"] is False

    async def test_connection_exception_marks_error(self, service, connector_repo, connector_registry):
        """Verifica que una excepcion durante la conexion marque el conector como ERROR."""
        config = {"url": "https://gitlab.example.com", "token": "bad-token"}
        fernet = Fernet(_VALID_KEY)
        encrypted = fernet.encrypt(str(config).encode())

        connector = _make_connector(
            encrypted_credentials=encrypted,
            status=ConnectorStatus.ACTIVO,
        )
        connector_repo.get_by_id.return_value = connector
        connector_repo.update.side_effect = lambda c: c

        mock_impl = MagicMock()
        mock_impl.test_connection = MagicMock(side_effect=ConnectionError("timeout"))
        connector_registry.get_by_implementation.return_value = mock_impl

        user_id = uuid4()
        with pytest.raises(ConnectorConnectionFailedError, match="Error al probar conexi"):
            await service.test_connector_connection(connector.id, user_id)

        assert connector.status == ConnectorStatus.ERROR
        connector_repo.update.assert_called_once_with(connector)

    async def test_connection_connector_not_found(self, service, connector_repo):
        """Verifica que se lance EntityNotFoundError si el conector no existe."""
        connector_repo.get_by_id.return_value = None

        with pytest.raises(EntityNotFoundError, match="Conector no encontrado"):
            await service.test_connector_connection(uuid4(), uuid4())

    async def test_connection_impl_not_found(self, service, connector_repo, connector_registry):
        """Verifica que se lance ValidationError cuando la implementacion no esta soportada."""
        connector = _make_connector()
        connector_repo.get_by_id.return_value = connector
        connector_registry.get_by_implementation.return_value = None

        with pytest.raises(ValidationError, match="no soportada"):
            await service.test_connector_connection(connector.id, uuid4())


# ---------------------------------------------------------------------------
# Tests: delete_connector
# ---------------------------------------------------------------------------

class TestDeleteConnector:
    async def test_delete_connector_success(self, service, connector_repo, mock_audit_logger):
        """Verifica la eliminacion exitosa de un conector y el registro de auditoria."""
        connector = _make_connector()
        connector_repo.get_by_id.return_value = connector
        user_id = uuid4()

        await service.delete_connector(connector.id, user_id)

        connector_repo.delete.assert_called_once_with(connector.id)
        mock_audit_logger.log.assert_called_once()
        call_arg = mock_audit_logger.log.call_args[0][0]
        assert call_arg.event == AuditEvent.CONNECTOR_DELETED
        assert call_arg.user_id == user_id
        assert call_arg.organization_id == connector.organization_id
        assert call_arg.resource_id == connector.id
        assert call_arg.details["name"] == connector.name

    async def test_delete_connector_not_found(self, service, connector_repo):
        """Verifica que se lance EntityNotFoundError al eliminar un conector inexistente."""
        connector_repo.get_by_id.return_value = None

        with pytest.raises(EntityNotFoundError, match="Conector no encontrado"):
            await service.delete_connector(uuid4(), uuid4())


# ---------------------------------------------------------------------------
# Tests: toggle_connector_status
# ---------------------------------------------------------------------------

class TestToggleConnectorStatus:
    async def test_toggle_to_inactive(self, service, connector_repo):
        """Verifica el cambio de estado de un conector a INACTIVO."""
        connector = _make_connector(status=ConnectorStatus.ACTIVO)
        connector_repo.get_by_id.return_value = connector
        connector_repo.update.side_effect = lambda c: c

        result = await service.toggle_connector_status(
            connector.id, ConnectorStatus.INACTIVO, uuid4()
        )

        assert result.status == ConnectorStatus.INACTIVO
        connector_repo.update.assert_called_once_with(connector)

    async def test_toggle_to_active(self, service, connector_repo):
        """Verifica el cambio de estado de un conector a ACTIVO."""
        connector = _make_connector(status=ConnectorStatus.INACTIVO)
        connector_repo.get_by_id.return_value = connector
        connector_repo.update.side_effect = lambda c: c

        result = await service.toggle_connector_status(
            connector.id, ConnectorStatus.ACTIVO, uuid4()
        )

        assert result.status == ConnectorStatus.ACTIVO
        connector_repo.update.assert_called_once_with(connector)

    async def test_toggle_to_error(self, service, connector_repo):
        """Verifica el cambio de estado de un conector a ERROR."""
        connector = _make_connector(status=ConnectorStatus.ACTIVO)
        connector_repo.get_by_id.return_value = connector
        connector_repo.update.side_effect = lambda c: c

        result = await service.toggle_connector_status(
            connector.id, ConnectorStatus.ERROR, uuid4()
        )

        assert result.status == ConnectorStatus.ERROR
        connector_repo.update.assert_called_once_with(connector)

    async def test_toggle_connector_not_found(self, service, connector_repo):
        """Verifica que se lance EntityNotFoundError al cambiar el estado de un conector inexistente."""
        connector_repo.get_by_id.return_value = None

        with pytest.raises(EntityNotFoundError, match="Conector no encontrado"):
            await service.toggle_connector_status(uuid4(), ConnectorStatus.INACTIVO, uuid4())


# ---------------------------------------------------------------------------
# Tests: _get_connector_impl (helper)
# ---------------------------------------------------------------------------

class TestGetConnectorImpl:
    def test_get_connector_impl_found(self, service, connector_registry):
        """Verifica que el helper retorne la implementacion cuando existe en el registro."""
        mock_impl = MagicMock()
        connector_registry.get_by_implementation.return_value = mock_impl

        result = service._get_connector_impl(ConnectorImplementation.GITLAB.value)

        assert result == mock_impl
        connector_registry.get_by_implementation.assert_called_once_with(
            ConnectorImplementation.GITLAB.value
        )

    def test_get_connector_impl_not_found(self, service, connector_registry):
        """Verifica que el helper retorne None cuando la implementacion no esta registrada."""
        connector_registry.get_by_implementation.return_value = None

        result = service._get_connector_impl("UNKNOWN")

        assert result is None
        connector_registry.get_by_implementation.assert_called_once_with("UNKNOWN")

"""
Test suite for ``ConfigureConnectorUseCase``.

External connectors (GitHub, Jira, SonarQube, etc.) are the adapters that feed
data to the verification engine. ``ConfigureConnectorUseCase`` registers a new
connector for an organisation: resolves the concrete client from the connector
registry, tests the connection, and persists the instance with encrypted
credentials.

The use case implements a deliberate fault-tolerance policy:
    - If ``test_connection`` returns ``False``: ``ConnectorConnectionFailedError``
      is raised and nothing is persisted (credentials are invalid).
    - If ``test_connection`` raises ``RuntimeError`` or ``ValueError``: the
      instance is persisted in ``INACTIVO`` state, allowing the administrator
      to correct the configuration without re-entering all data.

Testing strategy:
    Unit tests. The repository, connector registry, connector client, and
    encryptor are all replaced by test doubles to completely isolate the use-case
    logic.

Key invariants verified:
    - Successful connection → instance saved as ``ACTIVO``.
    - ``test_connection`` returns ``False`` → ``ConnectorConnectionFailedError``, not saved.
    - ``RuntimeError`` / ``ValueError`` from the client → instance saved as ``INACTIVO``.
    - Credentials are always encrypted before being persisted.
    - An unregistered connector type raises ``KeyError`` before any I/O.
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from application.use_cases.configure_connector import ConfigureConnectorUseCase, ConfigureConnectorCommand
from domain.entities.enums import ConnectorStatus
from domain.exceptions import ConnectorConnectionFailedError
from infrastructure.adapters.connector_registry import ConnectorRegistry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def org_id():
    """Reusable test organisation UUID shared across multiple tests."""
    return uuid.uuid4()


@pytest.fixture
def connector_client():
    """Connector client stub with a successful connection by default."""
    client = AsyncMock()
    client.test_connection.return_value = True
    return client


@pytest.fixture
def registry(connector_client):
    """
    Connector registry with the «github» type registered.

    Uses a real ``ConnectorRegistry`` (not mocked) to verify that client
    resolution by type works correctly.
    """
    reg = ConnectorRegistry()
    reg.register("github", connector_client)
    return reg


@pytest.fixture
def connector_repo():
    """Connector repository stub that returns the received instance."""
    repo = AsyncMock()

    def _save(instance):
        return instance

    repo.save.side_effect = _save
    return repo


@pytest.fixture
def encryptor():
    """Encryptor stub that returns predictable encrypted bytes."""
    enc = MagicMock()
    enc.encrypt.return_value = b"encrypted_creds"
    return enc


@pytest.fixture
def command(org_id):
    """Test command with type «github» and sample credentials."""
    return ConfigureConnectorCommand(
        organization_id=org_id,
        connector_type="github",
        name="GitHub CI",
        config_data={"token": "ghp_secret"},
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestConfigureConnectorUseCase:
    """
    Unit tests for ``ConfigureConnectorUseCase``.

    Covers the connection-error handling policy, mandatory credential
    encryption, and resolution of unregistered connector types.
    """

    async def test_successful_connection_saved_as_activo(
        self, connector_repo, registry, encryptor, command
    ):
        """
        A successful connection persists the instance with state ``ACTIVO``.

        Given:  A client whose ``test_connection`` returns ``True``.
        When:   ``ConfigureConnectorUseCase`` is executed.
        Then:   The returned instance has state ``ACTIVO`` and the repository
                persists the instance exactly once.
        """
        use_case = ConfigureConnectorUseCase(connector_repo, registry, encryptor)
        result = await use_case.execute(command)

        assert result.status == ConnectorStatus.ACTIVO
        connector_repo.save.assert_called_once()

    async def test_connection_returns_false_raises_error(
        self, connector_repo, registry, encryptor, command, connector_client
    ):
        """
        ``test_connection`` returning ``False`` raises ``ConnectorConnectionFailedError``.

        Given:  A client whose ``test_connection`` explicitly returns ``False``.
        When:   The use case is executed.
        Then:   ``ConnectorConnectionFailedError`` is raised, indicating that the
                provided credentials are invalid and the connection cannot be made.
        """
        connector_client.test_connection.return_value = False
        use_case = ConfigureConnectorUseCase(connector_repo, registry, encryptor)

        with pytest.raises(ConnectorConnectionFailedError):
            await use_case.execute(command)

    async def test_connection_false_does_not_save(
        self, connector_repo, registry, encryptor, command, connector_client
    ):
        """
        When the connection fails with ``False``, no instance is persisted.

        Given:  A client whose ``test_connection`` returns ``False``.
        When:   The use case is executed and the expected exception is caught.
        Then:   ``connector_repo.save`` is never called, avoiding storage of
                connectors with known-invalid credentials.
        """
        connector_client.test_connection.return_value = False
        use_case = ConfigureConnectorUseCase(connector_repo, registry, encryptor)

        with pytest.raises(ConnectorConnectionFailedError):
            await use_case.execute(command)

        connector_repo.save.assert_not_called()

    async def test_runtime_error_saved_as_inactivo(
        self, connector_repo, registry, encryptor, command, connector_client
    ):
        """
        A ``RuntimeError`` during the connection test persists the instance as ``INACTIVO``.

        Given:  A client whose ``test_connection`` raises ``RuntimeError("connection timeout")``.
        When:   The use case is executed.
        Then:   The instance is persisted with state ``INACTIVO``, allowing the
                administrator to edit it without recreating the entire connector.
                This distinguishes transient infrastructure errors from invalid
                credentials (which are not persisted).
        """
        connector_client.test_connection.side_effect = RuntimeError("connection timeout")
        use_case = ConfigureConnectorUseCase(connector_repo, registry, encryptor)

        result = await use_case.execute(command)

        assert result.status == ConnectorStatus.INACTIVO
        connector_repo.save.assert_called_once()

    async def test_value_error_saved_as_inactivo(
        self, connector_repo, registry, encryptor, command, connector_client
    ):
        """
        A ``ValueError`` during the connection test persists the instance as ``INACTIVO``.

        Given:  A client whose ``test_connection`` raises ``ValueError("invalid config")``.
        When:   The use case is executed.
        Then:   The instance is persisted with state ``INACTIVO``, applying the
                same fault-tolerance semantics as the ``RuntimeError`` case.
        """
        connector_client.test_connection.side_effect = ValueError("invalid config")
        use_case = ConfigureConnectorUseCase(connector_repo, registry, encryptor)

        result = await use_case.execute(command)

        assert result.status == ConnectorStatus.INACTIVO

    async def test_credentials_are_encrypted_and_stored(
        self, connector_repo, registry, encryptor, command
    ):
        """
        Credentials are encrypted via ``ICredentialEncryptor`` before being persisted.

        Given:  An encryptor that returns ``b"encrypted_creds"`` for any input.
        When:   The use case executes successfully.
        Then:   ``encryptor.encrypt`` is called exactly once and the resulting
                instance stores the encrypted bytes, never the plain-text credentials.
        """
        use_case = ConfigureConnectorUseCase(connector_repo, registry, encryptor)
        result = await use_case.execute(command)

        encryptor.encrypt.assert_called_once()
        assert result.encrypted_credentials == b"encrypted_creds"

    async def test_unregistered_connector_type_raises_key_error(
        self, connector_repo, encryptor, org_id
    ):
        """
        An unregistered connector type raises ``KeyError`` before any I/O.

        Given:  An empty ``ConnectorRegistry`` (no connectors registered).
        When:   A connector of type ``"nonexistent"`` is configured.
        Then:   ``KeyError`` is raised immediately, without attempting connections
                or database writes, enabling early detection of registry
                configuration errors.
        """
        reg = ConnectorRegistry()
        cmd = ConfigureConnectorCommand(
            organization_id=org_id,
            connector_type="nonexistent",
            name="X",
            config_data={},
        )
        use_case = ConfigureConnectorUseCase(connector_repo, reg, encryptor)

        with pytest.raises(KeyError):
            await use_case.execute(cmd)

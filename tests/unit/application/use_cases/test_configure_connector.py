"""
Test suite para ``ConfigureConnectorUseCase``.

Los conectores externos (GitHub, Jira, SonarQube, etc.) son los adaptadores que
alimentan de datos al motor de verificación. ``ConfigureConnectorUseCase`` registra
un nuevo conector para una organización: resuelve el cliente concreto desde el
registro de conectores, prueba la conexión y persiste la instancia con las
credenciales cifradas.

El caso de uso implementa una política de tolerancia a fallos deliberada:
    - Si ``test_connection`` retorna ``False``: se lanza ``ConnectorConnectionFailedError``
      y **no** se persiste (las credenciales son inválidas, no hay nada que guardar).
    - Si ``test_connection`` lanza ``RuntimeError`` o ``ValueError``: la instancia se
      persiste en estado ``INACTIVO``, permitiendo que el administrador corrija la
      configuración sin reintroducir todos los datos.

Estrategia de prueba:
    Pruebas unitarias. El repositorio, el registro de conectores, el cliente del
    conector y el encriptador se sustituyen por dobles de prueba para aislar
    completamente la lógica del caso de uso.

Invariantes clave verificadas:
    - Conexión exitosa → instancia guardada con ``ACTIVO``.
    - ``test_connection`` retorna ``False`` → ``ConnectorConnectionFailedError``, sin guardar.
    - ``RuntimeError`` / ``ValueError`` en el cliente → instancia guardada con ``INACTIVO``.
    - Las credenciales siempre se cifran antes de persistir.
    - Un tipo de conector no registrado lanza ``KeyError`` antes de cualquier I/O.
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
    """UUID de organización de prueba reutilizable entre varios tests."""
    return uuid.uuid4()


@pytest.fixture
def connector_client():
    """Cliente de conector stub con conexión exitosa por defecto."""
    client = AsyncMock()
    client.test_connection.return_value = True
    return client


@pytest.fixture
def registry(connector_client):
    """
    Registro de conectores con el tipo «github» registrado.

    Proporciona un ``ConnectorRegistry`` real (no mockeado) para verificar
    que la resolución del cliente por tipo funciona correctamente.
    """
    reg = ConnectorRegistry()
    reg.register("github", connector_client)
    return reg


@pytest.fixture
def connector_repo():
    """Repositorio de conectores stub que retorna la instancia recibida."""
    repo = AsyncMock()

    def _save(instance):
        return instance

    repo.save.side_effect = _save
    return repo


@pytest.fixture
def encryptor():
    """Encriptador stub que retorna bytes cifrados predecibles."""
    enc = MagicMock()
    enc.encrypt.return_value = b"encrypted_creds"
    return enc


@pytest.fixture
def command(org_id):
    """Comando de prueba con tipo «github» y credenciales de ejemplo."""
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
    Pruebas unitarias para ``ConfigureConnectorUseCase``.

    Cubre la política de manejo de errores de conexión, el cifrado obligatorio
    de credenciales y la resolución de tipos de conector no registrados.
    """

    async def test_successful_connection_saved_as_activo(
        self, connector_repo, registry, encryptor, command
    ):
        """
        Una conexión exitosa persiste la instancia con estado ``ACTIVO``.

        Given:  Un cliente cuyo ``test_connection`` retorna ``True``.
        When:   Se ejecuta ``ConfigureConnectorUseCase``.
        Then:   La instancia retornada tiene estado ``ACTIVO`` y el repositorio
                persiste la instancia exactamente una vez.
        """
        use_case = ConfigureConnectorUseCase(connector_repo, registry, encryptor)
        result = await use_case.execute(command)

        assert result.status == ConnectorStatus.ACTIVO
        connector_repo.save.assert_called_once()

    async def test_connection_returns_false_raises_error(
        self, connector_repo, registry, encryptor, command, connector_client
    ):
        """
        ``test_connection`` retornando ``False`` lanza ``ConnectorConnectionFailedError``.

        Given:  Un cliente cuyo ``test_connection`` retorna ``False`` explícitamente.
        When:   Se ejecuta el caso de uso.
        Then:   Se lanza ``ConnectorConnectionFailedError``, indicando que las credenciales
                provistas son inválidas y la conexión no puede establecerse.
        """
        connector_client.test_connection.return_value = False
        use_case = ConfigureConnectorUseCase(connector_repo, registry, encryptor)

        with pytest.raises(ConnectorConnectionFailedError):
            await use_case.execute(command)

    async def test_connection_false_does_not_save(
        self, connector_repo, registry, encryptor, command, connector_client
    ):
        """
        Cuando la conexión falla con ``False``, no se persiste ninguna instancia.

        Given:  Un cliente cuyo ``test_connection`` retorna ``False``.
        When:   Se ejecuta el caso de uso y se captura la excepción esperada.
        Then:   ``connector_repo.save`` no se llama en ningún momento, evitando
                almacenar conectores con credenciales que se saben incorrectas.
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
        Un ``RuntimeError`` en la prueba de conexión persiste la instancia como ``INACTIVO``.

        Given:  Un cliente cuyo ``test_connection`` lanza ``RuntimeError("connection timeout")``.
        When:   Se ejecuta el caso de uso.
        Then:   La instancia se persiste con estado ``INACTIVO``, permitiendo que el
                administrador la edite sin necesidad de recrear el conector completo.
                Este comportamiento distingue los errores de infraestructura transitorios
                de las credenciales inválidas (que no se persisten).
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
        Un ``ValueError`` en la prueba de conexión persiste la instancia como ``INACTIVO``.

        Given:  Un cliente cuyo ``test_connection`` lanza ``ValueError("invalid config")``.
        When:   Se ejecuta el caso de uso.
        Then:   La instancia se persiste con estado ``INACTIVO``, con la misma
                semántica de tolerancia a fallos aplicada al caso ``RuntimeError``.
        """
        connector_client.test_connection.side_effect = ValueError("invalid config")
        use_case = ConfigureConnectorUseCase(connector_repo, registry, encryptor)

        result = await use_case.execute(command)

        assert result.status == ConnectorStatus.INACTIVO

    async def test_credentials_are_encrypted_and_stored(
        self, connector_repo, registry, encryptor, command
    ):
        """
        Las credenciales se cifran mediante ``ICredentialEncryptor`` antes de persistir.

        Given:  Un encriptador que retorna ``b"encrypted_creds"`` para cualquier entrada.
        When:   Se ejecuta el caso de uso con éxito.
        Then:   ``encryptor.encrypt`` se llama exactamente una vez y la instancia
                resultante almacena los bytes cifrados, nunca las credenciales en claro.
        """
        use_case = ConfigureConnectorUseCase(connector_repo, registry, encryptor)
        result = await use_case.execute(command)

        encryptor.encrypt.assert_called_once()
        assert result.encrypted_credentials == b"encrypted_creds"

    async def test_unregistered_connector_type_raises_key_error(
        self, connector_repo, encryptor, org_id
    ):
        """
        Un tipo de conector no registrado lanza ``KeyError`` antes de cualquier I/O.

        Given:  Un ``ConnectorRegistry`` vacío (sin conectores registrados).
        When:   Se intenta configurar un conector de tipo ``"nonexistent"``.
        Then:   Se lanza ``KeyError``, fallando rápido sin intentar conexiones ni
                escrituras en base de datos, facilitando la detección temprana de
                errores de configuración en la capa de registro.
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

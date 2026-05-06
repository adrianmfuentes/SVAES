import uuid
import json
from dataclasses import dataclass
from typing import Dict, Any

from domain.entities.connector_instance import ConnectorInstance
from domain.entities.enums import ConnectorStatus
from domain.ports.i_connector_repository import IConnectorRepository
from domain.ports.i_credential_encryptor import ICredentialEncryptor
from domain.exceptions import ConnectorConnectionFailedError
from infrastructure.adapters.connector_registry import ConnectorRegistry
from infrastructure.logging.logger import get_logger

_log = get_logger(__name__)


@dataclass
class ConfigureConnectorCommand:
    organization_id: uuid.UUID
    connector_type: str
    name: str
    config_data: Dict[str, Any]


class ConfigureConnectorUseCase:
    """Registers and validates an external connector for an organization.

    Resolves the concrete IConnector implementation from the registry, tests the connection,
    then persists the instance. On connection failure the instance is saved as INACTIVO
    rather than rejected — this lets admins correct credentials without re-entering all config.
    """

    def __init__(
        self,
        connector_repo: IConnectorRepository,
        connector_registry: ConnectorRegistry,
        credential_encryptor: ICredentialEncryptor,
    ) -> None:
        self.connector_repo = connector_repo
        self.connector_registry = connector_registry
        self.credential_encryptor = credential_encryptor

    async def execute(self, command: ConfigureConnectorCommand) -> ConnectorInstance:
        connector_client = self.connector_registry.get_connector(command.connector_type)

        try:
            is_valid = await connector_client.test_connection(command.config_data)
            status = ConnectorStatus.ACTIVO if is_valid else ConnectorStatus.INACTIVO
            if not is_valid:
                raise ConnectorConnectionFailedError("Las credenciales son inválidas.")
        except ConnectorConnectionFailedError:
            raise
        except (ValueError, RuntimeError) as exc:
            _log.warning(
                "Connection test failed for type=%s org=%s: %s",
                command.connector_type, command.organization_id, exc,
            )
            status = ConnectorStatus.INACTIVO

        encrypted = self.credential_encryptor.encrypt(json.dumps(command.config_data))

        instance = ConnectorInstance(
            id=uuid.uuid4(),
            organization_id=command.organization_id,
            connector_type=command.connector_type,
            encrypted_credentials=encrypted,
            status=status,
        )

        saved = await self.connector_repo.save(instance)
        _log.info(
            "Connector %s registered for org=%s status=%s",
            saved.id, command.organization_id, status.value,
        )
        return saved

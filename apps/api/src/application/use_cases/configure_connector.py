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
    """Command object for configuring a connector instance."""
    organization_id: uuid.UUID
    connector_type: str
    name: str
    config_data: Dict[str, Any]


class ConfigureConnectorUseCase:
    """Use case for registering and validating an external connector for an organization.

    Attributes:
        connector_repo (IConnectorRepository): Repository for storing connector instances.
        connector_registry (ConnectorRegistry): Registry for obtaining connector clients.
        credential_encryptor (ICredentialEncryptor): Service for encrypting connector credentials.

    Raises:
        ConnectorConnectionFailedError: If the connector fails to connect with the provided configuration.

    Logs:
        - Warning: Failed connection test for the connector with organization and error details.
        - Info: Successful registration of the connector with organization and status.
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
                raise ConnectorConnectionFailedError("Invalid credentials.")
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

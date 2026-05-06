import uuid
import json
from dataclasses import dataclass
from typing import Dict, Any
from domain.entities.connector_instance import ConnectorInstance
from domain.entities.enums import ConnectorStatus
from domain.ports.i_connector_repository import IConnectorRepository
from domain.exceptions import ConnectorConnectionFailedError
from infrastructure.adapters.connector_registry import ConnectorRegistry

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
    ):
        self.connector_repo = connector_repo
        self.connector_registry = connector_registry

    async def execute(self, command: ConfigureConnectorCommand) -> ConnectorInstance:
        connector_client = self.connector_registry.get_connector(command.connector_type)

        try:
            is_valid = await connector_client.test_connection(command.config_data)
            if not is_valid:
                raise ConnectorConnectionFailedError("Las credenciales son inválidas.")
            status = ConnectorStatus.ACTIVO
        except Exception:
            status = ConnectorStatus.INACTIVO

        config_bytes = json.dumps(command.config_data).encode("utf-8")

        instance = ConnectorInstance(
            id=uuid.uuid4(),
            organization_id=command.organization_id,
            connector_type=command.connector_type,
            encrypted_credentials=config_bytes,
            status=status,
        )

        return await self.connector_repo.save(instance)

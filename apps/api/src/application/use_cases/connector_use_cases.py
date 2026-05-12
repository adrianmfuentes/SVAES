import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from domain.entities.connector_instance import ConnectorInstance, ConnectorStatus
from domain.exceptions import EntityNotFoundError
from domain.ports.i_connector_repository import IConnectorRepository
from domain.ports.i_credential_encryptor import ICredentialEncryptor
from infrastructure.adapters.connector_registry import ConnectorRegistry
from infrastructure.logging.logger import get_logger

_log = get_logger(__name__)


@dataclass
class GetConnectorCommand:
    organization_id: uuid.UUID
    connector_id: uuid.UUID


@dataclass
class UpdateConnectorCommand:
    organization_id: uuid.UUID
    connector_id: uuid.UUID
    name: Optional[str] = None
    status: Optional[ConnectorStatus] = None


@dataclass
class DeleteConnectorCommand:
    organization_id: uuid.UUID
    connector_id: uuid.UUID


@dataclass
class TestConnectorCommand:
    organization_id: uuid.UUID
    connector_id: uuid.UUID


def _check_ownership(connector: Optional[ConnectorInstance], organization_id: uuid.UUID) -> ConnectorInstance:
    """Raises EntityNotFoundError if connector is missing or belongs to a different org."""
    if not connector or connector.organization_id != organization_id:
        raise EntityNotFoundError(f"Connector not found")
    return connector


class GetConnectorUseCase:
    def __init__(self, connector_repo: IConnectorRepository) -> None:
        self.connector_repo = connector_repo

    async def execute(self, command: GetConnectorCommand) -> ConnectorInstance:
        connector = await self.connector_repo.get_by_id(command.connector_id)
        return _check_ownership(connector, command.organization_id)


class ListConnectorsUseCase:
    def __init__(self, connector_repo: IConnectorRepository) -> None:
        self.connector_repo = connector_repo

    async def execute(self, organization_id: uuid.UUID, include_inactive: bool = False, skip: int = 0, limit: int = 50) -> List[ConnectorInstance]:
        return await self.connector_repo.list_by_organization(
            organization_id, active_only=not include_inactive, skip=skip, limit=limit
        )


class UpdateConnectorUseCase:
    def __init__(self, connector_repo: IConnectorRepository) -> None:
        self.connector_repo = connector_repo

    async def execute(self, command: UpdateConnectorCommand) -> ConnectorInstance:
        connector = await self.connector_repo.get_by_id(command.connector_id)
        _check_ownership(connector, command.organization_id)
        if command.name is not None:
            connector.name = command.name
        if command.status is not None:
            connector.status = command.status
        return await self.connector_repo.update(connector)


class DeleteConnectorUseCase:
    def __init__(self, connector_repo: IConnectorRepository) -> None:
        self.connector_repo = connector_repo

    async def execute(self, command: DeleteConnectorCommand) -> None:
        connector = await self.connector_repo.get_by_id(command.connector_id)
        _check_ownership(connector, command.organization_id)
        await self.connector_repo.delete(command.connector_id)


class TestConnectorUseCase:
    def __init__(
        self,
        connector_repo: IConnectorRepository,
        connector_registry: ConnectorRegistry,
        credential_encryptor: ICredentialEncryptor,
    ) -> None:
        self.connector_repo = connector_repo
        self.connector_registry = connector_registry
        self.credential_encryptor = credential_encryptor

    async def execute(self, command: TestConnectorCommand) -> ConnectorInstance:
        connector = await self.connector_repo.get_by_id(command.connector_id)
        _check_ownership(connector, command.organization_id)

        try:
            config_data = json.loads(self.credential_encryptor.decrypt(connector.encrypted_credentials))
            connector_client = self.connector_registry.get_connector(connector.connector_type)
            is_valid = await connector_client.test_connection(config_data)
            connector.status = ConnectorStatus.ACTIVO if is_valid else ConnectorStatus.INACTIVO
        except Exception as exc:
            _log.warning("Connection test failed for connector %s: %s", connector.id, exc)
            connector.status = ConnectorStatus.INACTIVO

        connector.last_tested_at = datetime.now(timezone.utc)
        return await self.connector_repo.update(connector)

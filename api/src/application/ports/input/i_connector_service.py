from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

# Dominio y entidades
from domain.entities.connector_instance import ConnectorInstance
from domain.enums import ConnectorStatus

class IConnectorService(ABC):
    @abstractmethod
    async def register_connector(
        self,
        organization_id: UUID,
        connector_type: str,
        connector_implementation: str,
        name: str,
        config: dict,
    ) -> ConnectorInstance:
        pass

    @abstractmethod
    async def update_connector(
        self,
        connector_id: UUID,
        name: Optional[str] = None,
        config: Optional[dict] = None,
    ) -> ConnectorInstance:
        pass

    @abstractmethod
    async def test_connector_connection(self, connector_id: UUID) -> bool:
        pass

    @abstractmethod
    async def list_connectors(
        self,
        organization_id: UUID,
        active_only: bool = True,
    ) -> List[ConnectorInstance]:
        pass

    @abstractmethod
    async def get_connector(self, connector_id: UUID) -> Optional[ConnectorInstance]:
        pass

    @abstractmethod
    async def delete_connector(self, connector_id: UUID) -> None:
        pass

    @abstractmethod
    async def toggle_connector_status(
        self, connector_id: UUID, status: ConnectorStatus
    ) -> ConnectorInstance:
        pass
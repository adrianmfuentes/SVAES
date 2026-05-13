from abc import ABC, abstractmethod
from typing import Optional, List
import uuid
from domain.entities.connector_instance import ConnectorInstance

class IConnectorRepository(ABC):
    @abstractmethod
    async def save(self, connector: ConnectorInstance) -> ConnectorInstance:
        pass

    @abstractmethod
    async def get_by_id(self, instance_id: uuid.UUID) -> Optional[ConnectorInstance]:
        pass

    @abstractmethod
    async def list_by_organization(
        self, organization_id: uuid.UUID, active_only: bool = True, skip: int = 0, limit: int = 50
    ) -> List[ConnectorInstance]:
        pass

    @abstractmethod
    async def list_active(self, organization_id: uuid.UUID) -> List[ConnectorInstance]:
        pass

    @abstractmethod
    async def update(self, connector: ConnectorInstance) -> ConnectorInstance:
        pass

    @abstractmethod
    async def delete(self, connector_id: uuid.UUID) -> None:
        pass
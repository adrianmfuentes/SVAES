from abc import ABC, abstractmethod
from typing import Optional, List
import uuid
from domain.entities.connector_instance import ConnectorInstance

class IConnectorRepository(ABC):
    """Outbound port for managing connector instances. This repository interface abstracts the persistence mechanism for 
    connector instances, allowing the application layer to interact with connector data without being coupled to a specific database or storage solution.

    Methods:
        save(connector: ConnectorInstance) -> ConnectorInstance: Saves a connector instance to the repository and returns the saved instance.
        get_by_id(instance_id: uuid.UUID) -> Optional[ConnectorInstance]: Retrieves a connector instance by its unique identifier, returning None if not found.
        list_by_organization(organization_id: uuid.UUID, active_only: bool = True) -> List[ConnectorInstance]: Retrieves all connector instances associated with a specific organization, optionally filtering only active instances.
    """
    @abstractmethod
    async def save(self, connector: ConnectorInstance) -> ConnectorInstance:
        pass

    @abstractmethod
    async def get_by_id(self, instance_id: uuid.UUID) -> Optional[ConnectorInstance]:
        pass

    @abstractmethod
    async def list_by_organization(self, organization_id: uuid.UUID, active_only: bool = True, skip: int = 0, limit: int = 50) -> List[ConnectorInstance]:
        pass

    @abstractmethod
    async def update(self, connector: ConnectorInstance) -> ConnectorInstance:
        pass

    @abstractmethod
    async def delete(self, connector_id: uuid.UUID) -> None:
        pass
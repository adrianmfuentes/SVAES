from abc import ABC, abstractmethod
from typing import Optional, List
import uuid
from domain.entities.organization import Organization

class IOrganizationRepository(ABC):
    """Outbound port for managing Organization entities in the data store. This interface defines the contract for persisting, retrieving, and updating
    organization data, abstracting away the underlying database or storage mechanism. Implementations of this interface can use SQL databases, 
    NoSQL databases, or any other form of storage, while the application layer interacts with it through these defined methods.

    Methods:
        create(organization: Organization) -> Organization: Persists a new organization and returns the created
        get_by_id(organization_id: uuid.UUID) -> Optional[Organization]: Retrieves an organization by its unique identifier, or returns None if not found.
        get_by_slug(slug: str) -> Optional[Organization]: Retrieves an organization by its
        slug (which is UNIQUE according to the schema), or returns None if not found.
        list_all(active_only: bool = True) -> List[Organization]: Returns a list of organizations, with an option to filter for only active ones.
        update(organization: Organization) -> Organization: Updates the state of an existing organization and returns the updated entity.
    """
    @abstractmethod
    async def create(self, organization: Organization) -> Organization:
        pass

    @abstractmethod
    async def get_by_id(self, organization_id: uuid.UUID) -> Optional[Organization]:
        pass

    @abstractmethod
    async def get_by_slug(self, slug: str) -> Optional[Organization]:
        pass

    @abstractmethod
    async def list_all(self, active_only: bool = True) -> List[Organization]:
         pass

    @abstractmethod
    async def update(self, organization: Organization) -> Organization:
        pass
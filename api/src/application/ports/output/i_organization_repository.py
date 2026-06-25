from abc import ABC, abstractmethod
from typing import Optional, List
import uuid
from domain.entities.organization import Organization


class IOrganizationRepository(ABC):
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
    async def list_all(
        self,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Organization]:
        pass

    @abstractmethod
    async def update(self, organization: Organization) -> Organization:
        pass

    @abstractmethod
    async def delete(self, organization_id: uuid.UUID) -> None:
        pass

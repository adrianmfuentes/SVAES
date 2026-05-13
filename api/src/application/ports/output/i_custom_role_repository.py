from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID
from domain.entities.custom_role import CustomRole


class ICustomRoleRepository(ABC):
    @abstractmethod
    async def create(self, role: CustomRole) -> CustomRole:
        pass

    @abstractmethod
    async def get_by_id(self, role_id: UUID) -> Optional[CustomRole]:
        pass

    @abstractmethod
    async def list_by_organization(self, organization_id: UUID) -> List[CustomRole]:
        pass

    @abstractmethod
    async def update(self, role: CustomRole) -> CustomRole:
        pass

    @abstractmethod
    async def delete(self, role_id: UUID) -> None:
        pass
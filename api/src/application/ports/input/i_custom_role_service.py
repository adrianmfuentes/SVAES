from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID
from domain.entities.custom_role import CustomRole
from domain.enums import Permission


class ICustomRoleService(ABC):
    @abstractmethod
    async def create_role(self, organization_id: UUID, name: str, permissions: List[Permission], requested_by: UUID) -> CustomRole:
        pass

    @abstractmethod
    async def get_role(self, role_id: UUID) -> Optional[CustomRole]:
        pass

    @abstractmethod
    async def list_roles(self, organization_id: UUID) -> List[CustomRole]:
        pass

    @abstractmethod
    async def update_role(
        self,
        role_id: UUID,
        name: Optional[str] = None,
        permissions: Optional[List[Permission]] = None,
        is_active: Optional[bool] = None,
        requested_by: Optional[UUID] = None,
    ) -> CustomRole:
        pass

    @abstractmethod
    async def delete_role(self, role_id: UUID, requested_by: UUID) -> None:
        pass
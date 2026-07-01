from abc import ABC, abstractmethod
from typing import Optional, List
import uuid
from domain.entities.user import UserMembership
from domain.enums import UserRole


class IUserMembershipRepository(ABC):
    @abstractmethod
    async def create(self, membership: UserMembership) -> UserMembership:
        pass

    @abstractmethod
    async def get(self, user_id: uuid.UUID, organization_id: uuid.UUID) -> Optional[UserMembership]:
        pass

    @abstractmethod
    async def list_by_user(self, user_id: uuid.UUID) -> List[UserMembership]:
        pass

    @abstractmethod
    async def list_by_organization(self, organization_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[UserMembership]:
        pass

    @abstractmethod
    async def update_role(self, user_id: uuid.UUID, organization_id: uuid.UUID, role: UserRole) -> UserMembership:
        pass

    @abstractmethod
    async def delete(self, user_id: uuid.UUID, organization_id: uuid.UUID) -> None:
        pass

    @abstractmethod
    async def delete_all_for_user(self, user_id: uuid.UUID) -> None:
        pass

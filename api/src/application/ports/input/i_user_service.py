from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID
from domain.entities.user import User
from domain.enums import UserRole


class IUserService(ABC):
    @abstractmethod
    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        pass

    @abstractmethod
    async def update_profile(self, user_id: UUID, display_name: Optional[str] = None) -> User:
        pass

    @abstractmethod
    async def change_password(self, user_id: UUID, current_password: str, new_password: str) -> bool:
        pass

    @abstractmethod
    async def list_organization_users(self, organization_id: UUID, skip: int = 0, limit: int = 50) -> List[User]:
        pass

    @abstractmethod
    async def invite_user(self, organization_id: UUID, email: str, role: UserRole, requested_by: UUID) -> User:
        pass

    @abstractmethod
    async def update_user_role(self, user_id: UUID, organization_id: UUID, new_role: UserRole, requested_by: UUID) -> User:
        pass

    @abstractmethod
    async def remove_user_from_organization(self, user_id: UUID, organization_id: UUID, requested_by: UUID) -> None:
        pass

    @abstractmethod
    async def create_user(self, email: str, display_name: str, password: str, role: UserRole) -> User:
        pass

    @abstractmethod
    async def activate_user(self, user_id: UUID) -> User:
        pass

    @abstractmethod
    async def deactivate_user(self, user_id: UUID, requested_by: UUID) -> User:
        pass

    @abstractmethod
    async def update_global_role(self, user_id: UUID, new_role: UserRole, requested_by: UUID) -> User:
        pass

    @abstractmethod
    async def list_all_users(self, skip: int = 0, limit: int = 50, is_active: Optional[bool] = None, role: Optional[UserRole] = None) -> List[User]:
        pass
from abc import ABC, abstractmethod
from typing import Optional, List
import uuid
from domain.entities.user import User

class IUserRepository(ABC):
    @abstractmethod
    async def create(self, user: User) -> User:
        pass

    @abstractmethod
    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        pass

    @abstractmethod
    async def list_all(self, organization_id: Optional[uuid.UUID] = None, active_only: bool = True, skip: int = 0, limit: int = 100) -> List[User]:
        pass

    @abstractmethod
    async def update(self, user: User) -> User:
        pass

    @abstractmethod
    async def delete(self, user_id: uuid.UUID) -> None:
        pass
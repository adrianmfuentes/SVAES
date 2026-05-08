from abc import ABC, abstractmethod
from typing import Optional, List
import uuid
from domain.entities.user import User

class IUserRepository(ABC):
    """Outbound port for managing User entities in the data store. This interface defines the contract for persisting, retrieving, updating, and listing
    user data, abstracting away the underlying database or storage mechanism. Implementations of this interface can use SQL databases, NoSQL databases,
    or any other form of storage, while the application layer interacts with it through these defined methods

    Methods:
        create(user: User) -> User: Persists a new user and returns the created entity
        get_by_id(user_id: uuid.UUID) -> Optional[User]: Retrieves a user by their unique identifier, or returns None if not found.
        get_by_email(email: str) -> Optional[User]: Retrieves a user by their email address, or returns None if not found.
        list_all(active_only: bool = True) -> List[User]: Returns a list of all registered users, with an option to filter only active ones.
        update(user: User) -> User: Updates the state, password, or other data of an existing user and returns the updated entity.
    """
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
    async def list_all(self, active_only: bool = True) -> List[User]:
        pass

    @abstractmethod
    async def update(self, user: User) -> User:
        pass
from abc import ABC, abstractmethod
from typing import List, Optional
import uuid
from domain.entities.api_key import APIKey


class IAPIKeyRepository(ABC):
    @abstractmethod
    async def save(self, api_key: APIKey) -> APIKey:
        pass

    @abstractmethod
    async def get_by_id(self, api_key_id: uuid.UUID) -> Optional[APIKey]:
        pass

    @abstractmethod
    async def get_by_hash(self, key_hash: str) -> Optional[APIKey]:
        pass

    @abstractmethod
    async def list_by_organization(self, organization_id: uuid.UUID) -> List[APIKey]:
        pass

    @abstractmethod
    async def list_by_user(self, user_id: uuid.UUID) -> List[APIKey]:
        pass

    @abstractmethod
    async def update(self, api_key: APIKey) -> APIKey:
        pass

    @abstractmethod
    async def delete(self, api_key_id: uuid.UUID) -> None:
        pass
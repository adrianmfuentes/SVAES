from abc import ABC, abstractmethod
from typing import List, Optional
import uuid
from domain.entities.access_request import AccessRequest
from domain.enums import AccessRequestStatus


class IAccessRequestRepository(ABC):
    @abstractmethod
    async def create(self, access_request: AccessRequest) -> AccessRequest:
        pass

    @abstractmethod
    async def get_by_id(self, access_request_id: uuid.UUID) -> Optional[AccessRequest]:
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[AccessRequest]:
        pass

    @abstractmethod
    async def list_by_status(
        self,
        status: AccessRequestStatus,
        skip: int = 0,
        limit: int = 100,
    ) -> List[AccessRequest]:
        pass

    @abstractmethod
    async def update(self, access_request: AccessRequest) -> AccessRequest:
        pass

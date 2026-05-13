from abc import ABC, abstractmethod
from typing import Optional, List
import uuid
from domain.entities.verification_profile import VerificationProfile

class IProfileRepository(ABC):
    @abstractmethod
    async def create(self, profile: VerificationProfile) -> VerificationProfile:
        pass

    @abstractmethod
    async def get_by_id(self, profile_id: uuid.UUID) -> Optional[VerificationProfile]:
        pass

    @abstractmethod
    async def get_default_for_organization(self, organization_id: uuid.UUID) -> Optional[VerificationProfile]:
        pass

    @abstractmethod
    async def update(self, profile: VerificationProfile) -> VerificationProfile:
        pass

    @abstractmethod
    async def list_by_organization(self, organization_id: uuid.UUID, skip: int = 0, limit: int = 50) -> List[VerificationProfile]:
        pass

    @abstractmethod
    async def delete(self, profile_id: uuid.UUID) -> None:
        pass
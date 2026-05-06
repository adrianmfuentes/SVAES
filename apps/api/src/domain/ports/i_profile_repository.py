from abc import ABC, abstractmethod
from typing import Optional, List
import uuid
from domain.entities.verification_profile import VerificationProfile

class IProfileRepository(ABC):
    """Puerto para la persistencia de Perfiles de Verificación."""

    @abstractmethod
    async def create(self, profile: VerificationProfile) -> VerificationProfile:
        pass

    @abstractmethod
    async def get_by_id(self, profile_id: uuid.UUID) -> Optional[VerificationProfile]:
        pass

    @abstractmethod
    async def get_default_for_organization(self, organization_id: uuid.UUID) -> Optional[VerificationProfile]:
        pass
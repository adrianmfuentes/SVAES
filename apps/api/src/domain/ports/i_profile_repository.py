from abc import ABC, abstractmethod
from typing import Optional, List
import uuid
from domain.entities.verification_profile import VerificationProfile

class IProfileRepository(ABC):
    """Outbound port for managing VerificationProfile entities in the data store. This interface defines the contract for persisting, retrieving, and updating
    verification profile data, abstracting away the underlying database or storage mechanism. Implementations of this interface can use SQL databases,
    NoSQL databases, or any other form of storage, while the application layer interacts with it through these defined methods.

    Methods:
        create(profile: VerificationProfile) -> VerificationProfile: Persists a new verification profile and returns the created entity.
        get_by_id(profile_id: uuid.UUID) -> Optional[VerificationProfile]: Retrieves a verification profile by its unique identifier, or returns None if not found.
        get_default_for_organization(organization_id: uuid.UUID) -> Optional[VerificationProfile]: Retrieves the default verification profile for a given organization, or returns None if not found.
    """
    @abstractmethod
    async def create(self, profile: VerificationProfile) -> VerificationProfile:
        pass

    @abstractmethod
    async def get_by_id(self, profile_id: uuid.UUID) -> Optional[VerificationProfile]:
        pass

    @abstractmethod
    async def get_default_for_organization(self, organization_id: uuid.UUID) -> Optional[VerificationProfile]:
        pass
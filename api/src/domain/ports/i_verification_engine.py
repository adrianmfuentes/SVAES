from abc import ABC, abstractmethod
from typing import Dict, Any

from domain.entities.verification_result import VerificationResult
from domain.entities.release import Release
from domain.entities.verification_profile import VerificationProfile

class IVerificationEngine(ABC):
    """Outbound port for executing verification processes. This interface defines the contract for running verifications based on release data, 
    verification profiles, and associated artifacts. Implementations of this interface can integrate with various verification tools or services, 
    allowing the application layer to remain decoupled from specific verification technologies.
    
    Methods:
        execute_verification(release: Release, profile: VerificationProfile, artifacts_data: list) -> VerificationResult: Executes the verification process and returns the results.
    """
    @abstractmethod
    async def execute_verification(
        self, 
        release: Release, 
        profile: VerificationProfile, 
        artifacts_data: list
    ) -> VerificationResult:
        pass
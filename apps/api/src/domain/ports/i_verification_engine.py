from abc import ABC, abstractmethod
from typing import Dict, Any

from domain.entities.verification_result import VerificationResult
from domain.entities.release import Release
from domain.entities.verification_profile import VerificationProfile

class IVerificationEngine(ABC):
    """Puerto para invocar al motor de verificación independiente."""

    @abstractmethod
    async def execute_verification(
        self, 
        release: Release, 
        profile: VerificationProfile, 
        artifacts_data: list
    ) -> VerificationResult:
        """
        Envía los datos al motor y retorna el resultado estructurado.
        """
        pass
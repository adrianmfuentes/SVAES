from abc import ABC, abstractmethod
from typing import Dict, Any
from features.verification.domain.verification_result import VerificationResult
from features.projects_releases.domain.release import Release
from features.verification.domain.verification_profile import VerificationProfile

class IVerificationEngine(ABC):
    @abstractmethod
    async def execute_verification(
        self,
        release: Release,
        profile: VerificationProfile,
        artifacts_data: list[Dict[str, Any]],
    ) -> VerificationResult:
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        pass
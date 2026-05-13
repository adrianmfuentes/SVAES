from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from domain.entities.verification_result import VerificationResult


class IVerificationService(ABC):
    @abstractmethod
    async def launch_verification(self, release_id: UUID) -> str:
        pass

    @abstractmethod
    async def get_verification_result(
        self, release_id: UUID, result_id: UUID
    ) -> Optional[VerificationResult]:
        pass

    @abstractmethod
    async def get_verification_history(
        self, release_id: UUID
    ) -> List[VerificationResult]:
        pass

    @abstractmethod
    async def get_latest_verification(
        self, release_id: UUID
    ) -> Optional[VerificationResult]:
        pass

    @abstractmethod
    async def cancel_verification(self, release_id: UUID) -> bool:
        pass

    @abstractmethod
    async def get_verification_status(self, release_id: UUID) -> str:
        pass

    @abstractmethod
    async def list_verification_results(self, release_id: UUID) -> List[VerificationResult]:
        pass
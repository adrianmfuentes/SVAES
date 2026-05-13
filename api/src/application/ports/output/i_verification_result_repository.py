from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID
from domain.entities.verification_result import VerificationResult

class IVerificationResultRepository(ABC):
    @abstractmethod
    async def save(self, result: VerificationResult) -> VerificationResult:
        pass

    @abstractmethod
    async def find_by_id(self, result_id: UUID) -> Optional[VerificationResult]:
        pass

    @abstractmethod
    async def find_by_release(self, release_id: UUID) -> List[VerificationResult]:
        pass

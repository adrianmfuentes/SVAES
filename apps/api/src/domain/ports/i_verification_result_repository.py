from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID
from domain.entities.verification_result import VerificationResult


class IVerificationResultRepository(ABC):
    """Outbound port for persisting and querying the results of verification runs."""

    @abstractmethod
    def save(self, result: VerificationResult) -> VerificationResult:
        pass

    @abstractmethod
    def find_by_id(self, result_id: UUID) -> Optional[VerificationResult]:
        pass

    @abstractmethod
    def find_by_release(self, release_id: UUID) -> List[VerificationResult]:
        pass

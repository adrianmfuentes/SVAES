from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID
from domain.entities.verification_result import VerificationResult


class IVerificationResultRepository(ABC):
    """Outbound port for managing verification results. This repository interface abstracts the persistence mechanism for
    verification results, allowing the application layer to interact with verification result data without being coupled 
    to a specific database or storage solution.

    Methods:
        save(result: VerificationResult) -> VerificationResult: Saves a verification result to the repository and returns the saved instance.
        find_by_id(result_id: UUID) -> Optional[VerificationResult]: Retrieves a verification result by its unique identifier, returning None if not found.
        find_by_release(release_id: UUID) -> List[VerificationResult]: Retrieves all verification results associated with a specific release.
    """
    @abstractmethod
    def save(self, result: VerificationResult) -> VerificationResult:
        pass

    @abstractmethod
    def find_by_id(self, result_id: UUID) -> Optional[VerificationResult]:
        pass

    @abstractmethod
    def find_by_release(self, release_id: UUID) -> List[VerificationResult]:
        pass

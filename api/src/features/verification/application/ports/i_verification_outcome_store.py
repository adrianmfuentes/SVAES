from typing import Protocol

from features.verification.domain.verification_result import VerificationResult
from shared.domain.enums import ReleaseStatus


class IVerificationOutcomeStore(Protocol):
    async def save(self, result: VerificationResult, status: ReleaseStatus) -> VerificationResult: ...

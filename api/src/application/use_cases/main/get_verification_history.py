from typing import List
from uuid import UUID
from application.ports.output.i_verification_result_repository import IVerificationResultRepository
from domain.entities.verification_result import VerificationResult
from domain.exceptions import ValidationError


class GetVerificationHistoryUseCase:
    def __init__(
        self,
        verification_result_repository: IVerificationResultRepository,
    ) -> None:
        self._verification_repo = verification_result_repository

    async def execute(self, release_id: UUID) -> List[VerificationResult]:
        if not release_id:
            raise ValidationError("release_id es requerido")
        return await self._verification_repo.find_by_release(release_id)
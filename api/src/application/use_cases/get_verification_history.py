import uuid
from typing import List

from domain.entities.verification_result import VerificationResult
from domain.exceptions import EntityNotFoundError
from domain.ports.i_release_repository import IReleaseRepository
from domain.ports.i_verification_result_repository import IVerificationResultRepository


class GetVerificationHistoryUseCase:
    def __init__(
        self,
        release_repo: IReleaseRepository,
        verification_result_repo: IVerificationResultRepository,
    ) -> None:
        self.release_repo = release_repo
        self.verification_result_repo = verification_result_repo

    async def execute(self, release_id: uuid.UUID) -> List[VerificationResult]:
        release = await self.release_repo.get_by_id(release_id)
        if not release:
            raise EntityNotFoundError(f"Release not found with ID: {release_id}")
        return await self.verification_result_repo.find_by_release(release_id)

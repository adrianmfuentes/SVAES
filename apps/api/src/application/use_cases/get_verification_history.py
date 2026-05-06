import uuid
from typing import Dict, Any
from domain.ports.i_release_repository import IReleaseRepository
from domain.exceptions import EntityNotFoundError


class GetVerificationHistoryUseCase:
    def __init__(self, release_repo: IReleaseRepository):
        self.release_repo = release_repo

    async def execute(self, release_id: uuid.UUID) -> Dict[str, Any]:
        release = await self.release_repo.get_by_id(release_id)
        if not release:
            raise EntityNotFoundError("Release no encontrada")
        return {
            "release_id": str(release_id),
            "verdict": "PASSED",
            "duration_ms": 1450,
            "rules_evaluated": 5,
        }

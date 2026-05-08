import uuid
from typing import Dict, Any
from domain.ports.i_release_repository import IReleaseRepository
from domain.exceptions import EntityNotFoundError


class GetVerificationHistoryUseCase:
    """Use case for retrieving the verification history of a release.

    Attributes:
        release_repo (IReleaseRepository): Repository for managing release entities.

    Raises:
        EntityNotFoundError: If the release with the given ID does not exist.

    Returns:
        Dict[str, Any]: A dictionary containing the verification history details of the release.

    Note: Now returns a dictionary with hardcoded values for demonstration purposes. 
    """

    def __init__(self, release_repo: IReleaseRepository):
        self.release_repo = release_repo

    async def execute(self, release_id: uuid.UUID) -> Dict[str, Any]:
        release = await self.release_repo.get_by_id(release_id)
        
        if not release:
            raise EntityNotFoundError("Release not found with ID: {}".format(release_id))
        
        return {
            "release_id": str(release_id),
            "verdict": "PASSED",
            "duration_ms": 1450,
            "rules_evaluated": 5,
        }

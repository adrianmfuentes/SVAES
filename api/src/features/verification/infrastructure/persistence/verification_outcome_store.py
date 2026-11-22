from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from features.projects_releases.application.ports.i_release_repository import IReleaseRepository
from features.verification.domain.verification_result import VerificationResult
from features.verification.infrastructure.persistence.verification_result_repository import SqlVerificationResultRepository
from shared.domain.enums import ReleaseStatus
from shared.infrastructure.database.get_async_session import AsyncSessionLocal
from shared.infrastructure.sql_unit_of_work import SqlUnitOfWork


class SqlVerificationOutcomeStore:
    def __init__(self, release_repository: Callable[[AsyncSession], IReleaseRepository]) -> None:
        self._release_repository = release_repository

    async def save(self, result: VerificationResult, status: ReleaseStatus) -> VerificationResult:
        session = AsyncSessionLocal()
        async with SqlUnitOfWork(session).transaction():
            saved = await SqlVerificationResultRepository(session).save(result)
            await self._release_repository(session).update_status(result.release_id, status)
        return saved

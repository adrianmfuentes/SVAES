from sqlalchemy.future import select
from typing import List, Optional, cast
import uuid
from datetime import datetime
from application.ports.output.i_verification_result_repository import IVerificationResultRepository
from domain.entities.verification_result import VerificationResult
from domain.enums import VerdictType
from infrastructure.secondary.database.models.result_model import VerificationResultModel
from infrastructure.secondary.database.get_async_session import AsyncSessionLocal


class SqlVerificationResultRepository(IVerificationResultRepository):
    async def save(self, result: VerificationResult) -> VerificationResult:
        async with AsyncSessionLocal() as session:
            result_model = VerificationResultModel(
                id=result.id,
                release_id=result.release_id,
                verdict=result.verdict.value,
                duration_ms=result.duration_ms,
                summary=result.summary,
                rule_results=result.rule_results,
                profile_snapshot=result.profile_snapshot,
                executed_at=result.executed_at,
            )
            session.add(result_model)
            await session.commit()
            await session.refresh(result_model)

            return VerificationResult(
                id=cast(uuid.UUID, result_model.id),
                release_id=cast(uuid.UUID, result_model.release_id),
                verdict=VerdictType(result_model.verdict),
                duration_ms=cast(int, result_model.duration_ms),
                summary=cast(dict, result_model.summary) or {},
                rule_results=cast(list, result_model.rule_results) or [],
                profile_snapshot=cast(dict, result_model.profile_snapshot) or {},
                executed_at=cast(datetime, result_model.executed_at),
            )

    async def find_by_id(self, result_id: uuid.UUID) -> Optional[VerificationResult]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(VerificationResultModel).where(VerificationResultModel.id == result_id))
            result_row = result.scalar_one_or_none()
            if not result_row:
                return None

            return VerificationResult(
                id=cast(uuid.UUID, result_row.id),
                release_id=cast(uuid.UUID, result_row.release_id),
                verdict=VerdictType(result_row.verdict),
                duration_ms=cast(int, result_row.duration_ms),
                summary=cast(dict, result_row.summary) or {},
                rule_results=cast(list, result_row.rule_results) or [],
                profile_snapshot=cast(dict, result_row.profile_snapshot) or {},
                executed_at=cast(datetime, result_row.executed_at),
            )

    async def find_by_release(self, release_id: uuid.UUID) -> List[VerificationResult]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(VerificationResultModel)
                .where(VerificationResultModel.release_id == release_id)
                .order_by(VerificationResultModel.executed_at.desc())
            )
            result_rows = result.scalars().all()

            return [
                VerificationResult(
                    id=cast(uuid.UUID, row.id),
                    release_id=cast(uuid.UUID, row.release_id),
                    verdict=VerdictType(row.verdict),
                    duration_ms=cast(int, row.duration_ms),
                    summary=cast(dict, row.summary) or {},
                    rule_results=cast(list, row.rule_results) or [],
                    profile_snapshot=cast(dict, row.profile_snapshot) or {},
                    executed_at=cast(datetime, row.executed_at),
                )
                for row in result_rows
            ]
from sqlalchemy.future import select
from typing import List, Optional
import uuid
from datetime import datetime
from application.ports.output.i_verification_result_repository import IVerificationResultRepository
from domain.entities.verification_result import VerificationResult
from domain.enums import VerdictType
from infrastructure.secondary.database.models.result_model import VerificationResultModel
from infrastructure.secondary.database.get_async_session import get_async_session


class SqlVerificationResultRepository(IVerificationResultRepository):
    async def save(self, result: VerificationResult) -> VerificationResult:
        session = await get_async_session().__anext__()

        try:
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
                id=result_model.id,
                release_id=result_model.release_id,
                verdict=VerdictType(result_model.verdict),
                duration_ms=result_model.duration_ms,
                summary=result_model.summary or {},
                rule_results=result_model.rule_results or [],
                profile_snapshot=result_model.profile_snapshot or {},
                executed_at=result_model.executed_at,
            )
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def find_by_id(self, result_id: uuid.UUID) -> Optional[VerificationResult]:
        session = await get_async_session().__anext__()

        try:
            result = await session.execute(select(VerificationResultModel).where(VerificationResultModel.id == result_id))
            result_row = result.scalar_one_or_none()
            if not result_row:
                return None

            return VerificationResult(
                id=result_row.id,
                release_id=result_row.release_id,
                verdict=VerdictType(result_row.verdict),
                duration_ms=result_row.duration_ms,
                summary=result_row.summary or {},
                rule_results=result_row.rule_results or [],
                profile_snapshot=result_row.profile_snapshot or {},
                executed_at=result_row.executed_at,
            )
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

    async def find_by_release(self, release_id: uuid.UUID) -> List[VerificationResult]:
        session = await get_async_session().__anext__()

        try:
            result = await session.execute(
                select(VerificationResultModel)
                .where(VerificationResultModel.release_id == release_id)
                .order_by(VerificationResultModel.executed_at.desc())
            )
            result_rows = result.scalars().all()

            return [
                VerificationResult(
                    id=row.id,
                    release_id=row.release_id,
                    verdict=VerdictType(row.verdict),
                    duration_ms=row.duration_ms,
                    summary=row.summary or {},
                    rule_results=row.rule_results or [],
                    profile_snapshot=row.profile_snapshot or {},
                    executed_at=row.executed_at,
                )
                for row in result_rows
            ]
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()
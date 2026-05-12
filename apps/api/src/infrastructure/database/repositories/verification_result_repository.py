from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from domain.entities.verification_result import VerificationResult
from domain.entities.enums import VerdictType
from domain.ports.i_verification_result_repository import IVerificationResultRepository
from infrastructure.database.models.verification_result import VerificationResultModel

# DB verdicts use Spanish strings; map to domain enum
_DB_TO_DOMAIN: dict[str, VerdictType] = {
    "VALIDO": VerdictType.VALID,
    "CON_ADVERTENCIAS": VerdictType.VALID_WITH_WARNINGS,
    "NO_VALIDO": VerdictType.INVALID,
}
_DOMAIN_TO_DB: dict[VerdictType, str] = {v: k for k, v in _DB_TO_DOMAIN.items()}


class SqlVerificationResultRepository(IVerificationResultRepository):
    """Async SQLAlchemy adapter — used by FastAPI request handlers."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, result: VerificationResult) -> VerificationResult:
        model = await self.session.get(VerificationResultModel, result.id)
        if model is None:
            model = VerificationResultModel(
                id=result.id,
                release_id=result.release_id,
                verdict=_DOMAIN_TO_DB.get(result.verdict, "VALIDO"),
                rule_results=result.rule_results,
                profile_snapshot=result.profile_snapshot,
                executed_at=result.executed_at,
                duration_ms=result.duration_ms,
            )
            self.session.add(model)
        await self.session.flush()
        return result

    async def find_by_id(self, result_id: UUID) -> Optional[VerificationResult]:
        model = await self.session.get(VerificationResultModel, result_id)
        return self._to_entity(model) if model else None

    async def find_by_release(self, release_id: UUID) -> List[VerificationResult]:
        result = await self.session.execute(
            select(VerificationResultModel)
            .where(VerificationResultModel.release_id == release_id)
            .order_by(VerificationResultModel.executed_at.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    def _to_entity(self, model: VerificationResultModel) -> VerificationResult:
        return VerificationResult(
            id=model.id,
            release_id=model.release_id,
            verdict=_DB_TO_DOMAIN.get(model.verdict, VerdictType.INVALID),
            rule_results=model.rule_results or {},
            profile_snapshot=model.profile_snapshot or {},
            executed_at=model.executed_at,
            duration_ms=model.duration_ms or 0,
        )


class SyncSqlVerificationResultRepository:
    """Sync SQLAlchemy adapter — used by Celery workers (no event loop)."""

    def __init__(self, session: Session):
        self.session = session

    def save(self, result: VerificationResult) -> VerificationResult:
        model = self.session.get(VerificationResultModel, result.id)
        if model is None:
            model = VerificationResultModel(
                id=result.id,
                release_id=result.release_id,
                verdict=_DOMAIN_TO_DB.get(result.verdict, "VALIDO"),
                rule_results=result.rule_results,
                profile_snapshot=result.profile_snapshot,
                executed_at=result.executed_at,
                duration_ms=result.duration_ms,
            )
            self.session.add(model)
        self.session.flush()
        return result

    def find_by_release(self, release_id: UUID) -> List[VerificationResult]:
        models = (
            self.session.query(VerificationResultModel)
            .filter_by(release_id=release_id)
            .order_by(VerificationResultModel.executed_at.desc())
            .all()
        )
        return [self._to_entity(m) for m in models]

    def _to_entity(self, model: VerificationResultModel) -> VerificationResult:
        return VerificationResult(
            id=model.id,
            release_id=model.release_id,
            verdict=_DB_TO_DOMAIN.get(model.verdict, VerdictType.INVALID),
            rule_results=model.rule_results or {},
            profile_snapshot=model.profile_snapshot or {},
            executed_at=model.executed_at,
            duration_ms=model.duration_ms or 0,
        )

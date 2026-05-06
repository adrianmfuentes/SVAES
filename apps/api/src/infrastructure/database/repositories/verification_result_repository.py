from uuid import UUID
from sqlalchemy.orm import Session
from domain.entities.verification_result import VerificationResult
from domain.entities.enums import VerdictType
from domain.ports.i_verification_result_repository import IVerificationResultRepository
from infrastructure.database.models.verification_result import VerificationResultModel

class SqlVerificationResultRepository(IVerificationResultRepository):
    def __init__(self, session: Session):
        self.session = session

    def save(self, result: VerificationResult) -> VerificationResult:
        model = self.session.get(VerificationResultModel, result.id)
        if model is None:
            model = VerificationResultModel(
                id=result.id,
                release_id=result.release_id,
                verdict=result.verdict,
                rule_results=result.rule_results,
                profile_snapshot=result.profile_snapshot,
                executed_at=result.executed_at,
                duration_ms=result.duration_ms,
            )
            self.session.add(model)
        self.session.flush()
        return result

    def find_by_id(self, result_id: UUID) -> VerificationResult | None:
        model = self.session.get(VerificationResultModel, result_id)
        return self._to_entity(model) if model else None

    def find_by_release(self, release_id: UUID) -> list[VerificationResult]:
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
            verdict=VerdictType(model.verdict),
            rule_results=model.rule_results or {},
            profile_snapshot=model.profile_snapshot or {},
            executed_at=model.executed_at,
            duration_ms=model.duration_ms,
        )
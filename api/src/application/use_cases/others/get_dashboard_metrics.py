from collections import defaultdict
from uuid import UUID
from dataclasses import dataclass, field
from application.ports.output.i_verification_result_repository import IVerificationResultRepository
from application.ports.output.i_release_repository import IReleaseRepository
from domain.enums import ReleaseStatus, VerdictType


@dataclass
class DashboardMetrics:
    total_releases: int
    valid_releases: int
    invalid_releases: int
    pending_releases: int
    total_verifications: int
    pass_rate: float
    temporal_data: list = field(default_factory=list)
    top_failed_rules: list = field(default_factory=list)


class GetDashboardMetricsUseCase:
    def __init__(
        self,
        release_repository: IReleaseRepository,
        verification_repository: IVerificationResultRepository,
    ) -> None:
        self._release_repo = release_repository
        self._verification_repo = verification_repository

    async def execute(self, organization_id: UUID) -> DashboardMetrics:
        releases = await self._release_repo.list_by_organization(organization_id)
        total_releases = len(releases)

        valid_releases = sum(1 for r in releases if r.status == ReleaseStatus.VALIDA)
        invalid_releases = sum(1 for r in releases if r.status == ReleaseStatus.NO_VALIDA)
        pending_releases = sum(
            1
            for r in releases
            if r.status in (ReleaseStatus.PENDIENTE, ReleaseStatus.BORRADOR)
        )

        all_results = []
        for release in releases:
            results = await self._verification_repo.find_by_release(release.id)
            all_results.extend(results)

        total_verifications = len(all_results)
        valid_verifications = sum(
            1 for r in all_results if r.verdict == VerdictType.VALID
        )
        pass_rate = (
            (valid_verifications / total_verifications * 100)
            if total_verifications > 0
            else 0.0
        )

        return DashboardMetrics(
            total_releases=total_releases,
            valid_releases=valid_releases,
            invalid_releases=invalid_releases,
            pending_releases=pending_releases,
            total_verifications=total_verifications,
            pass_rate=round(pass_rate, 2),
            temporal_data=self._compute_temporal_data(all_results),
            top_failed_rules=self._compute_top_failed_rules(all_results),
        )

    def _compute_temporal_data(self, all_results: list) -> list:
        daily: dict = defaultdict(lambda: {"valid": 0, "with_warnings": 0, "invalid": 0})
        for result in all_results:
            if not result.executed_at:
                continue
            day = result.executed_at.strftime("%Y-%m-%d")
            if result.verdict == VerdictType.VALID:
                daily[day]["valid"] += 1
            elif result.verdict == VerdictType.VALID_WITH_WARNINGS:
                daily[day]["with_warnings"] += 1
            else:
                daily[day]["invalid"] += 1
        return [
            {"date": day, **counts}
            for day, counts in sorted(daily.items())
        ]

    def _compute_top_failed_rules(self, all_results: list) -> list:
        rule_counts: dict = {}
        total_fails = 0
        for result in all_results:
            for rule_result in (result.rule_results or []):
                status = (rule_result.get("status") or "").upper()
                if status not in ("ERROR", "FAILED"):
                    continue
                rid = rule_result.get("rule_id", "")
                name = rule_result.get("rule_name", rid)
                if rid not in rule_counts:
                    rule_counts[rid] = {"rule_id": rid, "rule_name": name, "count": 0}
                rule_counts[rid]["count"] += 1
                total_fails += 1

        top = sorted(rule_counts.values(), key=lambda x: x["count"], reverse=True)[:5]
        for rule in top:
            rule["percentage"] = (
                round(rule["count"] / total_fails * 100, 1) if total_fails > 0 else 0.0
            )
        return top

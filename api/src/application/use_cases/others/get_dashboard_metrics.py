from uuid import UUID
from dataclasses import dataclass
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
        )
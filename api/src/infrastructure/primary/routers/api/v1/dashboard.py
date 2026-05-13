from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from application.ports.output.i_verification_result_repository import IVerificationResultRepository
from application.ports.output.i_release_repository import IReleaseRepository
from application.use_cases.others.get_dashboard_metrics import GetDashboardMetricsUseCase
from core.dependencies import get_current_user, CurrentUser, get_release_repository, get_verification_result_repository

router = APIRouter(tags=["Dashboard"])


class DashboardMetricsResponse(BaseModel):
    total_releases: int
    valid_releases: int
    invalid_releases: int
    pending_releases: int
    total_verifications: int
    pass_rate: float


@router.get("/api/v1/organizations/{org_id}/dashboard/metrics")
async def get_dashboard_metrics(
    org_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    release_repo: IReleaseRepository = Depends(get_release_repository),
    verification_repo: IVerificationResultRepository = Depends(get_verification_result_repository),
):
    """Endpoint para obtener métricas del dashboard de una organización.

    Atributos:
        - org_id: UUID - El ID de la organización.
        - current_user: Usuario autenticado con permisos del token JWT.
        - release_repo: Repositorio de releases inyectado.
        - verification_repo: Repositorio de resultados de verificación inyectado.

    Retorna:
        - Métricas agregadas del dashboard incluyendo totales de releases,
          verificaciones y tasa de aprobación.
    """
    try:
        use_case = GetDashboardMetricsUseCase(
            release_repository=release_repo,
            verification_repository=verification_repo,
        )
        metrics = await use_case.execute(org_id)
        return DashboardMetricsResponse(
            total_releases=metrics.total_releases,
            valid_releases=metrics.valid_releases,
            invalid_releases=metrics.invalid_releases,
            pending_releases=metrics.pending_releases,
            total_verifications=metrics.total_verifications,
            pass_rate=metrics.pass_rate,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
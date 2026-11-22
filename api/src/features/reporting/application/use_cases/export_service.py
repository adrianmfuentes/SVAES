import logging
from uuid import UUID
from features.reporting.application.ports.i_export_service import IExportService
from features.projects_releases.application.ports.i_release_repository import IReleaseRepository
from features.verification.application.ports.i_verification_result_repository import IVerificationResultRepository
from features.projects_releases.application.ports.i_project_repository import IProjectRepository
from features.reporting.application.ports.i_report_renderers import ICsvExporter, IPdfRenderer
import os
import tempfile

_log = logging.getLogger(__name__)


class ExportService(IExportService):

    def __init__(
        self,
        release_repository: IReleaseRepository,
        verification_repository: IVerificationResultRepository,
        project_repository: IProjectRepository,
        pdf_renderer: IPdfRenderer,
        csv_exporter: ICsvExporter,
    ):
        self._release_repo       = release_repository
        self._verification_repo  = verification_repository
        self._project_repo       = project_repository
        self._pdf_renderer = pdf_renderer
        self._csv_exporter = csv_exporter

    async def export_verification_to_pdf(
        self, release_id: UUID, result_id: UUID, lang: str = "es"
    ) -> str:
        result = await self._verification_repo.find_by_id(result_id)
        if not result:
            raise ValueError(f"Verificación no encontrada: {result_id}")

        release   = await self._release_repo.get_by_id(release_id)
        safe_lang = lang if lang in ("es", "en") else "es"
        pdf_path  = os.path.join(
            tempfile.gettempdir(), f"verification_{result_id}_{safe_lang}.pdf"
        )

        await self._pdf_renderer.render(pdf_path, result, release, safe_lang)
        _log.info("PDF exported: result_id=%s lang=%s path=%s", result_id, safe_lang, pdf_path)
        return pdf_path

    async def export_project_results_to_csv(self, project_id: UUID) -> str:
        project = await self._project_repo.get_by_id(project_id)
        if not project:
            raise ValueError(f"Proyecto no encontrado: {project_id}")

        releases = await self._release_repo.list_by_project(project_id)
        results  = []
        for release in releases:
            for ver in await self._verification_repo.find_by_release(release.id):
                results.append({
                    "release_id":       str(release.id),
                    "release_name":     release.name,
                    "release_version":  release.version,
                    "verification_id":  str(ver.id),
                    "verdict":          ver.verdict,
                    "executed_at":      ver.executed_at.isoformat() if ver.executed_at else "",
                })

        csv_path = os.path.join(
            tempfile.gettempdir(), f"project_{project_id}_results.csv"
        )
        await self._csv_exporter.export(csv_path, results)
        _log.info("CSV exported: project_id=%s path=%s count=%d", project_id, csv_path, len(results))
        return csv_path

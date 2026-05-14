from uuid import UUID
from application.ports.input.i_export_service import IExportService
from application.ports.output.i_release_repository import IReleaseRepository
from application.ports.output.i_verification_result_repository import IVerificationResultRepository
from application.ports.output.i_project_repository import IProjectRepository
from core.logger import get_logger
import asyncio
import tempfile
import csv
import os

_log = get_logger(__name__)


def _write_bytes(path: str, content: bytes) -> None:
    with open(path, "wb") as f:
        f.write(content)


def _write_csv(path: str, results: list) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        if results:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)


class ExportService(IExportService):

    def __init__(
        self,
        release_repository: IReleaseRepository,
        verification_repository: IVerificationResultRepository,
        project_repository: IProjectRepository,
    ):
        self._release_repo = release_repository
        self._verification_repo = verification_repository
        self._project_repo = project_repository

    async def export_verification_to_pdf(self, release_id: UUID, result_id: UUID) -> str:
        result = await self._verification_repo.get_by_id(result_id)
        if not result:
            raise ValueError(f"Verificación no encontrada: {result_id}")

        temp_dir = tempfile.gettempdir()
        pdf_path = os.path.join(temp_dir, f"verification_{result_id}.pdf")

        pdf_content = (
            b"%PDF-1.4\n"
            b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
            b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n"
            b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n199\n%%EOF\n"
        )
        await asyncio.to_thread(_write_bytes, pdf_path, pdf_content)

        _log.info("PDF exported: result_id=%s path=%s", result_id, pdf_path)
        return pdf_path

    async def export_project_results_to_csv(self, project_id: UUID) -> str:
        project = await self._project_repo.get_by_id(project_id)
        if not project:
            raise ValueError(f"Proyecto no encontrado: {project_id}")

        releases = await self._release_repo.list_by_project(project_id)
        results = []
        for release in releases:
            verifications = await self._verification_repo.list_by_release(release.id)
            for ver in verifications:
                results.append({
                    "release_id": str(release.id),
                    "release_name": release.name,
                    "release_version": release.version,
                    "verification_id": str(ver.id),
                    "verdict": ver.verdict,
                    "executed_at": ver.executed_at.isoformat() if ver.executed_at else "",
                })

        temp_dir = tempfile.gettempdir()
        csv_path = os.path.join(temp_dir, f"project_{project_id}_results.csv")

        await asyncio.to_thread(_write_csv, csv_path, results)

        _log.info("CSV exported: project_id=%s path=%s count=%d", project_id, csv_path, len(results))
        return csv_path
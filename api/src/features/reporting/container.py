from __future__ import annotations

from bootstrap.repositories import get_project_repository, get_release_repository, get_verification_result_repository
from features.reporting.application.ports.i_export_service import IExportService
from features.reporting.application.use_cases.export_service import ExportService
from features.reporting.infrastructure.gateways.csv_exporter import CsvExporter
from features.reporting.infrastructure.gateways.pdf_renderer import PdfRenderer


def get_export_service() -> IExportService:
    release_repo = get_release_repository()
    verification_repo = get_verification_result_repository()
    project_repo = get_project_repository()
    return ExportService(
        release_repository=release_repo,
        verification_repository=verification_repo,
        project_repository=project_repo,
        pdf_renderer=PdfRenderer(),
        csv_exporter=CsvExporter(),
    )

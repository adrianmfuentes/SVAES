import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from application.use_cases.main.export_service import ExportService, _write_bytes, _write_csv
from domain.entities.release import Release
from domain.entities.verification_result import VerificationResult
from domain.entities.project import Project
from domain.enums import ReleaseStatus, VerdictType

pytestmark = pytest.mark.unit


@pytest.fixture
def release_repo():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.list_by_project = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def verification_repo():
    repo = AsyncMock()
    repo.find_by_id = AsyncMock(return_value=None)
    repo.find_by_release = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def project_repo():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def service(release_repo, verification_repo, project_repo):
    return ExportService(release_repo, verification_repo, project_repo)


@pytest.fixture
def sample_release():
    return Release(
        id=uuid4(),
        name="Test Release",
        version="1.0.0",
        project_id=uuid4(),
        profile_id=uuid4(),
        created_by=uuid4(),
        description="A test release",
        status=ReleaseStatus.VALIDA,
    )


@pytest.fixture
def sample_result(sample_release):
    return VerificationResult(
        id=uuid4(),
        release_id=sample_release.id,
        verdict=VerdictType.VALID,
        rule_results=[
            {"rule": "check_1", "status": "passed", "message": "OK"},
            {"rule": "check_2", "status": "failed", "message": "Error"},
        ],
        summary="All checks passed",
        executed_at=datetime.now(timezone.utc),
    )


class TestWriteBytes:
    def test_write_bytes_success(self, tmp_path):
        """Verifica que los bytes se escriban correctamente en un archivo."""
        path = os.path.join(tmp_path, "test.bin")
        _write_bytes(path, b"hello world")

        with open(path, "rb") as f:
            assert f.read() == b"hello world"


class TestWriteCsv:
    def test_write_csv_success(self, tmp_path):
        """Verifica que los datos se escriban correctamente en CSV."""
        path = os.path.join(tmp_path, "test.csv")
        results = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]
        _write_csv(path, results)

        with open(path, "r", newline="", encoding="utf-8") as f:
            content = f.read()
        assert "name,age" in content or "age,name" in content
        assert "Alice" in content
        assert "Bob" in content

    def test_write_csv_empty_list(self, tmp_path):
        """Verifica que una lista vacía cree un archivo CSV vacío."""
        path = os.path.join(tmp_path, "empty.csv")
        _write_csv(path, [])

        with open(path, "r", newline="", encoding="utf-8") as f:
            content = f.read()
        assert content == ""


class TestExportPdf:
    @patch("reportlab.platypus.SimpleDocTemplate")
    async def test_export_pdf_success(self, mock_doc_template, service, verification_repo, release_repo, sample_release, sample_result):
        """Verifica la exportación exitosa de un PDF."""
        verification_repo.find_by_id.return_value = sample_result
        release_repo.get_by_id.return_value = sample_release

        mock_doc = MagicMock()
        mock_doc_template.return_value = mock_doc

        path = await service.export_verification_to_pdf(sample_release.id, sample_result.id)

        assert path.endswith(f"verification_{sample_result.id}.pdf")
        mock_doc_template.assert_called_once()
        mock_doc.build.assert_called_once()

    async def test_export_pdf_verification_not_found(self, service, verification_repo):
        """Verifica que se lance ValueError cuando la verificación no existe."""
        verification_repo.find_by_id.return_value = None

        with pytest.raises(ValueError, match="Verificación no encontrada"):
            await service.export_verification_to_pdf(uuid4(), uuid4())

    @patch("reportlab.platypus.SimpleDocTemplate")
    async def test_export_pdf_release_not_found_still_works(self, mock_doc_template, service, verification_repo, release_repo, sample_result):
        """Verifica que el PDF se genere incluso si la release no existe."""
        verification_repo.find_by_id.return_value = sample_result
        release_repo.get_by_id.return_value = None

        mock_doc = MagicMock()
        mock_doc_template.return_value = mock_doc

        path = await service.export_verification_to_pdf(uuid4(), sample_result.id)

        assert path.endswith(".pdf")


class TestExportCsv:
    @patch("application.use_cases.main.export_service._write_csv")
    async def test_export_csv_success(self, mock_write_csv, service, release_repo, verification_repo, project_repo):
        """Verifica la exportación exitosa de resultados a CSV."""
        project_id = uuid4()
        project = Project(
            id=project_id,
            name="Test Project",
            description="",
            organization_id=uuid4(),
            profile_id=uuid4(),
        )
        project_repo.get_by_id.return_value = project

        release = Release(
            id=uuid4(),
            name="Release 1",
            version="1.0.0",
            project_id=project_id,
            profile_id=uuid4(),
            created_by=uuid4(),
            status=ReleaseStatus.VALIDA,
        )
        release_repo.list_by_project.return_value = [release]

        ver_result = VerificationResult(
            id=uuid4(),
            release_id=release.id,
            verdict=VerdictType.VALID,
            rule_results=[],
            executed_at=datetime.now(timezone.utc),
        )
        verification_repo.find_by_release.return_value = [ver_result]

        csv_path = await service.export_project_results_to_csv(project_id)

        assert csv_path.endswith(f"project_{project_id}_results.csv")
        assert mock_write_csv.called

    async def test_export_csv_project_not_found(self, service, project_repo):
        """Verifica que se lance ValueError cuando el proyecto no existe."""
        project_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="Proyecto no encontrado"):
            await service.export_project_results_to_csv(uuid4())

    @patch("application.use_cases.main.export_service._write_csv")
    async def test_export_csv_empty_results(self, mock_write_csv, service, release_repo, verification_repo, project_repo):
        """Verifica que se exporte un CSV vacío cuando no hay resultados."""
        project_id = uuid4()
        project = Project(
            id=project_id,
            name="Empty Project",
            description="",
            organization_id=uuid4(),
            profile_id=uuid4(),
        )
        project_repo.get_by_id.return_value = project
        release_repo.list_by_project.return_value = []
        verification_repo.find_by_release.return_value = []

        csv_path = await service.export_project_results_to_csv(project_id)

        assert mock_write_csv.called
        call_args = mock_write_csv.call_args[0]
        assert call_args == (csv_path, [])

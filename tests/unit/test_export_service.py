"""
Branch-coverage tests for application/use_cases/main/export_service.py.
"""

import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from uuid import uuid4

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api", "src"))

pytestmark = pytest.mark.unit


class TestExportHelpers:
    """Cover _write_bytes and _write_csv module-level helpers."""

    def test_write_bytes_writes_content(self, tmp_path):
        """Branch: _write_bytes opens file in wb mode and writes content"""
        from application.use_cases.main.export_service import _write_bytes
        path = str(tmp_path / "test.bin")
        _write_bytes(path, b"hello")
        with open(path, "rb") as f:
            assert f.read() == b"hello"

    def test_write_csv_empty_results_creates_empty_file(self, tmp_path):
        """Branch: _write_csv with empty results list → no header, no rows"""
        from application.use_cases.main.export_service import _write_csv
        path = str(tmp_path / "empty.csv")
        _write_csv(path, [])
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert content == ""

    def test_write_csv_with_results_writes_header_and_rows(self, tmp_path):
        """Branch: _write_csv with results → writes DictWriter header + rows"""
        from application.use_cases.main.export_service import _write_csv
        results = [
            {"col_a": "val1", "col_b": "val2"},
            {"col_a": "val3", "col_b": "val4"},
        ]
        path = str(tmp_path / "data.csv")
        _write_csv(path, results)
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) == 3
        assert "col_a,col_b" in lines[0].strip()
        assert "val1,val2" in lines[1].strip()


class TestExportServicePDF:
    """Cover export_verification_to_pdf branches."""

    @pytest.fixture
    def svc(self):
        from application.use_cases.main.export_service import ExportService
        release_repo = AsyncMock()
        verification_repo = AsyncMock()
        project_repo = AsyncMock()
        return ExportService(release_repo, verification_repo, project_repo), release_repo, verification_repo

    async def test_export_pdf_result_not_found_raises(self, svc):
        """Branch: result not found → ValueError"""
        service, _, verification_repo = svc
        verification_repo.find_by_id = AsyncMock(return_value=None)
        with pytest.raises(ValueError, match="Verificaci"):
            await service.export_verification_to_pdf(uuid4(), uuid4())

    async def test_export_pdf_result_exists_generates_pdf(self, svc):
        """Branch: result found, release found → PDF generated and path returned"""
        service, release_repo, verification_repo = svc
        from domain.entities.verification_result import VerificationResult
        from domain.entities.release import Release
        from domain.enums import VerdictType

        rid = uuid4()
        vid = uuid4()

        result = VerificationResult(
            id=vid,
            release_id=rid,
            verdict=VerdictType.VALID,
            summary={"message": "All good"},
            rule_results=[
                {"rule": "RV01", "status": "PASS", "message": "ok"},
                {"rule": "RV02", "status": "FAIL", "message": "bad"},
            ],
            executed_at=MagicMock(),
        )
        result.executed_at.strftime = MagicMock(return_value="2024-01-01 00:00:00 UTC")

        release = Release(
            id=rid,
            name="v1.0.0",
            version="1.0.0",
            project_id=uuid4(),
            profile_id=uuid4(),
            created_by=uuid4(),
            status=MagicMock(),
        )

        verification_repo.find_by_id = AsyncMock(return_value=result)
        release_repo.get_by_id = AsyncMock(return_value=release)

        with patch("reportlab.platypus.SimpleDocTemplate") as mock_doc:
            mock_instance = MagicMock()
            mock_doc.return_value = mock_instance

            pdf_path = await service.export_verification_to_pdf(rid, vid)

            assert pdf_path.endswith(f"verification_{vid}.pdf")
            mock_instance.build.assert_called_once()

    async def test_export_pdf_result_found_release_none(self, svc):
        """Branch: result found but release is None → PDF still generated with N/A"""
        service, release_repo, verification_repo = svc
        from domain.entities.verification_result import VerificationResult
        from domain.enums import VerdictType

        rid = uuid4()
        vid = uuid4()

        result = VerificationResult(
            id=vid,
            release_id=rid,
            verdict=VerdictType.VALID,
            summary={},
            rule_results=[],
            executed_at=MagicMock(),
        )

        verification_repo.find_by_id = AsyncMock(return_value=result)
        release_repo.get_by_id = AsyncMock(return_value=None)

        with patch("reportlab.platypus.SimpleDocTemplate") as mock_doc:
            mock_instance = MagicMock()
            mock_doc.return_value = mock_instance

            pdf_path = await service.export_verification_to_pdf(rid, vid)

            mock_instance.build.assert_called_once()

    async def test_export_pdf_verdict_no_value_attr(self, svc):
        """Branch: verdict has no .value attribute → str(verdict) fallback"""
        service, release_repo, verification_repo = svc
        from domain.entities.verification_result import VerificationResult

        rid = uuid4()
        vid = uuid4()
        result = MagicMock()
        result.verdict = "CUSTOM_VERDICT"
        result.summary = {}
        result.rule_results = []
        result.executed_at = None

        verification_repo.find_by_id = AsyncMock(return_value=result)
        release_repo.get_by_id = AsyncMock(return_value=None)

        with patch("reportlab.platypus.SimpleDocTemplate") as mock_doc:
            mock_instance = MagicMock()
            mock_doc.return_value = mock_instance

            await service.export_verification_to_pdf(rid, vid)
            mock_instance.build.assert_called_once()


class TestExportServiceCSV:
    """Cover export_project_results_to_csv branches."""

    @pytest.fixture
    def svc(self):
        from application.use_cases.main.export_service import ExportService
        release_repo = AsyncMock()
        verification_repo = AsyncMock()
        project_repo = AsyncMock()
        return ExportService(release_repo, verification_repo, project_repo), release_repo, verification_repo, project_repo

    async def test_export_csv_project_not_found_raises(self, svc):
        """Branch: project not found → ValueError"""
        service, _, _, project_repo = svc
        project_repo.get_by_id = AsyncMock(return_value=None)
        with pytest.raises(ValueError, match="Proyecto"):
            await service.export_project_results_to_csv(uuid4())

    async def test_export_csv_project_found_no_releases(self, svc):
        """Branch: project found, no releases → empty CSV"""
        service, release_repo, _, project_repo = svc
        from domain.entities.project import Project

        pid = uuid4()
        project = Project(id=pid, name="test", organization_id=uuid4(), description="desc", profile_id=uuid4())
        project_repo.get_by_id = AsyncMock(return_value=project)
        release_repo.list_by_project = AsyncMock(return_value=[])

        with patch("application.use_cases.main.export_service._write_csv") as mock_write:
            csv_path = await service.export_project_results_to_csv(pid)
            assert f"project_{pid}_results.csv" in csv_path
            mock_write.assert_called_once_with(pytest.approx(csv_path), [])

    async def test_export_csv_with_releases_and_verifications(self, svc):
        """Branch: project with releases and verification results → populated CSV"""
        service, release_repo, verification_repo, project_repo = svc
        from domain.entities.project import Project
        from domain.entities.release import Release

        pid = uuid4()
        project = Project(id=pid, name="test", organization_id=uuid4(), description="desc", profile_id=uuid4())

        rid1 = uuid4()
        release1 = Release(
            id=rid1, name="R1", version="1.0", project_id=pid,
            profile_id=uuid4(), created_by=uuid4(), status=MagicMock(),
        )
        ver1 = MagicMock()
        ver1.id = uuid4()
        ver1.verdict = "VALID"
        ver1.executed_at = MagicMock()
        ver1.executed_at.isoformat.return_value = "2024-01-01T00:00:00"

        project_repo.get_by_id = AsyncMock(return_value=project)
        release_repo.list_by_project = AsyncMock(return_value=[release1])
        verification_repo.find_by_release = AsyncMock(return_value=[ver1])

        with patch("application.use_cases.main.export_service._write_csv") as mock_write:
            await service.export_project_results_to_csv(pid)
            call_args = mock_write.call_args_list[0][0]
            assert len(call_args[1]) == 1
            assert call_args[1][0]["release_name"] == "R1"

    async def test_export_csv_executed_at_none(self, svc):
        """Branch: verification result has executed_at=None → empty string"""
        service, release_repo, verification_repo, project_repo = svc
        from domain.entities.project import Project
        from domain.entities.release import Release

        pid = uuid4()
        project = Project(id=pid, name="test", organization_id=uuid4(), description="desc", profile_id=uuid4())
        rid1 = uuid4()
        release1 = Release(
            id=rid1, name="R1", version="1.0", project_id=pid,
            profile_id=uuid4(), created_by=uuid4(), status=MagicMock(),
        )
        ver = MagicMock()
        ver.id = uuid4()
        ver.verdict = "VALID"
        ver.executed_at = None

        project_repo.get_by_id = AsyncMock(return_value=project)
        release_repo.list_by_project = AsyncMock(return_value=[release1])
        verification_repo.find_by_release = AsyncMock(return_value=[ver])

        with patch("application.use_cases.main.export_service._write_csv") as mock_write:
            await service.export_project_results_to_csv(pid)
            call_args = mock_write.call_args_list[0][0]
            assert call_args[1][0]["executed_at"] == ""

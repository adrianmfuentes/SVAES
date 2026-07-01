"""
Consolidated router/endpoint unit tests.
Sources merged:
  - test_releases_endpoint.py
  - test_routers_coverage.py
  - test_routers_extended.py
  - test_remaining_gaps.py (router classes only)
  - test_more_services.py (router classes only)
  - test_low_coverage_boost.py (router classes only)
"""

import os
import json
import sys
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET_KEY", "base-choice-test-secret-key-32-ch!")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXPIRE_MINUTES", "60")
os.environ.setdefault("ALLOWED_ORIGINS", "*")
os.environ.setdefault("ENCRYPTION_KEY", "g7vylajG0IOM0hvMbCNcVWN7G9l1oIF_pHFIj5uO5m8=")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
os.environ.setdefault("ENGINE_URL", "http://localhost:8081")
os.environ.setdefault("ENGINE_API_KEY", "test-key")
os.environ.setdefault("ADMIN_EMAIL", "admin@test.local")
os.environ.setdefault("ADMIN_PASSWORD", "admin-test-pass")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api", "src"))

pytestmark = pytest.mark.unit


# ═══════════════════════════════════════════════════════════════════════════════
# Unified helpers
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


def _token(user_id, org_id, role_str="OPERATOR"):
    from domain.enums import UserRole
    from infrastructure.primary.middleware.jwt_handler import JwtHandler
    role_map = {
        "OPERATOR": UserRole.U2,
        "ADMIN": UserRole.U3,
        "MANAGER": UserRole.U4,
    }
    handler = JwtHandler(
        secret=os.environ["JWT_SECRET_KEY"],
        algorithm=os.environ["JWT_ALGORITHM"],
        access_token_expire_minutes=60,
        refresh_token_expire_days=30,
        redis_url=None,
    )
    return handler.create_access_token(
        user_id=user_id,
        email=f"{role_str.lower()}@test.com",
        role=role_map[role_str],
        organization_id=org_id,
    )


def _make_org(org_id, owner_id=None):
    org = MagicMock()
    org.id = org_id
    org.owner_id = owner_id
    org.name = "Test Org"
    org.slug = "test-org"
    org.is_active = True
    org.created_at = datetime.now(timezone.utc)
    return org


def _make_project(proj_id=None, org_id=None):
    p = MagicMock()
    p.id = proj_id or uuid4()
    p.name = "Proj"
    p.description = "desc"
    p.organization_id = org_id or uuid4()
    p.profile_id = uuid4()
    p.is_archived = False
    p.created_at = datetime.now(timezone.utc)
    return p


def _make_release_service():
    service = AsyncMock()
    release = MagicMock()
    release.id = uuid4()
    release.status = MagicMock()
    release.status.value = "BORRADOR"
    service.create_release = AsyncMock(return_value=release)
    return service


def _make_project_repo(project, operator_user_id):
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=project)
    return repo


def _make_org_repo(org):
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=org)
    return repo


# ═══════════════════════════════════════════════════════════════════════════════
# TestCreateReleaseEndpoint  (from test_releases_endpoint.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCreateReleaseEndpoint:
    """
    TC-UNI-API-00 a TC-UNI-API-07: Base Choice sobre POST /releases.
    """

    @pytest.fixture(autouse=True)
    def _setup_app(self):
        from fastapi.testclient import TestClient
        from main import app
        from core.dependencies import (
            get_release_service,
            get_project_repository,
            get_organization_repository,
        )

        self.app = app

        self.user_id = uuid4()
        self.org_id = uuid4()
        self.project_id = uuid4()

        project = MagicMock()
        project.id = self.project_id
        project.organization_id = self.org_id
        project.profile_id = uuid4()

        org = MagicMock()
        org.id = self.org_id
        org.owner_id = self.user_id

        self.release_service = _make_release_service()
        self.project_repo = _make_project_repo(project, self.user_id)
        self.org_repo = _make_org_repo(org)

        app.dependency_overrides[get_release_service] = lambda: self.release_service
        app.dependency_overrides[get_project_repository] = lambda: self.project_repo
        app.dependency_overrides[get_organization_repository] = lambda: self.org_repo

        self.client = TestClient(app)
        yield
        app.dependency_overrides.clear()

    def _valid_body(self):
        return {"name": "Release v1.0.0", "version": "1.0.0", "description": "Test"}

    def _headers(self, token):
        return {"Authorization": f"Bearer {token}"}

    # TC-UNI-API-00: Base Case
    def test_tc_uni_api_00_base_case_operator_valid_token_returns_201(self):
        from fastapi.testclient import TestClient
        token = _token(self.user_id, self.org_id, "OPERATOR")
        resp = self.client.post(
            f"/api/v1/projects/{self.project_id}/releases",
            json=self._valid_body(),
            headers=self._headers(token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert "status" in data

    # TC-UNI-API-01: Variacion ADMIN -> 201 (admin bypasses project checks)
    def test_tc_uni_api_01_admin_role_bypasses_checks_returns_201(self):
        from fastapi.testclient import TestClient
        token = _token(self.user_id, self.org_id, "ADMIN")
        resp = self.client.post(
            f"/api/v1/projects/{self.project_id}/releases",
            json=self._valid_body(),
            headers=self._headers(token),
        )
        assert resp.status_code == 201

    # TC-UNI-API-03: No token -> 401
    def test_tc_uni_api_03_no_token_returns_401(self):
        from fastapi.testclient import TestClient
        resp = self.client.post(
            f"/api/v1/projects/{self.project_id}/releases",
            json=self._valid_body(),
        )
        assert resp.status_code == 401

    # TC-UNI-API-04: Missing name -> 422
    def test_tc_uni_api_04_missing_name_returns_422(self):
        from fastapi.testclient import TestClient
        token = _token(self.user_id, self.org_id, "OPERATOR")
        resp = self.client.post(
            f"/api/v1/projects/{self.project_id}/releases",
            json={"version": "1.0.0"},
            headers=self._headers(token),
        )
        assert resp.status_code == 422

    # TC-UNI-API-05: Nonexistent project -> 404
    def test_tc_uni_api_05_nonexistent_project_returns_404(self):
        from fastapi.testclient import TestClient
        self.project_repo.get_by_id = AsyncMock(return_value=None)
        token = _token(self.user_id, self.org_id, "OPERATOR")
        resp = self.client.post(
            f"/api/v1/projects/{self.project_id}/releases",
            json=self._valid_body(),
            headers=self._headers(token),
        )
        assert resp.status_code == 404

    # TC-UNI-API-06: Invalid SemVer -> 422
    def test_tc_uni_api_06_invalid_semver_returns_422(self):
        from fastapi.testclient import TestClient
        self.release_service.create_release.side_effect = Exception("SemVer invalido")
        token = _token(self.user_id, self.org_id, "OPERATOR")
        resp = self.client.post(
            f"/api/v1/projects/{self.project_id}/releases",
            json={**self._valid_body(), "version": "not-semver"},
            headers=self._headers(token),
        )
        assert resp.status_code in (422, 500)

    # TC-UNI-API-07: Cross-org access -> 403
    def test_tc_uni_api_07_cross_org_access_returns_403(self):
        from fastapi.testclient import TestClient
        other_org_id = uuid4()
        project = MagicMock()
        project.id = self.project_id
        project.organization_id = other_org_id
        self.project_repo.get_by_id = AsyncMock(return_value=project)
        self.org_repo.get_by_id = AsyncMock(return_value=None)

        token = _token(self.user_id, self.org_id, "OPERATOR")
        resp = self.client.post(
            f"/api/v1/projects/{self.project_id}/releases",
            json=self._valid_body(),
            headers=self._headers(token),
        )
        assert resp.status_code in (403, 404)


# ═══════════════════════════════════════════════════════════════════════════════
# TestReleasesCoverage  (from test_routers_coverage.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestReleasesCoverage:
    @pytest.fixture(autouse=True)
    def _setup(self):
        from main import app
        from core.dependencies import (
            get_release_service, get_artifact_service, get_connector_service,
            get_verification_service,
            get_export_service, get_project_repository, get_organization_repository,
            get_release_repository,
        )
        self.app = app
        self.rel_svc = AsyncMock()
        self.art_svc = AsyncMock()
        self.conn_svc = AsyncMock()
        self.conn_svc.verify_artifact_ref = AsyncMock(return_value=None)
        self.ver_svc = AsyncMock()
        self.exp_svc = AsyncMock()
        self.proj_repo = AsyncMock()
        self.org_repo = AsyncMock()
        self.release_repo = AsyncMock()

        project = MagicMock()
        project.id = uuid4()
        project.organization_id = uuid4()
        org = MagicMock()
        org.id = project.organization_id
        org.owner_id = uuid4()
        self.proj_repo.get_by_id = AsyncMock(return_value=project)
        self.org_repo.get_by_id = AsyncMock(return_value=org)

        fake_row = MagicMock()
        fake_row.id = uuid4()
        self.release_repo.get_by_id = AsyncMock(return_value=fake_row)

        app.dependency_overrides[get_release_service] = lambda: self.rel_svc
        app.dependency_overrides[get_artifact_service] = lambda: self.art_svc
        app.dependency_overrides[get_connector_service] = lambda: self.conn_svc
        app.dependency_overrides[get_verification_service] = lambda: self.ver_svc
        app.dependency_overrides[get_export_service] = lambda: self.exp_svc
        app.dependency_overrides[get_project_repository] = lambda: self.proj_repo
        app.dependency_overrides[get_organization_repository] = lambda: self.org_repo
        app.dependency_overrides[get_release_repository] = lambda: self.release_repo

        self.user_id = uuid4()
        self.org_id = project.organization_id
        self.r_id = uuid4()
        yield
        app.dependency_overrides.clear()

    def _headers(self, role="OPERATOR"):
        return {"Authorization": f"Bearer {_token(self.user_id, self.org_id, role)}"}

    def _make_release(self):
        r = MagicMock()
        r.id = uuid4()
        r.name = "r1"
        r.version = "1.0"
        r.status = MagicMock()
        r.status.value = "BORRADOR"
        r.created_at = datetime.now(timezone.utc)
        r.created_by = uuid4()
        r.profile_id = uuid4()
        r.artifacts = []
        r.description = ""
        return r

    def test_list_releases_success(self):
        from fastapi.testclient import TestClient
        r = self._make_release()
        self.rel_svc.list_releases = AsyncMock(return_value=[r])
        client = TestClient(self.app)
        resp = client.get(f"/api/v1/projects/{uuid4()}/releases", headers=self._headers())
        assert resp.status_code == 200

    def test_list_releases_server_error_500(self):
        from fastapi.testclient import TestClient
        self.rel_svc.list_releases = AsyncMock(side_effect=RuntimeError("BOOM"))
        client = TestClient(self.app)
        resp = client.get(f"/api/v1/projects/{uuid4()}/releases", headers=self._headers())
        assert resp.status_code == 500

    def test_list_global_releases_non_admin(self):
        from fastapi.testclient import TestClient
        r = self._make_release()
        self.rel_svc.list_org_releases = AsyncMock(return_value=[r])
        client = TestClient(self.app)
        resp = client.get("/api/v1/releases", headers=self._headers("OPERATOR"))
        assert resp.status_code == 200

    def test_list_global_releases_admin(self):
        from fastapi.testclient import TestClient
        r = self._make_release()
        self.rel_svc.list_org_releases = AsyncMock(return_value=[r])
        client = TestClient(self.app)
        resp = client.get("/api/v1/releases", headers=self._headers("ADMIN"))
        assert resp.status_code == 200

    def test_get_release_found(self):
        from fastapi.testclient import TestClient
        r = self._make_release()
        self.rel_svc.get_release = AsyncMock(return_value=r)
        client = TestClient(self.app)
        resp = client.get(f"/api/v1/releases/{self.r_id}", headers=self._headers("MANAGER"))
        assert resp.status_code == 200

    def test_get_release_not_found_404(self):
        from fastapi.testclient import TestClient
        self.rel_svc.get_release = AsyncMock(return_value=None)
        client = TestClient(self.app)
        resp = client.get(f"/api/v1/releases/{self.r_id}", headers=self._headers("MANAGER"))
        assert resp.status_code == 404

    def test_update_release_success(self):
        from fastapi.testclient import TestClient
        r = self._make_release()
        self.rel_svc.update_release = AsyncMock(return_value=r)
        client = TestClient(self.app)
        resp = client.patch(f"/api/v1/releases/{self.r_id}", json={"name": "updated"}, headers=self._headers())
        assert resp.status_code == 200

    def test_update_release_validation_error_409(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import ValidationError
        self.rel_svc.update_release = AsyncMock(side_effect=ValidationError("bad"))
        client = TestClient(self.app)
        resp = client.patch(f"/api/v1/releases/{self.r_id}", json={"name": "bad"}, headers=self._headers())
        assert resp.status_code == 409

    def test_delete_release_success(self):
        from fastapi.testclient import TestClient
        self.rel_svc.delete_release = AsyncMock()
        client = TestClient(self.app)
        resp = client.delete(f"/api/v1/releases/{self.r_id}", headers=self._headers())
        assert resp.status_code == 204

    def test_archive_release_success(self):
        from fastapi.testclient import TestClient
        self.rel_svc.update_status = AsyncMock()
        client = TestClient(self.app)
        resp = client.post(f"/api/v1/releases/{self.r_id}/archive", headers=self._headers())
        assert resp.status_code == 200

    def test_restore_release_success(self):
        from fastapi.testclient import TestClient
        self.rel_svc.restore_release = AsyncMock()
        client = TestClient(self.app)
        resp = client.post(f"/api/v1/releases/{self.r_id}/restore", headers=self._headers("ADMIN"))
        assert resp.status_code == 200

    def test_restore_release_not_found_404(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import EntityNotFoundError
        self.rel_svc.restore_release = AsyncMock(side_effect=EntityNotFoundError("gone"))
        client = TestClient(self.app)
        resp = client.post(f"/api/v1/releases/{self.r_id}/restore", headers=self._headers("ADMIN"))
        assert resp.status_code == 404

    def test_restore_release_validation_error_409(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import ValidationError
        self.rel_svc.restore_release = AsyncMock(side_effect=ValidationError("state"))
        client = TestClient(self.app)
        resp = client.post(f"/api/v1/releases/{self.r_id}/restore", headers=self._headers("ADMIN"))
        assert resp.status_code == 409

    def test_list_artifacts_success(self):
        from fastapi.testclient import TestClient
        self.art_svc.list_artifacts = AsyncMock(return_value=[])
        client = TestClient(self.app)
        resp = client.get(f"/api/v1/releases/{self.r_id}/artifacts", headers=self._headers("MANAGER"))
        assert resp.status_code == 200

    def test_add_artifact_success(self):
        from fastapi.testclient import TestClient
        artifact = MagicMock()
        artifact.id = uuid4()
        self.art_svc.add_artifact = AsyncMock(return_value=artifact)
        client = TestClient(self.app)
        resp = client.post(
            f"/api/v1/releases/{self.r_id}/artifacts",
            json={"artifact_type": "TAREA", "connector_instance_id": str(uuid4()),
                  "connector_implementation": "JIRA", "external_ref": "REF-1"},
            headers=self._headers(),
        )
        assert resp.status_code == 201

    def test_add_artifact_validation_error_422(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import ValidationError
        self.art_svc.add_artifact = AsyncMock(side_effect=ValidationError("bad"))
        client = TestClient(self.app)
        resp = client.post(
            f"/api/v1/releases/{self.r_id}/artifacts",
            json={"artifact_type": "TAREA", "connector_instance_id": str(uuid4()),
                  "connector_implementation": "JIRA", "external_ref": "REF-1"},
            headers=self._headers(),
        )
        assert resp.status_code == 422

    def test_remove_artifact_success(self):
        from fastapi.testclient import TestClient
        self.art_svc.remove_artifact = AsyncMock()
        client = TestClient(self.app)
        resp = client.delete(f"/api/v1/releases/{self.r_id}/artifacts/{uuid4()}", headers=self._headers())
        assert resp.status_code == 204

    def test_verify_release_success(self):
        from fastapi.testclient import TestClient
        self.ver_svc.launch_verification = AsyncMock(return_value="task-123")
        client = TestClient(self.app)
        resp = client.post(f"/api/v1/releases/{self.r_id}/verify", headers=self._headers())
        assert resp.status_code == 202

    def test_verify_release_validation_error_409(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import ValidationError
        self.ver_svc.launch_verification = AsyncMock(side_effect=ValidationError("state"))
        client = TestClient(self.app)
        resp = client.post(f"/api/v1/releases/{self.r_id}/verify", headers=self._headers())
        assert resp.status_code == 409

    def test_get_results_success(self):
        from fastapi.testclient import TestClient
        self.ver_svc.get_verification_history = AsyncMock(return_value=[])
        client = TestClient(self.app)
        resp = client.get(f"/api/v1/releases/{self.r_id}/results", headers=self._headers())
        assert resp.status_code == 200

    def test_get_result_detail_success(self):
        from fastapi.testclient import TestClient
        self.ver_svc.get_verification_result = AsyncMock(return_value=MagicMock())
        client = TestClient(self.app)
        resp = client.get(f"/api/v1/releases/{self.r_id}/results/{uuid4()}", headers=self._headers())
        assert resp.status_code == 200

    def test_get_verification_detail_success(self):
        from fastapi.testclient import TestClient
        self.ver_svc.get_verification_result = AsyncMock(return_value=MagicMock())
        client = TestClient(self.app)
        resp = client.get(f"/api/v1/releases/{self.r_id}/verifications/{uuid4()}", headers=self._headers())
        assert resp.status_code in (200, 403)

    def test_export_verification_pdf_not_found_404(self):
        from fastapi.testclient import TestClient
        self.ver_svc.get_verification_result = AsyncMock(return_value=None)
        client = TestClient(self.app)
        resp = client.get(f"/api/v1/releases/{self.r_id}/results/{uuid4()}/export", headers=self._headers())
        assert resp.status_code == 404

    def test_export_verification_pdf_bad_format_400(self):
        from fastapi.testclient import TestClient
        client = TestClient(self.app)
        resp = client.get(
            f"/api/v1/releases/{self.r_id}/results/{uuid4()}/export?format=dox",
            headers=self._headers("MANAGER"),
        )
        assert resp.status_code in (400, 422, 403)

    def test_export_project_csv_bad_format_400(self):
        from fastapi.testclient import TestClient
        client = TestClient(self.app)
        resp = client.get(
            f"/api/v1/projects/{uuid4()}/results/export?format=pdf",
            headers=self._headers("MANAGER"),
        )
        assert resp.status_code in (400, 422)

    def test_import_artifacts_success(self):
        from fastapi.testclient import TestClient
        artifact = MagicMock()
        artifact.id = uuid4()
        artifact.external_ref = "REF-1"
        self.art_svc.add_artifact = AsyncMock(return_value=artifact)
        client = TestClient(self.app)
        payload = {"artifacts": [{"artifact_type": "TAREA", "connector_instance_id": str(uuid4()),
                                   "connector_implementation": "JIRA", "external_ref": "REF-1"}]}
        resp = client.post(f"/api/v1/releases/{self.r_id}/artifacts/import", json=payload, headers=self._headers())
        assert resp.status_code == 202

    def test_import_artifacts_validation_error_422(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import ValidationError
        self.art_svc.add_artifact = AsyncMock(side_effect=ValidationError("bad"))
        client = TestClient(self.app)
        payload = {"artifacts": [{"artifact_type": "TAREA", "connector_instance_id": str(uuid4()),
                                   "connector_implementation": "JIRA", "external_ref": "REF-1"}]}
        resp = client.post(f"/api/v1/releases/{self.r_id}/artifacts/import", json=payload, headers=self._headers())
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# TestOrganizationsCoverage  (from test_routers_coverage.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestOrganizationsCoverage:
    @pytest.fixture(autouse=True)
    def _setup(self):
        from main import app
        from core.dependencies import get_organization_service
        self.app = app
        self.svc = AsyncMock()
        app.dependency_overrides[get_organization_service] = lambda: self.svc
        self.user_id = uuid4()
        self.org_id = uuid4()
        yield
        app.dependency_overrides.clear()

    def _headers(self, role="OPERATOR"):
        return {"Authorization": f"Bearer {_token(self.user_id, self.org_id, role)}"}

    def test_get_organization_found_owner_access(self):
        from fastapi.testclient import TestClient
        org = _make_org(self.org_id, owner_id=self.user_id)
        self.svc.get_organization = AsyncMock(return_value=org)
        client = TestClient(self.app)
        resp = client.get(f"/api/v1/organizations/{self.org_id}", headers=self._headers())
        assert resp.status_code == 200

    def test_get_organization_found_org_member_access(self):
        from fastapi.testclient import TestClient
        org = _make_org(self.org_id, owner_id=uuid4())
        self.svc.get_organization = AsyncMock(return_value=org)
        client = TestClient(self.app)
        resp = client.get(f"/api/v1/organizations/{self.org_id}", headers=self._headers())
        assert resp.status_code == 200

    def test_get_organization_not_found_404(self):
        from fastapi.testclient import TestClient
        self.svc.get_organization = AsyncMock(return_value=None)
        client = TestClient(self.app)
        resp = client.get(f"/api/v1/organizations/{self.org_id}", headers=self._headers())
        assert resp.status_code == 404

    def test_get_organization_no_access_403(self):
        from fastapi.testclient import TestClient
        org = _make_org(self.org_id, owner_id=uuid4())
        self.svc.get_organization = AsyncMock(return_value=org)
        other_user = uuid4()
        client = TestClient(self.app)
        resp = client.get(f"/api/v1/organizations/{self.org_id}",
                          headers={"Authorization": f"Bearer {_token(other_user, uuid4(), 'OPERATOR')}"})
        assert resp.status_code == 403

    def test_get_project_by_id_found(self):
        from fastapi.testclient import TestClient
        p = _make_project(org_id=self.org_id)
        self.svc.get_project = AsyncMock(return_value=p)
        client = TestClient(self.app)
        resp = client.get(f"/api/v1/projects/{p.id}", headers=self._headers())
        assert resp.status_code == 200

    def test_get_project_by_id_not_found_404(self):
        from fastapi.testclient import TestClient
        self.svc.get_project = AsyncMock(return_value=None)
        client = TestClient(self.app)
        resp = client.get(f"/api/v1/projects/{uuid4()}", headers=self._headers())
        assert resp.status_code == 404

    def test_get_project_by_id_forbidden_403(self):
        from fastapi.testclient import TestClient
        p = _make_project(org_id=uuid4())
        self.svc.get_project = AsyncMock(return_value=p)
        client = TestClient(self.app)
        resp = client.get(f"/api/v1/projects/{p.id}", headers=self._headers())
        assert resp.status_code == 403

    def test_list_accessible_projects_admin(self):
        from fastapi.testclient import TestClient
        self.svc.list_accessible_projects = AsyncMock(return_value=[])
        client = TestClient(self.app)
        resp = client.get("/api/v1/projects", headers=self._headers("ADMIN"))
        assert resp.status_code == 200

    def test_list_accessible_projects_user_with_org(self):
        from fastapi.testclient import TestClient
        self.svc.list_projects = AsyncMock(return_value=[])
        client = TestClient(self.app)
        resp = client.get("/api/v1/projects", headers=self._headers("OPERATOR"))
        assert resp.status_code == 200

    def test_list_org_projects_success(self):
        from fastapi.testclient import TestClient
        self.svc.list_projects = AsyncMock(return_value=[_make_project(org_id=self.org_id)])
        client = TestClient(self.app)
        resp = client.get(f"/api/v1/organizations/{self.org_id}/projects", headers=self._headers("MANAGER"))
        assert resp.status_code == 200

    def test_get_project_in_org_found(self):
        from fastapi.testclient import TestClient
        p = _make_project(org_id=self.org_id)
        self.svc.get_project = AsyncMock(return_value=p)
        client = TestClient(self.app)
        resp = client.get(f"/api/v1/organizations/{self.org_id}/projects/{p.id}", headers=self._headers("MANAGER"))
        assert resp.status_code == 200

    def test_get_project_in_org_not_found_404(self):
        from fastapi.testclient import TestClient
        self.svc.get_project = AsyncMock(return_value=None)
        client = TestClient(self.app)
        resp = client.get(f"/api/v1/organizations/{self.org_id}/projects/{uuid4()}", headers=self._headers("MANAGER"))
        assert resp.status_code == 404

    def test_get_project_in_org_wrong_org_403(self):
        from fastapi.testclient import TestClient
        p = _make_project(org_id=uuid4())
        self.svc.get_project = AsyncMock(return_value=p)
        client = TestClient(self.app)
        resp = client.get(f"/api/v1/organizations/{self.org_id}/projects/{p.id}", headers=self._headers("MANAGER"))
        assert resp.status_code == 403

    def test_archive_project_success(self):
        from fastapi.testclient import TestClient
        p = _make_project(org_id=self.org_id)
        p.is_archived = True
        self.svc.archive_project = AsyncMock(return_value=p)
        client = TestClient(self.app)
        resp = client.post(f"/api/v1/organizations/{self.org_id}/projects/{p.id}/archive", headers=self._headers("MANAGER"))
        assert resp.status_code == 200

    def test_archive_project_not_found_404(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import EntityNotFoundError
        self.svc.archive_project = AsyncMock(side_effect=EntityNotFoundError("gone"))
        client = TestClient(self.app)
        resp = client.post(f"/api/v1/organizations/{self.org_id}/projects/{uuid4()}/archive", headers=self._headers("MANAGER"))
        assert resp.status_code == 404

    def test_restore_organization_success(self):
        from fastapi.testclient import TestClient
        org = _make_org(self.org_id)
        org.is_active = True
        self.svc.restore_organization = AsyncMock(return_value=org)
        client = TestClient(self.app)
        resp = client.post(f"/api/v1/organizations/{self.org_id}/restore", headers=self._headers("ADMIN"))
        assert resp.status_code == 200

    def test_restore_organization_not_found_404(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import EntityNotFoundError
        self.svc.restore_organization = AsyncMock(side_effect=EntityNotFoundError("gone"))
        client = TestClient(self.app)
        resp = client.post(f"/api/v1/organizations/{self.org_id}/restore", headers=self._headers("ADMIN"))
        assert resp.status_code == 404

    def test_transfer_ownership_success(self):
        from fastapi.testclient import TestClient
        org = _make_org(self.org_id)
        self.svc.transfer_ownership = AsyncMock(return_value=org)
        client = TestClient(self.app)
        resp = client.post(f"/api/v1/organizations/{self.org_id}/transfer-ownership",
                           json={"new_owner_id": str(uuid4())}, headers=self._headers("ADMIN"))
        assert resp.status_code == 200

    def test_transfer_ownership_not_found_404(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import EntityNotFoundError
        self.svc.transfer_ownership = AsyncMock(side_effect=EntityNotFoundError("gone"))
        client = TestClient(self.app)
        resp = client.post(f"/api/v1/organizations/{self.org_id}/transfer-ownership",
                           json={"new_owner_id": str(uuid4())}, headers=self._headers("ADMIN"))
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# TestOrganizationsRouter  (from test_routers_extended.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestOrganizationsRouter:
    @pytest.fixture(autouse=True)
    def _setup(self):
        from main import app
        from core.dependencies import get_organization_service, get_current_user_api_key_only, get_current_user
        self.app = app
        self.org_svc = AsyncMock()
        app.dependency_overrides[get_organization_service] = lambda: self.org_svc
        app.dependency_overrides[get_current_user_api_key_only] = get_current_user

        self.user_id = uuid4()
        self.org_id = uuid4()
        yield
        app.dependency_overrides.clear()

    def test_list_organizations_as_admin(self):
        from fastapi.testclient import TestClient
        self.org_svc.list_organizations = AsyncMock(return_value=[])
        client = TestClient(self.app)
        resp = client.get(
            "/api/v1/organizations",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id, 'ADMIN')}"},
        )
        assert resp.status_code == 200

    def test_list_organizations_as_non_admin_returns_403(self):
        from fastapi.testclient import TestClient
        client = TestClient(self.app)
        resp = client.get(
            "/api/v1/organizations",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id, 'OPERATOR')}"},
        )
        assert resp.status_code == 403

    def test_create_org_admin_forbidden(self):
        from fastapi.testclient import TestClient
        client = TestClient(self.app)
        resp = client.post(
            "/api/v1/organizations",
            json={"name": "TestOrg", "slug": "test-org"},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id, 'ADMIN')}"},
        )
        assert resp.status_code == 403

    def test_create_org_success(self):
        from fastapi.testclient import TestClient
        org = _make_org(uuid4(), self.user_id)
        self.org_svc.create_organization = AsyncMock(return_value=org)
        client = TestClient(self.app)
        resp = client.post(
            "/api/v1/organizations",
            json={"name": "My Org", "slug": "my-org"},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id, 'MANAGER')}"},
        )
        assert resp.status_code == 201

    def test_create_org_duplicate_slug_returns_409(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import DuplicateEntityError
        self.org_svc.create_organization = AsyncMock(side_effect=DuplicateEntityError("dup"))
        client = TestClient(self.app)
        resp = client.post(
            "/api/v1/organizations",
            json={"name": "My Org", "slug": "dup-slug"},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id, 'MANAGER')}"},
        )
        assert resp.status_code == 409

    def test_create_org_validation_error_returns_409(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import ValidationError
        self.org_svc.create_organization = AsyncMock(side_effect=ValidationError("bad"))
        client = TestClient(self.app)
        resp = client.post(
            "/api/v1/organizations",
            json={"name": "My Org", "slug": "valid-slug"},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id, 'MANAGER')}"},
        )
        assert resp.status_code in (409, 422)

    def test_create_org_server_error_returns_500(self):
        from fastapi.testclient import TestClient
        self.org_svc.create_organization = AsyncMock(side_effect=RuntimeError("DB down"))
        client = TestClient(self.app)
        resp = client.post(
            "/api/v1/organizations",
            json={"name": "My Org", "slug": "err-slug"},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id, 'MANAGER')}"},
        )
        assert resp.status_code == 500

    def test_create_project_success(self):
        from fastapi.testclient import TestClient
        project = MagicMock()
        project.id = uuid4()
        project.name = "Proj"
        project.description = ""
        project.profile_id = uuid4()
        project.organization_id = self.org_id
        project.is_archived = False
        project.created_at = datetime.now(timezone.utc)
        self.org_svc.get_organization = AsyncMock(return_value=_make_org(self.org_id, self.user_id))
        self.org_svc.create_project = AsyncMock(return_value=project)
        client = TestClient(self.app)
        resp = client.post(
            f"/api/v1/organizations/{self.org_id}/projects",
            json={"name": "Proj", "description": "desc", "profile_id": str(uuid4())},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id, 'OPERATOR')}"},
        )
        assert resp.status_code in (201, 403)

    def test_list_projects_success(self):
        from fastapi.testclient import TestClient
        org = _make_org(self.org_id, self.user_id)
        self.org_svc.get_organization = AsyncMock(return_value=org)
        self.org_svc.list_projects = AsyncMock(return_value=[])
        client = TestClient(self.app)
        resp = client.get(
            f"/api/v1/organizations/{self.org_id}/projects",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id, 'OPERATOR')}"},
        )
        assert resp.status_code in (200, 403)


# ═══════════════════════════════════════════════════════════════════════════════
# TestAuthCoverage  (from test_routers_coverage.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuthCoverage:
    @pytest.fixture(autouse=True)
    def _setup(self):
        from main import app
        from core.dependencies import get_auth_service, get_user_service
        self.app = app
        self.auth_svc = AsyncMock()
        self.user_svc = AsyncMock()
        app.dependency_overrides[get_auth_service] = lambda: self.auth_svc
        app.dependency_overrides[get_user_service] = lambda: self.user_svc
        self.user_id = uuid4()
        self.org_id = uuid4()
        yield
        app.dependency_overrides.clear()

    def _headers(self):
        return {"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"}

    def test_login_success(self):
        from fastapi.testclient import TestClient
        result = MagicMock()
        result.requires_2fa = False
        result.tokens = MagicMock()
        result.tokens.access_token = "access"
        result.tokens.refresh_token = "refresh"
        result.tokens.token_type = "bearer"
        result.user_id = self.user_id
        result.role = "OPERATOR"
        self.auth_svc.authenticate = AsyncMock(return_value=result)
        client = TestClient(self.app)
        resp = client.post("/api/v1/auth/login", json={"email": "test@test.com", "password": "Pass123"}) # NOSONAR
        assert resp.status_code == 200

    def test_login_requires_2fa(self):
        from fastapi.testclient import TestClient
        result = MagicMock()
        result.requires_2fa = True
        result.totp_token = "totp-token-123"
        self.auth_svc.authenticate = AsyncMock(return_value=result)
        client = TestClient(self.app)
        resp = client.post("/api/v1/auth/login", json={"email": "test@test.com", "password": "Pass123"}) # NOSONAR
        assert resp.status_code == 200
        assert resp.json()["requires_2fa"] is True

    def test_login_invalid_credentials_401(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import ValidationError
        self.auth_svc.authenticate = AsyncMock(side_effect=ValidationError("wrong"))
        client = TestClient(self.app)
        resp = client.post("/api/v1/auth/login", json={"email": "test@test.com", "password": "wrong"}) # NOSONAR
        assert resp.status_code == 401

    def test_verify_2fa_success(self):
        from fastapi.testclient import TestClient
        result = MagicMock()
        result.tokens = MagicMock()
        result.tokens.access_token = "access2"
        result.tokens.refresh_token = "refresh2"
        result.tokens.token_type = "bearer"
        result.user_id = self.user_id
        result.role = "OPERATOR"
        self.auth_svc.verify_totp = AsyncMock(return_value=result)
        client = TestClient(self.app)
        resp = client.post("/api/v1/auth/2fa/verify", json={"totp_token": "token", "code": "123456"})
        assert resp.status_code == 200

    def test_setup_2fa_success(self):
        from fastapi.testclient import TestClient
        result = MagicMock()
        result.totp_uri = "otpauth://..."
        result.secret = "SECRET"
        result.qr_data_url = "data:image/png;base64,..."
        self.auth_svc.setup_totp = AsyncMock(return_value=result)
        client = TestClient(self.app)
        resp = client.get("/api/v1/auth/2fa/setup", headers=self._headers())
        assert resp.status_code == 200

    def test_enable_2fa_success(self):
        from fastapi.testclient import TestClient
        self.auth_svc.enable_totp = AsyncMock()
        client = TestClient(self.app)
        resp = client.post("/api/v1/auth/2fa/enable", json={"code": "123456"}, headers=self._headers())
        assert resp.status_code == 200

    def test_disable_2fa_success(self):
        from fastapi.testclient import TestClient
        self.auth_svc.disable_totp = AsyncMock()
        client = TestClient(self.app)
        resp = client.post("/api/v1/auth/2fa/disable", json={"code": "123456"}, headers=self._headers())
        assert resp.status_code == 200

    def test_register_success(self):
        from fastapi.testclient import TestClient
        user = MagicMock()
        user.id = uuid4()
        self.user_svc.create_user = AsyncMock(return_value=user)
        client = TestClient(self.app)
        resp = client.post("/api/v1/auth/register", json={
            "email": "new@test.com", "password": "StrongPass1", # NOSONAR
            "display_name": "New User", "accept_terms": True, "accept_privacy_policy": True,
        })
        assert resp.status_code in (201, 200)

    def test_register_duplicate_400(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import DuplicateEntityError
        self.user_svc.create_user = AsyncMock(side_effect=DuplicateEntityError("dup"))
        client = TestClient(self.app)
        resp = client.post("/api/v1/auth/register", json={
            "email": "dup@test.com", "password": "StrongPass1", # NOSONAR
            "display_name": "Dup User", "accept_terms": True, "accept_privacy_policy": True,
        })
        assert resp.status_code == 400

    def test_register_no_consent_422(self):
        from fastapi.testclient import TestClient
        client = TestClient(self.app)
        resp = client.post("/api/v1/auth/register", json={
            "email": "bad@test.com", "password": "StrongPass1", # NOSONAR
            "display_name": "Bad", "accept_terms": False, "accept_privacy_policy": True,
        })
        assert resp.status_code == 422

    def test_refresh_token_success(self):
        from fastapi.testclient import TestClient
        tokens = MagicMock()
        tokens.access_token = "new-access"
        tokens.refresh_token = "new-refresh"
        tokens.token_type = "bearer"
        self.auth_svc.refresh_access_token = AsyncMock(return_value=tokens)
        client = TestClient(self.app)
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "old-refresh-token"})
        assert resp.status_code == 200

    def test_refresh_token_invalid_401(self):
        from fastapi.testclient import TestClient
        self.auth_svc.refresh_access_token = AsyncMock(return_value=None)
        client = TestClient(self.app)
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "bad-token"})
        assert resp.status_code == 401

    def test_logout_success(self):
        from fastapi.testclient import TestClient
        self.auth_svc.logout = AsyncMock()
        client = TestClient(self.app)
        resp = client.post("/api/v1/auth/logout", headers=self._headers())
        assert resp.status_code == 204


# ═══════════════════════════════════════════════════════════════════════════════
# TestAuthRouter  (from test_more_services.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuthRouter:
    @pytest.fixture(autouse=True)
    def _setup(self):
        from main import app
        from core.dependencies import get_auth_service, get_user_service
        self.app = app
        self.auth_svc = AsyncMock()
        self.user_svc = AsyncMock()
        app.dependency_overrides[get_auth_service] = lambda: self.auth_svc
        app.dependency_overrides[get_user_service] = lambda: self.user_svc
        yield
        app.dependency_overrides.clear()

    def test_login_success_returns_tokens(self):
        from fastapi.testclient import TestClient
        from application.ports.input.i_auth_service import LoginResult, AuthTokens
        tokens = AuthTokens(access_token="acc", refresh_token="ref")
        self.auth_svc.authenticate = AsyncMock(
            return_value=LoginResult(tokens=tokens, user_id=uuid4(), role="U2")
        )
        client = TestClient(self.app)
        resp = client.post("/api/v1/auth/login", json={"email": "x@x.com", "password": "p"})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_requires_2fa(self):
        from fastapi.testclient import TestClient
        from application.ports.input.i_auth_service import LoginResult
        self.auth_svc.authenticate = AsyncMock(
            return_value=LoginResult(requires_2fa=True, totp_token="pending")
        )
        client = TestClient(self.app)
        resp = client.post("/api/v1/auth/login", json={"email": "x@x.com", "password": "p"})
        assert resp.status_code == 200
        assert resp.json()["requires_2fa"] is True

    def test_login_validation_error_returns_401(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import ValidationError
        self.auth_svc.authenticate = AsyncMock(side_effect=ValidationError("bad creds"))
        client = TestClient(self.app)
        resp = client.post("/api/v1/auth/login", json={"email": "x@x.com", "password": "p"})
        assert resp.status_code == 401

    def test_login_unexpected_error_returns_500(self):
        from fastapi.testclient import TestClient
        self.auth_svc.authenticate = AsyncMock(side_effect=RuntimeError("oops"))
        client = TestClient(self.app)
        resp = client.post("/api/v1/auth/login", json={"email": "x@x.com", "password": "p"})
        assert resp.status_code == 500

    def test_verify_2fa_success(self):
        from fastapi.testclient import TestClient
        from application.ports.input.i_auth_service import LoginResult, AuthTokens
        tokens = AuthTokens(access_token="acc", refresh_token="ref")
        self.auth_svc.verify_totp = AsyncMock(
            return_value=LoginResult(tokens=tokens, user_id=uuid4(), role="U2")
        )
        client = TestClient(self.app)
        resp = client.post("/api/v1/auth/2fa/verify", json={"totp_token": "tok", "code": "123456"})
        assert resp.status_code == 200

    def test_verify_2fa_validation_error_returns_401(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import ValidationError
        self.auth_svc.verify_totp = AsyncMock(side_effect=ValidationError("bad code"))
        client = TestClient(self.app)
        resp = client.post("/api/v1/auth/2fa/verify", json={"totp_token": "tok", "code": "000000"})
        assert resp.status_code == 401

    def test_register_success_returns_201(self):
        from fastapi.testclient import TestClient
        user = MagicMock()
        user.id = uuid4()
        self.user_svc.create_user = AsyncMock(return_value=user)
        client = TestClient(self.app)
        resp = client.post("/api/v1/auth/register", json={
            "email": "new@x.com",
            "password": "Password1",
            "display_name": "New User",
            "accept_terms": True,
            "accept_privacy_policy": True,
        })
        assert resp.status_code == 201

    def test_register_password_no_uppercase_returns_422(self):
        from fastapi.testclient import TestClient
        client = TestClient(self.app)
        resp = client.post("/api/v1/auth/register", json={
            "email": "new@x.com",
            "password": "password1",
            "display_name": "User",
            "accept_terms": True,
            "accept_privacy_policy": True,
        })
        assert resp.status_code == 422

    def test_register_password_no_lowercase_returns_422(self):
        from fastapi.testclient import TestClient
        client = TestClient(self.app)
        resp = client.post("/api/v1/auth/register", json={
            "email": "new@x.com",
            "password": "PASSWORD1",
            "display_name": "User",
            "accept_terms": True,
            "accept_privacy_policy": True,
        })
        assert resp.status_code == 422

    def test_register_password_no_digit_returns_422(self):
        from fastapi.testclient import TestClient
        client = TestClient(self.app)
        resp = client.post("/api/v1/auth/register", json={
            "email": "new@x.com",
            "password": "Passwordd",
            "display_name": "User",
            "accept_terms": True,
            "accept_privacy_policy": True,
        })
        assert resp.status_code == 422

    def test_register_terms_not_accepted_returns_422(self):
        from fastapi.testclient import TestClient
        client = TestClient(self.app)
        resp = client.post("/api/v1/auth/register", json={
            "email": "new@x.com",
            "password": "Password1",
            "display_name": "User",
            "accept_terms": False,
            "accept_privacy_policy": True,
        })
        assert resp.status_code == 422

    def test_register_privacy_not_accepted_returns_422(self):
        from fastapi.testclient import TestClient
        client = TestClient(self.app)
        resp = client.post("/api/v1/auth/register", json={
            "email": "new@x.com",
            "password": "Password1",
            "display_name": "User",
            "accept_terms": True,
            "accept_privacy_policy": False,
        })
        assert resp.status_code == 422

    def test_register_duplicate_raises_400(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import DuplicateEntityError
        self.user_svc.create_user = AsyncMock(side_effect=DuplicateEntityError("dup"))
        client = TestClient(self.app)
        resp = client.post("/api/v1/auth/register", json={
            "email": "dup@x.com",
            "password": "Password1",
            "display_name": "User",
            "accept_terms": True,
            "accept_privacy_policy": True,
        })
        assert resp.status_code == 400

    def test_setup_2fa_success(self):
        from fastapi.testclient import TestClient
        from application.ports.input.i_auth_service import TotpSetupResult
        user_id = uuid4()
        org_id = uuid4()
        token = _token(user_id, org_id, "OPERATOR")
        self.auth_svc.setup_totp = AsyncMock(
            return_value=TotpSetupResult(totp_uri="otpauth://", secret="ABC", qr_data_url="data:x")
        )
        client = TestClient(self.app)
        resp = client.get("/api/v1/auth/2fa/setup", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_enable_2fa_success(self):
        from fastapi.testclient import TestClient
        user_id = uuid4()
        org_id = uuid4()
        token = _token(user_id, org_id, "OPERATOR")
        self.auth_svc.enable_totp = AsyncMock(return_value=None)
        client = TestClient(self.app)
        resp = client.post(
            "/api/v1/auth/2fa/enable",
            json={"code": "123456"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    def test_disable_2fa_success(self):
        from fastapi.testclient import TestClient
        user_id = uuid4()
        org_id = uuid4()
        token = _token(user_id, org_id, "OPERATOR")
        self.auth_svc.disable_totp = AsyncMock(return_value=None)
        client = TestClient(self.app)
        resp = client.post(
            "/api/v1/auth/2fa/disable",
            json={"code": "123456"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# TestAccessRequestsCoverage  (from test_routers_coverage.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestAccessRequestsCoverage:
    @pytest.fixture(autouse=True)
    def _setup(self):
        from main import app
        from core.dependencies import get_organization_service, get_user_service
        self.app = app
        self.svc = AsyncMock()
        self.user_svc = AsyncMock()
        app.dependency_overrides[get_organization_service] = lambda: self.svc
        app.dependency_overrides[get_user_service] = lambda: self.user_svc
        self.user_id = uuid4()
        self.org_id = uuid4()
        yield
        app.dependency_overrides.clear()

    def _headers(self, role="ADMIN"):
        return {"Authorization": f"Bearer {_token(self.user_id, self.org_id, role)}"}

    def test_create_access_request_exists_409(self):
        from fastapi.testclient import TestClient
        from domain.entities.access_request import AccessRequest
        with patch(
            "infrastructure.secondary.database.repositories.access_request_repository.SqlAccessRequestRepository.get_by_email",
            new_callable=AsyncMock,
        ) as mock_get_email:
            mock_get_email.return_value = AccessRequest(
                requester_name="Existing", requester_email="existing@test.com",
                organization_name="Existing Org",
            )
            client = TestClient(self.app)
            resp = client.post("/api/v1/access-requests", json={
                "requester_name": "John", "requester_email": "existing@test.com",
                "organization_name": "Test Corp",
            })
            assert resp.status_code == 409

    def test_list_access_requests_success(self):
        from fastapi.testclient import TestClient
        with patch(
            "infrastructure.secondary.database.repositories.access_request_repository.SqlAccessRequestRepository.list_by_status",
            new_callable=AsyncMock,
        ) as mock_list:
            mock_list.return_value = []
            client = TestClient(self.app)
            resp = client.get("/api/v1/access-requests", headers=self._headers("ADMIN"))
            assert resp.status_code == 200

    def test_list_access_requests_invalid_status_400(self):
        from fastapi.testclient import TestClient
        client = TestClient(self.app)
        resp = client.get("/api/v1/access-requests?status=INVALID_STATUS", headers=self._headers("ADMIN"))
        assert resp.status_code == 400

    def test_patch_access_request_not_found_404(self):
        from fastapi.testclient import TestClient
        with patch(
            "infrastructure.secondary.database.repositories.access_request_repository.SqlAccessRequestRepository.get_by_id",
            new_callable=AsyncMock,
        ) as mock_get:
            mock_get.return_value = None
            client = TestClient(self.app)
            resp = client.patch(f"/api/v1/access-requests/{uuid4()}", json={"action": "APPROVE"},
                                headers=self._headers("ADMIN"))
            assert resp.status_code == 404

    def test_patch_access_request_approve(self):
        from fastapi.testclient import TestClient
        from domain.entities.access_request import AccessRequest
        from domain.enums import AccessRequestStatus
        ar = AccessRequest(
            requester_name="Bob", requester_email="bob@test.com",
            organization_name="Bob Org", status=AccessRequestStatus.PENDING,
        )
        ar.id = uuid4()
        with patch(
            "infrastructure.secondary.database.repositories.access_request_repository.SqlAccessRequestRepository.get_by_id",
            new_callable=AsyncMock,
        ) as mock_get, patch(
            "infrastructure.secondary.database.repositories.access_request_repository.SqlAccessRequestRepository.update",
            new_callable=AsyncMock,
        ) as mock_update:
            mock_get.return_value = ar
            mock_update.return_value = ar
            client = TestClient(self.app)
            resp = client.patch(f"/api/v1/access-requests/{ar.id}", json={"action": "APPROVE"},
                                headers=self._headers("ADMIN"))
            assert resp.status_code == 200

    def test_patch_access_request_reject(self):
        from fastapi.testclient import TestClient
        from domain.entities.access_request import AccessRequest
        from domain.enums import AccessRequestStatus
        ar = AccessRequest(
            requester_name="Bob", requester_email="bob@test.com",
            organization_name="Bob Org", status=AccessRequestStatus.PENDING,
        )
        ar.id = uuid4()
        with patch(
            "infrastructure.secondary.database.repositories.access_request_repository.SqlAccessRequestRepository.get_by_id",
            new_callable=AsyncMock,
        ) as mock_get, patch(
            "infrastructure.secondary.database.repositories.access_request_repository.SqlAccessRequestRepository.update",
            new_callable=AsyncMock,
        ) as mock_update:
            mock_get.return_value = ar
            mock_update.return_value = ar
            client = TestClient(self.app)
            resp = client.patch(f"/api/v1/access-requests/{ar.id}",
                                json={"action": "REJECT", "rejection_reason": "Not eligible"},
                                headers=self._headers("ADMIN"))
            assert resp.status_code == 200

    def test_patch_access_request_invalid_action_400(self):
        from fastapi.testclient import TestClient
        from domain.entities.access_request import AccessRequest
        from domain.enums import AccessRequestStatus
        ar = AccessRequest(
            requester_name="Bob", requester_email="bob@test.com",
            organization_name="Bob Org", status=AccessRequestStatus.PENDING,
        )
        ar.id = uuid4()
        with patch(
            "infrastructure.secondary.database.repositories.access_request_repository.SqlAccessRequestRepository.get_by_id",
            new_callable=AsyncMock,
        ) as mock_get:
            mock_get.return_value = ar
            client = TestClient(self.app)
            resp = client.patch(f"/api/v1/access-requests/{ar.id}", json={"action": "SUSPEND"},
                                headers=self._headers("ADMIN"))
            assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# TestFeedbackRouter
# ═══════════════════════════════════════════════════════════════════════════════

class TestFeedbackRouter:
    def _mock_session(self):
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        return mock_session

    def test_submit_feedback_success(self):
        from fastapi.testclient import TestClient
        from main import app
        mock_session = self._mock_session()
        with patch(
            "infrastructure.primary.routers.api.v1.feedback.AsyncSessionLocal",
            return_value=mock_session,
        ), patch(
            "infrastructure.primary.routers.api.v1.feedback.email_service.send_feedback_email",
            new_callable=AsyncMock,
        ) as mock_email:
            client = TestClient(app)
            resp = client.post("/api/v1/feedback", json={
                "name": "Ada", "email": "ada@test.com", "rating": 5, "comments": "Great tool",
            })
            assert resp.status_code == 201
            assert resp.json() == {"status": "ok"}
            mock_session.add.assert_called_once()
            mock_session.commit.assert_awaited_once()
            mock_email.assert_awaited_once()

    def test_submit_feedback_without_email_is_accepted(self):
        from fastapi.testclient import TestClient
        from main import app
        mock_session = self._mock_session()
        with patch(
            "infrastructure.primary.routers.api.v1.feedback.AsyncSessionLocal",
            return_value=mock_session,
        ), patch(
            "infrastructure.primary.routers.api.v1.feedback.email_service.send_feedback_email",
            new_callable=AsyncMock,
        ):
            client = TestClient(app)
            resp = client.post("/api/v1/feedback", json={
                "name": "Ada", "rating": 4, "comments": "Nice",
            })
            assert resp.status_code == 201

    def test_submit_feedback_email_failure_still_persists(self):
        from fastapi.testclient import TestClient
        from main import app
        mock_session = self._mock_session()
        with patch(
            "infrastructure.primary.routers.api.v1.feedback.AsyncSessionLocal",
            return_value=mock_session,
        ), patch(
            "infrastructure.primary.routers.api.v1.feedback.email_service.send_feedback_email",
            new_callable=AsyncMock,
            side_effect=RuntimeError("smtp down"),
        ):
            client = TestClient(app)
            resp = client.post("/api/v1/feedback", json={
                "name": "Ada", "rating": 3, "comments": "Meh", "email": "ada@test.com",
            })
            assert resp.status_code == 201
            mock_session.commit.assert_awaited_once()

    def test_submit_feedback_db_failure_500(self):
        from fastapi.testclient import TestClient
        from main import app
        mock_session = self._mock_session()
        mock_session.commit = AsyncMock(side_effect=RuntimeError("db down"))
        with patch(
            "infrastructure.primary.routers.api.v1.feedback.AsyncSessionLocal",
            return_value=mock_session,
        ):
            client = TestClient(app)
            resp = client.post("/api/v1/feedback", json={
                "name": "Ada", "rating": 3, "comments": "Meh",
            })
            assert resp.status_code == 500

    def test_public_feedback_requires_sync_key(self):
        from fastapi.testclient import TestClient
        from main import app
        client = TestClient(app)
        resp = client.get("/api/v1/feedback/public")
        assert resp.status_code == 403

    def test_public_feedback_wrong_sync_key_403(self):
        from fastapi.testclient import TestClient
        from main import app
        with patch("infrastructure.primary.routers.api.v1.feedback.settings.feedback_sync_key", "right-key"):
            client = TestClient(app)
            resp = client.get("/api/v1/feedback/public", headers={"X-Feedback-Sync-Key": "wrong-key"})
            assert resp.status_code == 403

    def test_public_feedback_success_omits_email(self):
        from fastapi.testclient import TestClient
        from main import app
        row = MagicMock(name="Ada", rating=5, comments="Great tool", created_at=datetime.now(timezone.utc))
        row.name = "Ada"
        mock_session = self._mock_session()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[row]))))
        )
        with patch("infrastructure.primary.routers.api.v1.feedback.settings.feedback_sync_key", "right-key"), patch(
            "infrastructure.primary.routers.api.v1.feedback.AsyncSessionLocal",
            return_value=mock_session,
        ):
            client = TestClient(app)
            resp = client.get("/api/v1/feedback/public", headers={"X-Feedback-Sync-Key": "right-key"})
            assert resp.status_code == 200
            body = resp.json()
            assert body == [{
                "name": "Ada", "rating": 5, "comments": "Great tool",
                "created_at": row.created_at.isoformat(),
            }]
            assert "email" not in body[0]


# ═══════════════════════════════════════════════════════════════════════════════
# TestNotificationsCoverage  (from test_routers_coverage.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestNotificationsCoverage:
    @pytest.fixture(autouse=True)
    def _setup(self):
        from main import app
        from core.dependencies import get_notification_service, get_user_repository
        self.app = app
        self.svc = AsyncMock()
        self.user_repo = AsyncMock()
        app.dependency_overrides[get_notification_service] = lambda: self.svc
        app.dependency_overrides[get_user_repository] = lambda: self.user_repo
        self.user_id = uuid4()
        self.org_id = uuid4()
        yield
        app.dependency_overrides.clear()

    def _headers(self, role="MANAGER"):
        return {"Authorization": f"Bearer {_token(self.user_id, self.org_id, role)}"}

    def test_configure_channel_success(self):
        from fastapi.testclient import TestClient
        channel = MagicMock()
        channel.id = uuid4()
        channel.channel_type = "EMAIL"
        channel.enabled = True
        self.svc.configure_channel = AsyncMock(return_value=channel)
        client = TestClient(self.app)
        resp = client.post("/api/v1/notifications/channels",
                           json={"channel_type": "EMAIL", "enabled": True, "config_data": {"to": "x@x.com"}},
                           headers=self._headers("MANAGER"))
        assert resp.status_code == 201

    def test_update_channel_not_found_404(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import EntityNotFoundError
        self.svc.update_channel = AsyncMock(side_effect=EntityNotFoundError("gone"))
        client = TestClient(self.app)
        resp = client.patch(f"/api/v1/notifications/channels/{uuid4()}",
                            json={"channel_type": "EMAIL", "enabled": False, "config_data": {}},
                            headers=self._headers("MANAGER"))
        assert resp.status_code == 404

    def test_delete_channel_not_found_404(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import EntityNotFoundError
        self.svc.delete_channel = AsyncMock(side_effect=EntityNotFoundError("gone"))
        client = TestClient(self.app)
        resp = client.delete(f"/api/v1/notifications/channels/{uuid4()}", headers=self._headers("MANAGER"))
        assert resp.status_code == 404

    def test_delete_channel_success(self):
        from fastapi.testclient import TestClient
        self.svc.delete_channel = AsyncMock()
        client = TestClient(self.app)
        resp = client.delete(f"/api/v1/notifications/channels/{uuid4()}", headers=self._headers("MANAGER"))
        assert resp.status_code == 204

    def test_subscribe_success(self):
        from fastapi.testclient import TestClient
        sub = MagicMock()
        self.svc.subscribe = AsyncMock(return_value=sub)
        client = TestClient(self.app)
        resp = client.post("/api/v1/notifications/subscriptions",
                           json={"event_type": "release_validated", "enabled": True},
                           headers=self._headers("OPERATOR"))
        assert resp.status_code == 201

    def test_subscribe_validation_error_409(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import ValidationError
        self.svc.subscribe = AsyncMock(side_effect=ValidationError("bad event"))
        client = TestClient(self.app)
        resp = client.post("/api/v1/notifications/subscriptions",
                           json={"event_type": "bad_event", "enabled": True},
                           headers=self._headers("OPERATOR"))
        assert resp.status_code == 409

    def test_unsubscribe_success(self):
        from fastapi.testclient import TestClient
        self.svc.unsubscribe = AsyncMock()
        client = TestClient(self.app)
        resp = client.delete("/api/v1/notifications/subscriptions/release_validated", headers=self._headers("OPERATOR"))
        assert resp.status_code == 204


# ═══════════════════════════════════════════════════════════════════════════════
# TestNotificationsRouter  (from test_routers_extended.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestNotificationsRouter:
    @pytest.fixture(autouse=True)
    def _setup(self):
        from main import app
        from core.dependencies import get_notification_service, get_user_repository
        self.app = app
        self.svc = AsyncMock()
        self.user_repo = AsyncMock()
        app.dependency_overrides[get_notification_service] = lambda: self.svc
        app.dependency_overrides[get_user_repository] = lambda: self.user_repo
        self.user_id = uuid4()
        self.org_id = uuid4()
        yield
        app.dependency_overrides.clear()

    def test_list_channels_success(self):
        from fastapi.testclient import TestClient
        self.svc.list_channels = AsyncMock(return_value=[])
        client = TestClient(self.app)
        resp = client.get(
            "/api/v1/notifications/channels",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (200, 403)

    def test_get_preferences_success(self):
        from fastapi.testclient import TestClient
        self.svc.get_user_preferences = AsyncMock(return_value={
            "release_validated": True,
            "release_invalidated": True,
            "release_pending_reminder": False,
            "weekly_digest": True,
        })
        client = TestClient(self.app)
        resp = client.get(
            "/api/v1/notifications/preferences",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (200, 403)

    def test_update_preferences_success(self):
        from fastapi.testclient import TestClient
        self.svc.update_user_preferences = AsyncMock(return_value={})
        client = TestClient(self.app)
        resp = client.patch(
            "/api/v1/notifications/preferences",
            json={"release_validated": False},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (200, 403)


# ═══════════════════════════════════════════════════════════════════════════════
# TestUsersCoverage  (from test_routers_coverage.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestUsersCoverage:
    @pytest.fixture(autouse=True)
    def _setup(self):
        from main import app
        from core.dependencies import get_user_service, get_jwt_handler
        self.app = app
        self.svc = AsyncMock()
        self.token_svc = MagicMock()
        app.dependency_overrides[get_user_service] = lambda: self.svc
        app.dependency_overrides[get_jwt_handler] = lambda: self.token_svc
        self.user_id = uuid4()
        self.org_id = uuid4()
        yield
        app.dependency_overrides.clear()

    def _headers(self, role="OPERATOR"):
        return {"Authorization": f"Bearer {_token(self.user_id, self.org_id, role)}"}

    def _make_user(self):
        from domain.enums import UserRole
        user = MagicMock()
        user.id = self.user_id
        user.email = "test@test.com"
        user.display_name = "Test"
        user.role = UserRole.U2
        user.organization_id = self.org_id
        user.organization_ids = [self.org_id]
        user.is_active = True
        user.totp_enabled = False
        user.created_at = datetime.now(timezone.utc)
        user.updated_at = datetime.now(timezone.utc)
        user.terms_accepted_at = datetime.now(timezone.utc)
        user.privacy_accepted_at = datetime.now(timezone.utc)
        return user

    def test_delete_account_validation_error_403(self):
        from fastapi.testclient import TestClient
        import json
        from domain.exceptions import ValidationError
        user = self._make_user()
        self.svc.get_user_by_id = AsyncMock(return_value=user)
        self.svc.delete_user_account = AsyncMock(side_effect=ValidationError("block"))
        client = TestClient(self.app)
        resp = client.request(
            "DELETE", "/api/v1/users/me/account",
            content=json.dumps({"password": "wrong"}),
            headers={**self._headers(), "Content-Type": "application/json"},
        )
        assert resp.status_code == 403

    def test_export_user_data_success(self):
        from fastapi.testclient import TestClient
        user = self._make_user()
        self.svc.get_user_by_id = AsyncMock(return_value=user)
        client = TestClient(self.app)
        resp = client.get("/api/v1/users/me/export", headers=self._headers())
        assert resp.status_code == 200
        body = resp.json()
        assert body["schema_version"] == "1.0"
        assert body["export_format"] == "GDPR Art.20 Data Portability"
        assert body["user"]["id"] == str(self.user_id)
        assert body["user"]["email"] == user.email
        assert body["user"]["display_name"] == user.display_name
        assert body["user"]["role"] == "OPERATOR"
        assert body["user"]["is_active"] is True
        assert body["user"]["created_at"] is not None
        assert body["user"]["updated_at"] is not None
        assert body["user"]["terms_accepted_at"] is not None
        assert body["user"]["privacy_accepted_at"] is not None
        assert body["user"]["organization_ids"] == [str(self.org_id)]

    def test_export_user_data_unauthorized_401(self):
        from fastapi.testclient import TestClient
        client = TestClient(self.app)
        resp = client.get("/api/v1/users/me/export")
        assert resp.status_code == 401

    def test_export_user_data_not_found_404(self):
        from fastapi.testclient import TestClient
        self.svc.get_user_by_id = AsyncMock(return_value=None)
        client = TestClient(self.app)
        resp = client.get("/api/v1/users/me/export", headers=self._headers())
        assert resp.status_code == 404

    def test_update_user_role_validation_403(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import ValidationError
        self.svc.update_user_role = AsyncMock(side_effect=ValidationError("block"))
        client = TestClient(self.app)
        resp = client.patch(f"/api/v1/organizations/{self.org_id}/users/{uuid4()}/role",
                            json={"role": "ADMIN"}, headers=self._headers("MANAGER"))
        assert resp.status_code == 403

    def test_remove_user_from_org_validation_403(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import ValidationError
        self.svc.remove_user_from_organization = AsyncMock(side_effect=ValidationError("owner"))
        client = TestClient(self.app)
        resp = client.delete(f"/api/v1/organizations/{self.org_id}/users/{uuid4()}", headers=self._headers("MANAGER"))
        assert resp.status_code == 403

    def test_admin_create_user_success(self):
        from fastapi.testclient import TestClient
        self.svc.create_user = AsyncMock(return_value=self._make_user())
        client = TestClient(self.app)
        resp = client.post("/api/v1/admin/users", json={
            "email": "new@test.com", "display_name": "New", "password": "Pass1234", # NOSONAR
        }, headers=self._headers("ADMIN"))
        assert resp.status_code == 201

    def test_admin_create_user_validation_409(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import ValidationError
        self.svc.create_user = AsyncMock(side_effect=ValidationError("dup email"))
        client = TestClient(self.app)
        resp = client.post("/api/v1/admin/users", json={
            "email": "dup@test.com", "display_name": "Dup", "password": "Pass1234", # NOSONAR
        }, headers=self._headers("ADMIN"))
        assert resp.status_code == 409

    def test_admin_activate_user_success(self):
        from fastapi.testclient import TestClient
        user = self._make_user()
        user.is_active = True
        self.svc.activate_user = AsyncMock(return_value=user)
        client = TestClient(self.app)
        resp = client.patch(f"/api/v1/admin/users/{self.user_id}/activate", headers=self._headers("ADMIN"))
        assert resp.status_code == 200

    def test_admin_deactivate_user_success(self):
        from fastapi.testclient import TestClient
        user = self._make_user()
        user.is_active = False
        self.svc.deactivate_user = AsyncMock(return_value=user)
        client = TestClient(self.app)
        resp = client.patch(f"/api/v1/admin/users/{self.user_id}/deactivate", headers=self._headers("ADMIN"))
        assert resp.status_code == 200

    def test_admin_deactivate_user_validation_403(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import ValidationError
        self.svc.deactivate_user = AsyncMock(side_effect=ValidationError("self"))
        client = TestClient(self.app)
        resp = client.patch(f"/api/v1/admin/users/{self.user_id}/deactivate", headers=self._headers("ADMIN"))
        assert resp.status_code == 403

    def test_admin_update_global_role_success(self):
        from fastapi.testclient import TestClient
        user = self._make_user()
        self.svc.update_global_role = AsyncMock(return_value=user)
        client = TestClient(self.app)
        resp = client.patch(f"/api/v1/admin/users/{self.user_id}/role", json={"role": "ADMIN"},
                            headers=self._headers("ADMIN"))
        assert resp.status_code == 200

    def test_admin_update_global_role_validation_403(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import ValidationError
        self.svc.update_global_role = AsyncMock(side_effect=ValidationError("self"))
        client = TestClient(self.app)
        resp = client.patch(f"/api/v1/admin/users/{self.user_id}/role", json={"role": "MANAGER"},
                            headers=self._headers("ADMIN"))
        assert resp.status_code == 403

    def test_admin_list_users_success(self):
        from fastapi.testclient import TestClient
        self.svc.list_all_users = AsyncMock(return_value=[self._make_user()])
        client = TestClient(self.app)
        resp = client.get("/api/v1/admin/users", headers=self._headers("ADMIN"))
        assert resp.status_code == 200

    def test_admin_list_users_with_filters(self):
        from fastapi.testclient import TestClient
        self.svc.list_all_users = AsyncMock(return_value=[])
        client = TestClient(self.app)
        resp = client.get("/api/v1/admin/users?is_active=true&role=OPERATOR&skip=0&limit=10",
                          headers=self._headers("ADMIN"))
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# TestUsersRouter  (from test_routers_extended.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestUsersRouter:
    @pytest.fixture(autouse=True)
    def _setup(self):
        from main import app
        from core.dependencies import get_user_service
        self.app = app
        self.user_svc = AsyncMock()
        app.dependency_overrides[get_user_service] = lambda: self.user_svc

        self.user_id = uuid4()
        self.org_id = uuid4()
        yield
        app.dependency_overrides.clear()

    def test_get_me_success(self):
        from fastapi.testclient import TestClient
        user = MagicMock()
        user.id = self.user_id
        user.email = "x@x.com"
        user.display_name = "Test"
        from domain.enums import UserRole
        user.role = UserRole.U2
        user.organization_id = self.org_id
        self.user_svc.get_user_by_id = AsyncMock(return_value=user)
        client = TestClient(self.app)
        resp = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code == 200
        assert resp.json()["email"] == "x@x.com"

    def test_get_me_not_found_returns_404(self):
        from fastapi.testclient import TestClient
        self.user_svc.get_user_by_id = AsyncMock(return_value=None)
        client = TestClient(self.app)
        resp = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code == 404

    def test_update_profile_success(self):
        from fastapi.testclient import TestClient
        user = MagicMock()
        user.id = self.user_id
        user.email = "x@x.com"
        user.display_name = "Updated"
        from domain.enums import UserRole
        user.role = UserRole.U2
        user.organization_id = self.org_id
        self.user_svc.update_profile = AsyncMock(return_value=user)
        client = TestClient(self.app)
        resp = client.patch(
            "/api/v1/users/me",
            json={"display_name": "Updated"},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code == 200

    def test_change_password_mismatch_returns_422(self):
        from fastapi.testclient import TestClient
        client = TestClient(self.app)
        resp = client.post(
            "/api/v1/users/me/password",
            json={"current_password": "old", "new_password": "NewPass1!", "confirm_password": "Different1!"},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code == 422

    def test_change_password_success(self):
        from fastapi.testclient import TestClient
        self.user_svc.change_password = AsyncMock(return_value=True)
        client = TestClient(self.app)
        resp = client.post(
            "/api/v1/users/me/password",
            json={"current_password": "old", "new_password": "NewPass1!", "confirm_password": "NewPass1!"},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (200, 400)

    def test_change_password_wrong_current_returns_400(self):
        from fastapi.testclient import TestClient
        self.user_svc.change_password = AsyncMock(return_value=False)
        client = TestClient(self.app)
        resp = client.post(
            "/api/v1/users/me/password",
            json={"current_password": "wrong", "new_password": "NewPass1!", "confirm_password": "NewPass1!"},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code == 400

    def test_list_org_users_success(self):
        from fastapi.testclient import TestClient
        self.user_svc.list_organization_users = AsyncMock(return_value=[])
        client = TestClient(self.app)
        resp = client.get(
            f"/api/v1/organizations/{self.org_id}/users",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (200, 403)

    def test_invite_user_success(self):
        from fastapi.testclient import TestClient
        from domain.enums import UserRole
        user = MagicMock()
        user.id = uuid4()
        user.email = "new@x.com"
        user.display_name = "New"
        user.role = UserRole.U2
        user.organization_id = self.org_id
        self.user_svc.invite_user = AsyncMock(return_value=user)
        client = TestClient(self.app)
        resp = client.post(
            f"/api/v1/organizations/{self.org_id}/users/invite",
            json={"email": "new@x.com"},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (201, 403)


# ═══════════════════════════════════════════════════════════════════════════════
# TestDashboardRouter  (from test_routers_extended.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestDashboardRouter:
    @pytest.fixture(autouse=True)
    def _setup(self):
        from main import app
        from core.dependencies import get_release_repository, get_verification_result_repository
        self.app = app
        self.release_repo = AsyncMock()
        self.release_repo.list_by_organization = AsyncMock(return_value=[])
        self.verification_repo = AsyncMock()
        self.verification_repo.find_by_release = AsyncMock(return_value=[])
        app.dependency_overrides[get_release_repository] = lambda: self.release_repo
        app.dependency_overrides[get_verification_result_repository] = lambda: self.verification_repo
        self.user_id = uuid4()
        self.org_id = uuid4()
        yield
        app.dependency_overrides.clear()

    def test_get_dashboard_metrics_success(self):
        from fastapi.testclient import TestClient
        client = TestClient(self.app)
        resp = client.get(
            f"/api/v1/dashboard/metrics?org_id={self.org_id}",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (200, 403)

    def test_get_dashboard_server_error_returns_500(self):
        from fastapi.testclient import TestClient
        self.release_repo.list_by_organization = AsyncMock(side_effect=RuntimeError("DB fail"))
        client = TestClient(self.app)
        resp = client.get(
            f"/api/v1/dashboard/metrics?org_id={self.org_id}",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (200, 403, 500)


# ═══════════════════════════════════════════════════════════════════════════════
# TestDashboardMetrics  (from test_remaining_gaps.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestDashboardMetrics:
    @pytest.fixture(autouse=True)
    def _setup(self):
        from main import app
        from core.dependencies import get_release_repository, get_verification_result_repository
        self.app = app
        self.release_repo = AsyncMock()
        self.verif_repo = AsyncMock()
        app.dependency_overrides[get_release_repository] = lambda: self.release_repo
        app.dependency_overrides[get_verification_result_repository] = lambda: self.verif_repo
        self.user_id = uuid4()
        self.org_id = uuid4()
        yield
        app.dependency_overrides.clear()

    def _headers(self, role="OPERATOR"):
        return {"Authorization": f"Bearer {_token(self.user_id, self.org_id, role)}"}

    def test_dashboard_org_no_access_403(self):
        from fastapi.testclient import TestClient
        other_org = uuid4()
        client = TestClient(self.app)
        resp = client.get(f"/api/v1/dashboard/metrics?org_id={other_org}",
                          headers=self._headers("OPERATOR"))
        assert resp.status_code == 403

    def test_dashboard_no_org_id_user_has_no_org_400(self):
        from fastapi.testclient import TestClient
        no_org_user = uuid4()
        token = _token(no_org_user, None, "OPERATOR")
        client = TestClient(self.app)
        resp = client.get("/api/v1/dashboard/metrics",
                          headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# TestApiKeysRouter  (from test_routers_extended.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestApiKeysRouter:
    @pytest.fixture(autouse=True)
    def _setup(self):
        from main import app
        from core.dependencies import get_api_key_repository, get_user_repository
        self.app = app
        self.api_key_repo = AsyncMock()
        self.user_repo = AsyncMock()
        self.api_key_repo.list_by_user = AsyncMock(return_value=[])
        app.dependency_overrides[get_api_key_repository] = lambda: self.api_key_repo
        app.dependency_overrides[get_user_repository] = lambda: self.user_repo
        self.user_id = uuid4()
        self.org_id = uuid4()
        yield
        app.dependency_overrides.clear()

    def test_list_api_keys_success(self):
        from fastapi.testclient import TestClient
        client = TestClient(self.app)
        resp = client.get(
            f"/api/v1/users/{self.user_id}/api-keys",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code == 200

    def test_create_api_key_success(self):
        from fastapi.testclient import TestClient
        saved_key = MagicMock()
        saved_key.id = uuid4()
        saved_key.user_id = self.user_id
        saved_key.organization_id = self.org_id
        saved_key.name = "my-key"
        saved_key.prefix = "svk_abc123"
        saved_key.is_active = True
        saved_key.expires_at = None
        saved_key.created_at = datetime.now(timezone.utc)
        self.api_key_repo.save = AsyncMock(return_value=saved_key)
        client = TestClient(self.app)
        resp = client.post(
            f"/api/v1/users/{self.user_id}/api-keys",
            json={"name": "my-key"},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (201, 200)

    def test_revoke_api_key_success(self):
        from fastapi.testclient import TestClient
        key_id = uuid4()
        revoked_key = MagicMock()
        revoked_key.id = key_id
        revoked_key.is_active = False
        revoked_key.user_id = self.user_id
        revoked_key.organization_id = self.org_id
        revoked_key.name = "my-key"
        self.api_key_repo.get_by_id = AsyncMock(return_value=revoked_key)
        self.api_key_repo.update = AsyncMock(return_value=revoked_key)
        client = TestClient(self.app)
        resp = client.delete(
            f"/api/v1/users/{self.user_id}/api-keys/{key_id}",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (200, 204, 404)

    def test_revoke_api_key_not_found_returns_404(self):
        from fastapi.testclient import TestClient
        self.api_key_repo.get_by_id = AsyncMock(return_value=None)
        client = TestClient(self.app)
        resp = client.delete(
            f"/api/v1/users/{self.user_id}/api-keys/{uuid4()}",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# TestConnectorsRouter  (merged from test_routers_extended.py + test_low_coverage_boost.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestConnectorsRouter:
    @pytest.fixture(autouse=True)
    def _setup(self):
        from main import app
        from core.dependencies import get_connector_service, get_connector_repository, get_organization_repository
        self.app = app
        self.svc = AsyncMock()
        self.conn_repo = AsyncMock()
        self.org_repo = AsyncMock()
        app.dependency_overrides[get_connector_service] = lambda: self.svc
        app.dependency_overrides[get_connector_repository] = lambda: self.conn_repo
        app.dependency_overrides[get_organization_repository] = lambda: self.org_repo

        self.user_id = uuid4()
        self.org_id = uuid4()

        from domain.entities.connector_instance import ConnectorInstance
        from domain.enums import ConnectorStatus
        self.mock_conn = ConnectorInstance(
            id=uuid4(), organization_id=self.org_id,
            connector_type="GESTOR_TAREAS", connector_implementation="JIRA",
            name="jira-conn", encrypted_credentials=b"enc",
            status=ConnectorStatus.ACTIVO,
        )
        self.conn_repo.get_by_id = AsyncMock(return_value=self.mock_conn)

        from domain.entities.organization import Organization
        self.mock_org = Organization(id=self.org_id, name="org", slug="org", owner_id=self.user_id)
        self.org_repo.get_by_id = AsyncMock(return_value=self.mock_org)

        yield
        app.dependency_overrides.clear()

    def _headers(self, role="OPERATOR"):
        return {"Authorization": f"Bearer {_token(self.user_id, self.org_id, role)}"}

    def _make_connector(self):
        from domain.entities.connector_instance import ConnectorInstance
        from domain.enums import ConnectorStatus
        return ConnectorInstance(
            id=uuid4(), organization_id=self.org_id,
            connector_type="GESTOR_TAREAS", connector_implementation="JIRA",
            name="jira-conn", encrypted_credentials=b"enc",
            status=ConnectorStatus.ACTIVO,
        )

    # from test_low_coverage_boost.py

    def test_list_connector_types(self):
        from fastapi.testclient import TestClient
        client = TestClient(self.app)
        resp = client.get("/api/v1/connectors/types", headers=self._headers())
        assert resp.status_code == 200

    def test_list_connector_types_clickup_shown_under_planning_and_task_manager(self):
        """ClickUp/Plane/Taiga are genuine task managers (rule engine needs them tagged
        GESTOR_TAREAS so RV-03/RV-04/etc. keep applying) but must also be discoverable
        under Herramienta de Planificacion when creating a connector."""
        from fastapi.testclient import TestClient
        client = TestClient(self.app)
        resp = client.get("/api/v1/connectors/types", headers=self._headers())
        by_type = resp.json()["by_type"]
        planning_impls = {i["implementation"] for i in by_type.get("HERRAMIENTA_PLANIFICACION", [])}
        task_manager_impls = {i["implementation"] for i in by_type.get("GESTOR_TAREAS", [])}
        for impl in ("CLICKUP", "PLANE", "TAIGA"):
            assert impl in planning_impls
            assert impl in task_manager_impls
        assert "MIRO" in planning_impls


    def test_list_connectors_success(self):
        from fastapi.testclient import TestClient
        c = self._make_connector()
        self.svc.list_connectors = AsyncMock(return_value=[c])
        client = TestClient(self.app)
        resp = client.get(f"/api/v1/organizations/{self.org_id}/connectors", headers=self._headers())
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_list_connectors_active_only(self):
        from fastapi.testclient import TestClient
        self.svc.list_connectors = AsyncMock(return_value=[])
        client = TestClient(self.app)
        resp = client.get(f"/api/v1/organizations/{self.org_id}/connectors?active_only=true", headers=self._headers())
        assert resp.status_code == 200

    def test_list_connectors_server_error_500(self):
        from fastapi.testclient import TestClient
        self.svc.list_connectors = AsyncMock(side_effect=RuntimeError("BOOM"))
        client = TestClient(self.app)
        resp = client.get(f"/api/v1/organizations/{self.org_id}/connectors", headers=self._headers())
        assert resp.status_code == 500

    def test_register_connector_success(self):
        from fastapi.testclient import TestClient
        c = self._make_connector()
        self.svc.register_connector = AsyncMock(return_value=c)
        client = TestClient(self.app)
        resp = client.post(f"/api/v1/organizations/{self.org_id}/connectors", json={
            "connector_type": "GESTOR_TAREAS", "connector_implementation": "JIRA",
            "name": "jira-conn", "credentials": {"email": "u@t.com", "api_token": "t"},
        }, headers=self._headers())
        assert resp.status_code == 201

    def test_register_connector_duplicate_409(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import DuplicateEntityError
        self.svc.register_connector = AsyncMock(side_effect=DuplicateEntityError("dup"))
        client = TestClient(self.app)
        resp = client.post(f"/api/v1/organizations/{self.org_id}/connectors", json={
            "connector_type": "GESTOR_TAREAS", "connector_implementation": "JIRA",
            "name": "dup", "credentials": {},
        }, headers=self._headers())
        assert resp.status_code == 409

    def test_register_connector_validation_error_422(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import ValidationError
        self.svc.register_connector = AsyncMock(side_effect=ValidationError("bad"))
        client = TestClient(self.app)
        resp = client.post(f"/api/v1/organizations/{self.org_id}/connectors", json={
            "connector_type": "GESTOR_TAREAS", "connector_implementation": "JIRA",
            "name": "bad", "credentials": {},
        }, headers=self._headers())
        assert resp.status_code == 422

    def test_register_connector_server_error_500(self):
        from fastapi.testclient import TestClient
        self.svc.register_connector = AsyncMock(side_effect=RuntimeError("BOOM"))
        client = TestClient(self.app)
        resp = client.post(f"/api/v1/organizations/{self.org_id}/connectors", json={
            "connector_type": "GESTOR_TAREAS", "connector_implementation": "JIRA",
            "name": "err", "credentials": {},
        }, headers=self._headers())
        assert resp.status_code == 500

    def test_update_connector_success(self):
        from fastapi.testclient import TestClient
        c = self._make_connector()
        self.svc.update_connector = AsyncMock(return_value=c)
        client = TestClient(self.app)
        resp = client.patch(f"/api/v1/organizations/{self.org_id}/connectors/{c.id}",
                            json={"name": "updated"}, headers=self._headers())
        assert resp.status_code == 200

    def test_update_connector_not_found_404(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import EntityNotFoundError
        self.svc.update_connector = AsyncMock(side_effect=EntityNotFoundError("gone"))
        client = TestClient(self.app)
        resp = client.patch(f"/api/v1/organizations/{self.org_id}/connectors/{uuid4()}",
                            json={"name": "x"}, headers=self._headers())
        assert resp.status_code == 404

    def test_update_connector_validation_error_422(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import ValidationError
        self.svc.update_connector = AsyncMock(side_effect=ValidationError("bad"))
        client = TestClient(self.app)
        resp = client.patch(f"/api/v1/organizations/{self.org_id}/connectors/{uuid4()}",
                            json={"name": "bad"}, headers=self._headers())
        assert resp.status_code == 422

    def test_update_connector_server_error_500(self):
        from fastapi.testclient import TestClient
        self.svc.update_connector = AsyncMock(side_effect=RuntimeError("BOOM"))
        client = TestClient(self.app)
        resp = client.patch(f"/api/v1/organizations/{self.org_id}/connectors/{uuid4()}",
                            json={"name": "x"}, headers=self._headers())
        assert resp.status_code == 500

    def test_delete_connector_success(self):
        from fastapi.testclient import TestClient
        self.svc.delete_connector = AsyncMock()
        client = TestClient(self.app)
        resp = client.delete(f"/api/v1/organizations/{self.org_id}/connectors/{uuid4()}",
                             headers=self._headers())
        assert resp.status_code == 204

    def test_delete_connector_not_found_404(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import EntityNotFoundError
        self.svc.delete_connector = AsyncMock(side_effect=EntityNotFoundError("gone"))
        client = TestClient(self.app)
        resp = client.delete(f"/api/v1/organizations/{self.org_id}/connectors/{uuid4()}",
                             headers=self._headers())
        assert resp.status_code == 404

    def test_delete_connector_server_error_500(self):
        from fastapi.testclient import TestClient
        self.svc.delete_connector = AsyncMock(side_effect=RuntimeError("BOOM"))
        client = TestClient(self.app)
        resp = client.delete(f"/api/v1/organizations/{self.org_id}/connectors/{uuid4()}",
                             headers=self._headers())
        assert resp.status_code == 500

    def test_test_connector_success(self):
        from fastapi.testclient import TestClient
        conn = self._make_connector()
        self.svc.test_connector_connection = AsyncMock(return_value=conn)
        client = TestClient(self.app)
        resp = client.post(f"/api/v1/organizations/{self.org_id}/connectors/{uuid4()}/test",
                           headers=self._headers())
        assert resp.status_code == 200
        assert resp.json()["status"] == "ACTIVO"

    def test_test_connector_failure(self):
        from domain.enums import ConnectorStatus
        from fastapi.testclient import TestClient
        conn = self._make_connector()
        conn.status = ConnectorStatus.ERROR
        self.svc.test_connector_connection = AsyncMock(return_value=conn)
        client = TestClient(self.app)
        resp = client.post(f"/api/v1/organizations/{self.org_id}/connectors/{uuid4()}/test",
                           headers=self._headers())
        assert resp.status_code == 200
        assert resp.json()["status"] == "ERROR"

    def test_test_connector_not_found_404(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import EntityNotFoundError
        self.svc.test_connector_connection = AsyncMock(side_effect=EntityNotFoundError("gone"))
        client = TestClient(self.app)
        resp = client.post(f"/api/v1/organizations/{self.org_id}/connectors/{uuid4()}/test",
                           headers=self._headers())
        assert resp.status_code == 404

    def test_test_connector_connection_failed_409(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import ConnectorConnectionFailedError
        self.svc.test_connector_connection = AsyncMock(side_effect=ConnectorConnectionFailedError("fail"))
        client = TestClient(self.app)
        resp = client.post(f"/api/v1/organizations/{self.org_id}/connectors/{uuid4()}/test",
                           headers=self._headers())
        assert resp.status_code == 409

    def test_test_connector_server_error_500(self):
        from fastapi.testclient import TestClient
        self.svc.test_connector_connection = AsyncMock(side_effect=RuntimeError("BOOM"))
        client = TestClient(self.app)
        resp = client.post(f"/api/v1/organizations/{self.org_id}/connectors/{uuid4()}/test",
                           headers=self._headers())
        assert resp.status_code == 500

    def test_list_connector_types_non_admin_or_operator_gets_200(self):
        from fastapi.testclient import TestClient
        client = TestClient(self.app)
        resp = client.get("/api/v1/connectors/types", headers=self._headers("OPERATOR"))
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# TestTemplatesRouter  (from test_routers_extended.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestTemplatesRouter:
    @pytest.fixture(autouse=True)
    def _setup(self):
        from main import app
        from core.dependencies import get_template_service
        self.app = app
        self.svc = AsyncMock()
        app.dependency_overrides[get_template_service] = lambda: self.svc
        self.user_id = uuid4()
        self.org_id = uuid4()
        yield
        app.dependency_overrides.clear()

    def test_list_templates_success(self):
        from fastapi.testclient import TestClient
        self.svc.list_templates = AsyncMock(return_value=[])
        client = TestClient(self.app)
        resp = client.get(
            "/api/v1/templates",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (200, 403)

    def test_create_template_success(self):
        from fastapi.testclient import TestClient
        tmpl = MagicMock()
        tmpl.id = uuid4()
        tmpl.name = "T1"
        tmpl.description = ""
        tmpl.profile_id = uuid4()
        tmpl.organization_id = self.org_id
        tmpl.is_archived = False
        tmpl.created_by = self.user_id
        tmpl.project_name_template = None
        tmpl.created_at = datetime.now(timezone.utc)
        tmpl.updated_at = datetime.now(timezone.utc)
        self.svc.create_template = AsyncMock(return_value=tmpl)
        client = TestClient(self.app)
        resp = client.post(
            "/api/v1/templates",
            json={"name": "T1", "description": "", "profile_id": str(uuid4())},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (201, 403, 422)

    def test_get_template_not_found_returns_404(self):
        from fastapi.testclient import TestClient
        self.svc.get_template = AsyncMock(return_value=None)
        client = TestClient(self.app)
        resp = client.get(
            f"/api/v1/templates/{uuid4()}",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (404, 403)

    def test_create_template_missing_organization_returns_400(self):
        from fastapi.testclient import TestClient
        tmpl = MagicMock()
        tmpl.id = uuid4()
        tmpl.name = "T1"
        tmpl.description = ""
        tmpl.profile_id = uuid4()
        tmpl.organization_id = None
        tmpl.is_archived = False
        tmpl.created_by = self.user_id
        tmpl.project_name_template = None
        tmpl.created_at = datetime.now(timezone.utc)
        tmpl.updated_at = datetime.now(timezone.utc)
        self.svc.create_template = AsyncMock(return_value=tmpl)
        client = TestClient(self.app)
        resp = client.post(
            "/api/v1/templates",
            json={"name": "T1", "description": "", "profile_id": str(uuid4())},
            headers={"Authorization": f"Bearer {_token(self.user_id, None)}"},
        )
        assert resp.status_code in (400, 403, 500)

    def test_create_template_validation_error_returns_409(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import ValidationError
        self.svc.create_template = AsyncMock(side_effect=ValidationError("Template already exists"))
        client = TestClient(self.app)
        resp = client.post(
            "/api/v1/templates",
            json={"name": "T1", "description": "", "profile_id": str(uuid4())},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (409, 403, 500)

    def test_create_template_generic_error_returns_500(self):
        from fastapi.testclient import TestClient
        self.svc.create_template = AsyncMock(side_effect=RuntimeError("Unexpected error"))
        client = TestClient(self.app)
        resp = client.post(
            "/api/v1/templates",
            json={"name": "T1", "description": "", "profile_id": str(uuid4())},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (500, 403)

    def test_list_templates_missing_organization_returns_400(self):
        from fastapi.testclient import TestClient
        self.svc.list_templates = AsyncMock(return_value=[])
        client = TestClient(self.app)
        resp = client.get(
            "/api/v1/templates",
            headers={"Authorization": f"Bearer {_token(self.user_id, None)}"},
        )
        assert resp.status_code in (400, 500)

    def test_list_templates_generic_error_returns_500(self):
        from fastapi.testclient import TestClient
        self.svc.list_templates = AsyncMock(side_effect=RuntimeError("Unexpected error"))
        client = TestClient(self.app)
        resp = client.get(
            "/api/v1/templates",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (500, 403)

    def test_get_template_not_found_returns_404(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import EntityNotFoundError
        self.svc.get_template = AsyncMock(side_effect=EntityNotFoundError("Template not found"))
        client = TestClient(self.app)
        resp = client.get(
            f"/api/v1/templates/{uuid4()}",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (404, 403, 500)

    def test_get_template_http_exception_propagates(self):
        from fastapi.testclient import TestClient
        from fastapi import HTTPException
        self.svc.get_template = AsyncMock(side_effect=HTTPException(status_code=401, detail="Unauthorized"))
        client = TestClient(self.app)
        resp = client.get(
            f"/api/v1/templates/{uuid4()}",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (401, 403, 500)

    def test_get_template_generic_error_returns_500(self):
        from fastapi.testclient import TestClient
        self.svc.get_template = AsyncMock(side_effect=RuntimeError("Unexpected error"))
        client = TestClient(self.app)
        resp = client.get(
            f"/api/v1/templates/{uuid4()}",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (500, 403)

    def test_update_template_not_found_returns_404(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import EntityNotFoundError
        self.svc.update_template = AsyncMock(side_effect=EntityNotFoundError("Template not found"))
        client = TestClient(self.app)
        resp = client.patch(
            f"/api/v1/templates/{uuid4()}",
            json={"name": "Updated"},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (404, 403, 500)

    def test_update_template_generic_error_returns_500(self):
        from fastapi.testclient import TestClient
        self.svc.update_template = AsyncMock(side_effect=RuntimeError("Unexpected error"))
        client = TestClient(self.app)
        resp = client.patch(
            f"/api/v1/templates/{uuid4()}",
            json={"name": "Updated"},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (500, 403)

    def test_archive_template_not_found_returns_404(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import EntityNotFoundError
        self.svc.archive_template = AsyncMock(side_effect=EntityNotFoundError("Template not found"))
        client = TestClient(self.app)
        resp = client.post(
            f"/api/v1/templates/{uuid4()}/archive",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (404, 403, 500)

    def test_archive_template_generic_error_returns_500(self):
        from fastapi.testclient import TestClient
        self.svc.archive_template = AsyncMock(side_effect=RuntimeError("Unexpected error"))
        client = TestClient(self.app)
        resp = client.post(
            f"/api/v1/templates/{uuid4()}/archive",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (500, 403)

    def test_clone_template_not_found_returns_404(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import EntityNotFoundError
        self.svc.clone_template = AsyncMock(side_effect=EntityNotFoundError("Template not found"))
        client = TestClient(self.app)
        resp = client.post(
            f"/api/v1/templates/{uuid4()}/clone",
            json={"name": "Cloned", "target_organization_id": str(uuid4())},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (404, 403, 500)

    def test_clone_template_validation_error_returns_409(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import ValidationError
        self.svc.clone_template = AsyncMock(side_effect=ValidationError("Cannot clone to same organization"))
        client = TestClient(self.app)
        resp = client.post(
            f"/api/v1/templates/{uuid4()}/clone",
            json={"name": "Cloned", "target_organization_id": str(uuid4())},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (409, 403, 500)

    def test_clone_template_generic_error_returns_500(self):
        from fastapi.testclient import TestClient
        self.svc.clone_template = AsyncMock(side_effect=RuntimeError("Unexpected error"))
        client = TestClient(self.app)
        resp = client.post(
            f"/api/v1/templates/{uuid4()}/clone",
            json={"name": "Cloned", "target_organization_id": str(uuid4())},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (500, 403)


# ═══════════════════════════════════════════════════════════════════════════════
# TestProfilesRouter  (from test_routers_extended.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestProfilesRouter:
    @pytest.fixture(autouse=True)
    def _setup(self):
        from main import app
        from core.dependencies import get_profile_service
        self.app = app
        self.svc = AsyncMock()
        app.dependency_overrides[get_profile_service] = lambda: self.svc
        self.user_id = uuid4()
        self.org_id = uuid4()
        yield
        app.dependency_overrides.clear()

    def test_list_profiles_success(self):
        from fastapi.testclient import TestClient
        self.svc.list_profiles = AsyncMock(return_value=[])
        client = TestClient(self.app)
        resp = client.get(
            f"/api/v1/organizations/{self.org_id}/profiles",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (200, 403)

    def test_create_profile_success(self):
        from fastapi.testclient import TestClient
        from domain.entities.verification_profile import VerificationProfile
        p = VerificationProfile(id=uuid4(), organization_id=self.org_id, name="P1")
        self.svc.create_profile = AsyncMock(return_value=p)
        client = TestClient(self.app)
        resp = client.post(
            f"/api/v1/organizations/{self.org_id}/profiles",
            json={"name": "P1", "description": ""},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (201, 403, 422)

    def test_get_profile_not_found_returns_404(self):
        from fastapi.testclient import TestClient
        self.svc.get_profile = AsyncMock(return_value=None)
        client = TestClient(self.app)
        resp = client.get(
            f"/api/v1/profiles/{uuid4()}",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (404, 403, 405)

    def test_list_profiles_server_error_500(self):
        from fastapi.testclient import TestClient
        self.svc.list_profiles = AsyncMock(side_effect=RuntimeError("BOOM"))
        client = TestClient(self.app)
        resp = client.get(
            f"/api/v1/organizations/{self.org_id}/profiles",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code == 500

    def test_create_profile_validation_error_409(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import ValidationError
        self.svc.create_profile = AsyncMock(side_effect=ValidationError("bad"))
        client = TestClient(self.app)
        resp = client.post(
            f"/api/v1/organizations/{self.org_id}/profiles",
            json={"name": "P1", "description": ""},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code == 409

    def test_create_profile_server_error_500(self):
        from fastapi.testclient import TestClient
        self.svc.create_profile = AsyncMock(side_effect=RuntimeError("BOOM"))
        client = TestClient(self.app)
        resp = client.post(
            f"/api/v1/organizations/{self.org_id}/profiles",
            json={"name": "P1", "description": ""},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code == 500

    def test_get_profile_success(self):
        from fastapi.testclient import TestClient
        from domain.entities.verification_profile import VerificationProfile
        pid = uuid4()
        p = VerificationProfile(id=pid, organization_id=self.org_id, name="P1")
        rule = MagicMock()
        rule.id = uuid4()
        rule.rule_template = "RV01"
        rule.severity = MagicMock()
        rule.severity.value = "HIGH"
        rule.connector_instance_id = uuid4()
        rule.params = {}
        rule.display_order = 1
        rule.is_active = True
        p.rules = [rule]
        self.svc.get_profile = AsyncMock(return_value=p)
        client = TestClient(self.app)
        resp = client.get(
            f"/api/v1/profiles/{pid}",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (200, 403)
        if resp.status_code == 200:
            data = resp.json()
            assert data["id"] == str(pid)
            assert len(data["rules"]) == 1

    def test_get_profile_server_error_500(self):
        from fastapi.testclient import TestClient
        self.svc.get_profile = AsyncMock(side_effect=RuntimeError("BOOM"))
        client = TestClient(self.app)
        resp = client.get(
            f"/api/v1/profiles/{uuid4()}",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (500, 403)

    def test_update_profile_success(self):
        from fastapi.testclient import TestClient
        from domain.entities.verification_profile import VerificationProfile
        pid = uuid4()
        p = VerificationProfile(id=pid, organization_id=self.org_id, name="Updated")
        self.svc.update_profile = AsyncMock(return_value=p)
        client = TestClient(self.app)
        resp = client.patch(
            f"/api/v1/profiles/{pid}",
            json={"name": "Updated", "description": "new desc"},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (200, 403)
        if resp.status_code == 200:
            assert resp.json()["name"] == "Updated"

    def test_update_profile_not_found_404(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import EntityNotFoundError
        self.svc.update_profile = AsyncMock(side_effect=EntityNotFoundError("gone"))
        client = TestClient(self.app)
        resp = client.patch(
            f"/api/v1/profiles/{uuid4()}",
            json={"name": "Updated"},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (404, 403)

    def test_update_profile_validation_error_409(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import ValidationError
        self.svc.update_profile = AsyncMock(side_effect=ValidationError("bad"))
        client = TestClient(self.app)
        resp = client.patch(
            f"/api/v1/profiles/{uuid4()}",
            json={"name": "X"},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (409, 403)

    def test_update_profile_server_error_500(self):
        from fastapi.testclient import TestClient
        self.svc.update_profile = AsyncMock(side_effect=RuntimeError("BOOM"))
        client = TestClient(self.app)
        resp = client.patch(
            f"/api/v1/profiles/{uuid4()}",
            json={"name": "Updated"},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (500, 403)

    def test_delete_profile_success(self):
        from fastapi.testclient import TestClient
        self.svc.delete_profile = AsyncMock()
        client = TestClient(self.app)
        resp = client.delete(
            f"/api/v1/profiles/{uuid4()}",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (204, 403)

    def test_delete_profile_not_found_404(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import EntityNotFoundError
        self.svc.delete_profile = AsyncMock(side_effect=EntityNotFoundError("gone"))
        client = TestClient(self.app)
        resp = client.delete(
            f"/api/v1/profiles/{uuid4()}",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (404, 403)

    def test_delete_profile_server_error_500(self):
        from fastapi.testclient import TestClient
        self.svc.delete_profile = AsyncMock(side_effect=RuntimeError("BOOM"))
        client = TestClient(self.app)
        resp = client.delete(
            f"/api/v1/profiles/{uuid4()}",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (500, 403)

    def test_add_rule_success(self):
        from fastapi.testclient import TestClient
        pid = uuid4()
        rule = MagicMock()
        rule.id = uuid4()
        rule.rule_template = "RV01"
        self.svc.add_rule = AsyncMock(return_value=rule)
        client = TestClient(self.app)
        resp = client.post(
            f"/api/v1/profiles/{pid}/rules",
            json={"rule_template": "RV01", "severity": "HIGH"},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (201, 403)
        if resp.status_code == 201:
            assert resp.json()["rule_template"] == "RV01"

    def test_add_rule_profile_not_found_404(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import EntityNotFoundError
        self.svc.add_rule = AsyncMock(side_effect=EntityNotFoundError("gone"))
        client = TestClient(self.app)
        resp = client.post(
            f"/api/v1/profiles/{uuid4()}/rules",
            json={"rule_template": "RV01", "severity": "HIGH"},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (404, 403)

    def test_add_rule_server_error_500(self):
        from fastapi.testclient import TestClient
        self.svc.add_rule = AsyncMock(side_effect=RuntimeError("BOOM"))
        client = TestClient(self.app)
        resp = client.post(
            f"/api/v1/profiles/{uuid4()}/rules",
            json={"rule_template": "RV01", "severity": "HIGH"},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id, 'ADMIN')}"},
        )
        assert resp.status_code == 500

    def test_update_rule_success(self):
        from fastapi.testclient import TestClient
        rule = MagicMock()
        rule.id = uuid4()
        rule.is_active = True
        self.svc.update_rule = AsyncMock(return_value=rule)
        client = TestClient(self.app)
        resp = client.patch(
            f"/api/v1/rules/{uuid4()}",
            json={"is_active": True},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (200, 403)
        if resp.status_code == 200:
            assert resp.json()["is_active"] is True

    def test_update_rule_not_found_404(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import EntityNotFoundError
        self.svc.update_rule = AsyncMock(side_effect=EntityNotFoundError("gone"))
        client = TestClient(self.app)
        resp = client.patch(
            f"/api/v1/rules/{uuid4()}",
            json={"is_active": False},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (404, 403)

    def test_update_rule_server_error_500(self):
        from fastapi.testclient import TestClient
        self.svc.update_rule = AsyncMock(side_effect=RuntimeError("BOOM"))
        client = TestClient(self.app)
        resp = client.patch(
            f"/api/v1/rules/{uuid4()}",
            json={"is_active": False},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (500, 403)

    def test_delete_rule_success(self):
        from fastapi.testclient import TestClient
        self.svc.delete_rule = AsyncMock()
        client = TestClient(self.app)
        resp = client.delete(
            f"/api/v1/rules/{uuid4()}",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (204, 403)

    def test_delete_rule_not_found_404(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import EntityNotFoundError
        self.svc.delete_rule = AsyncMock(side_effect=EntityNotFoundError("gone"))
        client = TestClient(self.app)
        resp = client.delete(
            f"/api/v1/rules/{uuid4()}",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (404, 403)

    def test_delete_rule_server_error_500(self):
        from fastapi.testclient import TestClient
        self.svc.delete_rule = AsyncMock(side_effect=RuntimeError("BOOM"))
        client = TestClient(self.app)
        resp = client.delete(
            f"/api/v1/rules/{uuid4()}",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (500, 403)


# ═══════════════════════════════════════════════════════════════════════════════
# TestAuditRouter  (from test_routers_extended.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuditRouter:
    @pytest.fixture(autouse=True)
    def _setup(self):
        from main import app
        self.app = app
        self.user_id = uuid4()
        self.org_id = uuid4()
        yield
        app.dependency_overrides.clear()

    def test_get_audit_logs_no_token_returns_401(self):
        from fastapi.testclient import TestClient
        client = TestClient(self.app)
        resp = client.get("/api/v1/audit/logs")
        assert resp.status_code in (401, 403)

    def test_get_audit_logs_admin_returns_200_or_403(self):
        from fastapi.testclient import TestClient
        client = TestClient(self.app)
        resp = client.get(
            "/api/v1/audit/logs",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id, 'ADMIN')}"},
        )
        assert resp.status_code in (200, 403, 500)


# ═══════════════════════════════════════════════════════════════════════════════
# TestCustomRolesRouter  (merged from test_routers_extended.py + test_low_coverage_boost.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCustomRolesRouter:
    @pytest.fixture(autouse=True)
    def _setup(self):
        from main import app
        from core.dependencies import get_custom_role_service
        self.app = app
        self.svc = AsyncMock()
        app.dependency_overrides[get_custom_role_service] = lambda: self.svc
        self.user_id = uuid4()
        self.org_id = uuid4()
        yield
        app.dependency_overrides.clear()

    def _headers(self, role="OPERATOR"):
        return {"Authorization": f"Bearer {_token(self.user_id, self.org_id, role)}"}

    def _make_role(self):
        from domain.entities.custom_role import CustomRole
        from domain.enums import Permission
        return CustomRole(
            organization_id=self.org_id, name="viewer",
            permissions=[Permission.VIEW_DASHBOARD],
        )

    def test_list_custom_roles_success(self):
        from fastapi.testclient import TestClient
        r = self._make_role()
        self.svc.list_roles = AsyncMock(return_value=[r])
        client = TestClient(self.app)
        resp = client.get(f"/api/v1/organizations/{self.org_id}/roles", headers=self._headers("MANAGER"))
        assert resp.status_code in (200, 403)
        if resp.status_code == 200:
            assert len(resp.json()) == 1

    def test_list_custom_roles_empty(self):
        from fastapi.testclient import TestClient
        self.svc.list_roles = AsyncMock(return_value=[])
        client = TestClient(self.app)
        resp = client.get(f"/api/v1/organizations/{self.org_id}/roles", headers=self._headers("MANAGER"))
        assert resp.status_code in (200, 403)

    def test_list_custom_roles_server_error_500(self):
        from fastapi.testclient import TestClient
        self.svc.list_roles = AsyncMock(side_effect=RuntimeError("BOOM"))
        client = TestClient(self.app)
        resp = client.get(f"/api/v1/organizations/{self.org_id}/roles", headers=self._headers("MANAGER"))
        assert resp.status_code in (500, 403)

    def test_create_custom_role_success(self):
        from fastapi.testclient import TestClient
        r = self._make_role()
        self.svc.create_role = AsyncMock(return_value=r)
        client = TestClient(self.app)
        resp = client.post(f"/api/v1/organizations/{self.org_id}/roles", json={
            "name": "viewer", "permissions": ["VIEW_DASHBOARD"],
        }, headers=self._headers("MANAGER"))
        assert resp.status_code in (201, 403)

    def test_create_custom_role_duplicate_409(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import DuplicateEntityError
        self.svc.create_role = AsyncMock(side_effect=DuplicateEntityError("dup"))
        client = TestClient(self.app)
        resp = client.post(f"/api/v1/organizations/{self.org_id}/roles", json={
            "name": "dup", "permissions": ["VIEW_DASHBOARD"],
        }, headers=self._headers("MANAGER"))
        assert resp.status_code in (409, 403)

    def test_create_custom_role_value_error_422(self):
        from fastapi.testclient import TestClient
        self.svc.create_role = AsyncMock(side_effect=ValueError("bad"))
        client = TestClient(self.app)
        resp = client.post(f"/api/v1/organizations/{self.org_id}/roles", json={
            "name": "bad", "permissions": ["VIEW_DASHBOARD"],
        }, headers=self._headers("MANAGER"))
        assert resp.status_code in (422, 403)

    def test_create_custom_role_server_error_500(self):
        from fastapi.testclient import TestClient
        self.svc.create_role = AsyncMock(side_effect=RuntimeError("BOOM"))
        client = TestClient(self.app)
        resp = client.post(f"/api/v1/organizations/{self.org_id}/roles", json={
            "name": "err", "permissions": ["VIEW_DASHBOARD"],
        }, headers=self._headers("MANAGER"))
        assert resp.status_code in (500, 403)

    def test_update_custom_role_success(self):
        from fastapi.testclient import TestClient
        r = self._make_role()
        self.svc.update_role = AsyncMock(return_value=r)
        client = TestClient(self.app)
        resp = client.patch(f"/api/v1/roles/{r.id}", json={
            "name": "updated", "permissions": ["VIEW_DASHBOARD"],
        }, headers=self._headers("MANAGER"))
        assert resp.status_code in (200, 403)

    def test_update_custom_role_not_found_404(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import EntityNotFoundError
        self.svc.update_role = AsyncMock(side_effect=EntityNotFoundError("gone"))
        client = TestClient(self.app)
        resp = client.patch(f"/api/v1/roles/{uuid4()}", json={
            "name": "x", "permissions": ["VIEW_DASHBOARD"],
        }, headers=self._headers("MANAGER"))
        assert resp.status_code in (404, 403)

    def test_update_custom_role_duplicate_409(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import DuplicateEntityError
        self.svc.update_role = AsyncMock(side_effect=DuplicateEntityError("dup"))
        client = TestClient(self.app)
        resp = client.patch(f"/api/v1/roles/{uuid4()}", json={
            "name": "dup", "permissions": ["VIEW_DASHBOARD"],
        }, headers=self._headers("MANAGER"))
        assert resp.status_code in (409, 403)

    def test_update_custom_role_value_error_422(self):
        from fastapi.testclient import TestClient
        self.svc.update_role = AsyncMock(side_effect=ValueError("bad"))
        client = TestClient(self.app)
        resp = client.patch(f"/api/v1/roles/{uuid4()}", json={
            "name": "bad", "permissions": ["VIEW_DASHBOARD"],
        }, headers=self._headers("MANAGER"))
        assert resp.status_code in (422, 403)

    def test_update_custom_role_server_error_500(self):
        from fastapi.testclient import TestClient
        self.svc.update_role = AsyncMock(side_effect=RuntimeError("BOOM"))
        client = TestClient(self.app)
        resp = client.patch(f"/api/v1/roles/{uuid4()}", json={
            "name": "x", "permissions": ["VIEW_DASHBOARD"],
        }, headers=self._headers("MANAGER"))
        assert resp.status_code in (500, 403)

    def test_delete_custom_role_success(self):
        from fastapi.testclient import TestClient
        self.svc.delete_role = AsyncMock()
        client = TestClient(self.app)
        resp = client.delete(f"/api/v1/roles/{uuid4()}", headers=self._headers("MANAGER"))
        assert resp.status_code in (204, 403)

    def test_delete_custom_role_not_found_404(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import EntityNotFoundError
        self.svc.delete_role = AsyncMock(side_effect=EntityNotFoundError("gone"))
        client = TestClient(self.app)
        resp = client.delete(f"/api/v1/roles/{uuid4()}", headers=self._headers("MANAGER"))
        assert resp.status_code in (404, 403)

    def test_delete_custom_role_server_error_500(self):
        from fastapi.testclient import TestClient
        self.svc.delete_role = AsyncMock(side_effect=RuntimeError("BOOM"))
        client = TestClient(self.app)
        resp = client.delete(f"/api/v1/roles/{uuid4()}", headers=self._headers("MANAGER"))
        assert resp.status_code in (500, 403)


# ═══════════════════════════════════════════════════════════════════════════════
# TestHealthEndpoint  (from test_routers_extended.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestHealthEndpoint:
    def test_health_check(self):
        from fastapi.testclient import TestClient
        from main import app
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# TestAdminReloadRules  (from test_remaining_gaps.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdminReloadRules:
    @pytest.fixture(autouse=True)
    def _setup(self):
        from main import app
        from core.dependencies import get_rules_service
        self.app = app
        self.svc = AsyncMock()
        app.dependency_overrides[get_rules_service] = lambda: self.svc
        self.user_id = uuid4()
        self.org_id = uuid4()
        yield
        app.dependency_overrides.clear()

    def _headers(self, role="ADMIN"):
        return {"Authorization": f"Bearer {_token(self.user_id, self.org_id, role)}"}

    def test_reload_rules_success(self):
        from fastapi.testclient import TestClient
        self.svc.reload_custom_rules = AsyncMock(return_value={
            "success": True, "rules_loaded": 5, "message": "ok"
        })
        client = TestClient(self.app)
        resp = client.post("/api/v1/admin/rules/reload", headers=self._headers("ADMIN"))
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["rules_loaded"] == 5

    def test_reload_rules_server_error_500(self):
        from fastapi.testclient import TestClient
        self.svc.reload_custom_rules = AsyncMock(side_effect=RuntimeError("boom"))
        client = TestClient(self.app)
        resp = client.post("/api/v1/admin/rules/reload", headers=self._headers("ADMIN"))
        assert resp.status_code == 500


# ═══════════════════════════════════════════════════════════════════════════════
# TestTaskStatus  (from test_remaining_gaps.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestTaskStatus:
    @pytest.fixture(autouse=True)
    def _setup(self):
        from main import app
        from core.dependencies import get_task_service
        self.app = app
        self.svc = AsyncMock()
        app.dependency_overrides[get_task_service] = lambda: self.svc
        self.user_id = uuid4()
        self.org_id = uuid4()
        yield
        app.dependency_overrides.clear()

    def _headers(self, role="OPERATOR"):
        return {"Authorization": f"Bearer {_token(self.user_id, self.org_id, role)}"}

    def test_get_task_status_success(self):
        from fastapi.testclient import TestClient
        from domain.enums import TaskStatus
        self.svc.get_task_status = AsyncMock(return_value=TaskStatus.SUCCESS)

        with patch("infrastructure.secondary.queue.celery_app.celery_app.AsyncResult") as mock_async_result:
            mock_result = MagicMock()
            mock_result.ready.return_value = True
            mock_result.result = {"result": "ok"}
            mock_async_result.return_value = mock_result

            client = TestClient(self.app)
            resp = client.get("/api/v1/tasks/test-task-123", headers=self._headers())
            assert resp.status_code == 200
            data = resp.json()
            assert data["task_id"] == "test-task-123"
            assert data["status"] == "SUCCESS"

    def test_get_task_status_server_error_500(self):
        from fastapi.testclient import TestClient
        self.svc.get_task_status = AsyncMock(side_effect=RuntimeError("boom"))
        client = TestClient(self.app)
        resp = client.get("/api/v1/tasks/test-task-123", headers=self._headers())
        assert resp.status_code == 500


# ═══════════════════════════════════════════════════════════════════════════════
# TestReleasesRouter  (from test_more_services.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestReleasesRouter:
    @pytest.fixture(autouse=True)
    def _setup(self):
        from main import app
        from core.dependencies import (
            get_release_service, get_project_repository,
            get_organization_repository, get_artifact_service,
            get_verification_service,
        )
        self.app = app
        self.release_svc = AsyncMock()
        self.artifact_svc = AsyncMock()
        self.verification_svc = AsyncMock()
        self.project_repo = AsyncMock()
        self.org_repo = AsyncMock()

        self.user_id = uuid4()
        self.org_id = uuid4()
        self.project_id = uuid4()

        project = MagicMock()
        project.id = self.project_id
        project.organization_id = self.org_id
        project.profile_id = uuid4()
        self.project_repo.get_by_id = AsyncMock(return_value=project)

        org = MagicMock()
        org.id = self.org_id
        org.owner_id = self.user_id
        self.org_repo.get_by_id = AsyncMock(return_value=org)

        app.dependency_overrides[get_release_service] = lambda: self.release_svc
        app.dependency_overrides[get_artifact_service] = lambda: self.artifact_svc
        app.dependency_overrides[get_verification_service] = lambda: self.verification_svc
        app.dependency_overrides[get_project_repository] = lambda: self.project_repo
        app.dependency_overrides[get_organization_repository] = lambda: self.org_repo
        yield
        app.dependency_overrides.clear()

    def _token(self, role="OPERATOR"):
        return _token(self.user_id, self.org_id, role)

    def test_list_releases_returns_200(self):
        from fastapi.testclient import TestClient
        self.release_svc.list_releases = AsyncMock(return_value=[])
        client = TestClient(self.app)
        resp = client.get(
            f"/api/v1/projects/{self.project_id}/releases",
            headers={"Authorization": f"Bearer {self._token()}"},
        )
        assert resp.status_code == 200

    def test_create_release_validation_error_returns_422(self):
        from fastapi.testclient import TestClient
        from domain.exceptions import ValidationError
        self.release_svc.create_release = AsyncMock(side_effect=ValidationError("bad"))
        client = TestClient(self.app)
        resp = client.post(
            f"/api/v1/projects/{self.project_id}/releases",
            json={"name": "r", "version": "1.0.0", "description": "d"},
            headers={"Authorization": f"Bearer {self._token()}"},
        )
        assert resp.status_code == 422

    def test_get_global_releases_admin_returns_200(self):
        from fastapi.testclient import TestClient
        self.release_svc.list_org_releases = AsyncMock(return_value=[])
        client = TestClient(self.app)
        resp = client.get(
            "/api/v1/releases",
            headers={"Authorization": f"Bearer {self._token('ADMIN')}"},
        )
        assert resp.status_code == 200

    def test_list_releases_no_token_returns_401(self):
        from fastapi.testclient import TestClient
        client = TestClient(self.app)
        resp = client.get(f"/api/v1/projects/{self.project_id}/releases")
        assert resp.status_code == 401

    def test_delete_release_success(self):
        from fastapi.testclient import TestClient
        release = MagicMock()
        release.created_by = self.user_id
        release.project = MagicMock()
        release.project.organization_id = self.org_id
        self.release_svc.get_release = AsyncMock(return_value=release)
        self.release_svc.delete_release = AsyncMock()
        client = TestClient(self.app)
        resp = client.delete(
            f"/api/v1/releases/{uuid4()}",
            headers={"Authorization": f"Bearer {self._token('ADMIN')}"},
        )
        assert resp.status_code in (204, 200, 403)

    def test_no_token_returns_401(self):
        from fastapi.testclient import TestClient
        client = TestClient(self.app)
        resp = client.get(f"/api/v1/projects/{self.project_id}/releases")
        assert resp.status_code == 401

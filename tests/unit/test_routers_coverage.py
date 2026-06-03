"""
Router endpoint coverage tests for releases, organizations, auth,
access_requests, notifications, and users — covering previously
untested branches and endpoints.
"""

import os
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


def _token(user_id, org_id, role_str="OPERATOR"):
    from domain.enums import UserRole
    from infrastructure.primary.middleware.jwt_handler import JwtHandler
    role_map = {"VIEWER": UserRole.U1, "OPERATOR": UserRole.U2, "ADMIN": UserRole.U3, "MANAGER": UserRole.U4}
    handler = JwtHandler(
        secret=os.environ["JWT_SECRET_KEY"],
        algorithm=os.environ["JWT_ALGORITHM"],
        access_token_expire_minutes=60,
        refresh_token_expire_days=30,
        redis_url=None,
    )
    return handler.create_access_token(
        user_id=user_id, email=f"{role_str.lower()}@test.com",
        role=role_map[role_str], organization_id=org_id,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# RELEASES ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

class TestReleasesCoverage:
    @pytest.fixture(autouse=True)
    def _setup(self):
        from main import app
        from core.dependencies import (
            get_release_service, get_artifact_service, get_verification_service,
            get_export_service, get_project_repository, get_organization_repository,
            get_release_repository,
        )
        self.app = app
        self.rel_svc = AsyncMock()
        self.art_svc = AsyncMock()
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

        # Mock release repo for require_release_access dependency
        fake_row = MagicMock()
        fake_row.id = uuid4()
        self.release_repo.get_by_id = AsyncMock(return_value=fake_row)

        app.dependency_overrides[get_release_service] = lambda: self.rel_svc
        app.dependency_overrides[get_artifact_service] = lambda: self.art_svc
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
        # requires VIEW_ORG_PROJECTS permission
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
        # requires VIEW_ORG_PROJECTS permission
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
        # FastAPI validates Literal["pdf"] before handler, returns 422
        assert resp.status_code in (400, 422, 403)

    def test_export_project_csv_bad_format_400(self):
        from fastapi.testclient import TestClient
        client = TestClient(self.app)
        resp = client.get(
            f"/api/v1/projects/{uuid4()}/results/export?format=pdf",
            headers=self._headers("MANAGER"),
        )
        # FastAPI validates Literal["csv"] before handler
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
# ORGANIZATIONS ROUTER
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

    def _make_org(self, owner_id=None):
        org = MagicMock()
        org.id = self.org_id
        org.name = "Test Org"
        org.slug = "test-org"
        org.owner_id = owner_id or self.user_id
        org.is_active = True
        org.created_at = datetime.now(timezone.utc)
        return org

    def _make_project(self, proj_id=None):
        p = MagicMock()
        p.id = proj_id or uuid4()
        p.name = "Proj"
        p.description = "desc"
        p.organization_id = self.org_id
        p.profile_id = uuid4()
        p.is_archived = False
        p.created_at = datetime.now(timezone.utc)
        return p

    def test_get_organization_found_owner_access(self):
        from fastapi.testclient import TestClient
        org = self._make_org(owner_id=self.user_id)
        self.svc.get_organization = AsyncMock(return_value=org)
        client = TestClient(self.app)
        resp = client.get(f"/api/v1/organizations/{self.org_id}", headers=self._headers())
        assert resp.status_code == 200

    def test_get_organization_found_org_member_access(self):
        from fastapi.testclient import TestClient
        org = self._make_org(owner_id=uuid4())
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
        org = self._make_org(owner_id=uuid4())
        self.svc.get_organization = AsyncMock(return_value=org)
        other_user = uuid4()
        client = TestClient(self.app)
        resp = client.get(f"/api/v1/organizations/{self.org_id}",
                          headers={"Authorization": f"Bearer {_token(other_user, uuid4(), 'OPERATOR')}"})
        assert resp.status_code == 403

    def test_get_project_by_id_found(self):
        from fastapi.testclient import TestClient
        p = self._make_project()
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
        p = self._make_project()
        p.organization_id = uuid4()
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
        self.svc.list_projects = AsyncMock(return_value=[self._make_project()])
        client = TestClient(self.app)
        # Requires VIEW_ORG_PROJECTS which MANAGER/ADMIN have
        resp = client.get(f"/api/v1/organizations/{self.org_id}/projects", headers=self._headers("MANAGER"))
        assert resp.status_code == 200

    def test_get_project_in_org_found(self):
        from fastapi.testclient import TestClient
        p = self._make_project()
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
        p = self._make_project()
        p.organization_id = uuid4()
        self.svc.get_project = AsyncMock(return_value=p)
        client = TestClient(self.app)
        resp = client.get(f"/api/v1/organizations/{self.org_id}/projects/{p.id}", headers=self._headers("MANAGER"))
        assert resp.status_code == 403

    def test_archive_project_success(self):
        from fastapi.testclient import TestClient
        p = self._make_project()
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
        org = self._make_org()
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
        org = self._make_org()
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
# AUTH ROUTER
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
# ACCESS REQUESTS ROUTER
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
# NOTIFICATIONS ROUTER
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
# USERS ROUTER
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
        self.svc.get_user_by_id = AsyncMock(return_value=self._make_user())
        client = TestClient(self.app)
        resp = client.get("/api/v1/users/me/export", headers=self._headers())
        assert resp.status_code == 200

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
                            json={"role": "VIEWER"}, headers=self._headers("MANAGER"))
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
        resp = client.patch(f"/api/v1/admin/users/{self.user_id}/role", json={"role": "VIEWER"},
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

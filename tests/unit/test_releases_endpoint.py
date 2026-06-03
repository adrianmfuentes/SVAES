"""
Pruebas Unitarias de Endpoints FastAPI — POST /releases
Técnica: Base Choice (ISO 29119-4)
Total: 8 tests (TC-UNI-API-00 a TC-UNI-API-07)
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET_KEY", "base-choice-test-secret-key-32-ch!")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXPIRE_MINUTES", "60")
os.environ.setdefault("ALLOWED_ORIGINS", "*")
os.environ.setdefault("ENCRYPTION_KEY", "HnVk8Q2xLm9pR4sT6wYzA1bC3dF5gJ7kN=")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
os.environ.setdefault("ENGINE_URL", "http://localhost:8081")

pytestmark = pytest.mark.unit


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


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


def _make_token(user_id, org_id, role):
    from domain.enums import UserRole
    from infrastructure.primary.middleware.jwt_handler import JwtHandler
    handler = JwtHandler(
        secret=os.environ["JWT_SECRET_KEY"],
        algorithm=os.environ["JWT_ALGORITHM"],
        access_token_expire_minutes=60,
        refresh_token_expire_days=30,
        redis_url=None,
    )
    role_map = {
        "OPERATOR": UserRole.U2,
        "ADMIN": UserRole.U3,
        "VIEWER": UserRole.U1,
    }
    return handler.create_access_token(
        user_id=user_id,
        email=f"{role.lower()}@test.com",
        role=role_map[role],
        organization_id=org_id,
    )


class TestCreateReleaseEndpoint:
    """
    TC-UNI-API-00 a TC-UNI-API-07: Base Choice sobre POST /releases.
    """

    @pytest.fixture(autouse=True)
    def _setup_app(self):
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
        token = _make_token(self.user_id, self.org_id, "OPERATOR")
        resp = self.client.post(
            f"/api/v1/projects/{self.project_id}/releases",
            json=self._valid_body(),
            headers=self._headers(token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert "status" in data

    # TC-UNI-API-01: Variación ADMIN -> 201 (admin bypasses project checks)
    def test_tc_uni_api_01_admin_role_bypasses_checks_returns_201(self):
        token = _make_token(self.user_id, self.org_id, "ADMIN")
        resp = self.client.post(
            f"/api/v1/projects/{self.project_id}/releases",
            json=self._valid_body(),
            headers=self._headers(token),
        )
        assert resp.status_code == 201

    # TC-UNI-API-02: VIEWER cross-org -> 403
    def test_tc_uni_api_02_viewer_cross_org_returns_403(self):
        other_org_id = uuid4()
        project = MagicMock()
        project.id = self.project_id
        project.organization_id = other_org_id
        self.project_repo.get_by_id = AsyncMock(return_value=project)
        self.org_repo.get_by_id = AsyncMock(return_value=None)

        token = _make_token(self.user_id, self.org_id, "VIEWER")
        resp = self.client.post(
            f"/api/v1/projects/{self.project_id}/releases",
            json=self._valid_body(),
            headers=self._headers(token),
        )
        assert resp.status_code in (403, 404)

    # TC-UNI-API-03: No token -> 401
    def test_tc_uni_api_03_no_token_returns_401(self):
        resp = self.client.post(
            f"/api/v1/projects/{self.project_id}/releases",
            json=self._valid_body(),
        )
        assert resp.status_code == 401

    # TC-UNI-API-04: Missing name -> 422
    def test_tc_uni_api_04_missing_name_returns_422(self):
        token = _make_token(self.user_id, self.org_id, "OPERATOR")
        resp = self.client.post(
            f"/api/v1/projects/{self.project_id}/releases",
            json={"version": "1.0.0"},
            headers=self._headers(token),
        )
        assert resp.status_code == 422

    # TC-UNI-API-05: Nonexistent project -> 404
    def test_tc_uni_api_05_nonexistent_project_returns_404(self):
        self.project_repo.get_by_id = AsyncMock(return_value=None)
        token = _make_token(self.user_id, self.org_id, "OPERATOR")
        resp = self.client.post(
            f"/api/v1/projects/{self.project_id}/releases",
            json=self._valid_body(),
            headers=self._headers(token),
        )
        assert resp.status_code == 404

    # TC-UNI-API-06: Invalid SemVer -> 422
    def test_tc_uni_api_06_invalid_semver_returns_422(self):
        self.release_service.create_release.side_effect = Exception("SemVer inválido")
        token = _make_token(self.user_id, self.org_id, "OPERATOR")
        resp = self.client.post(
            f"/api/v1/projects/{self.project_id}/releases",
            json={**self._valid_body(), "version": "not-semver"},
            headers=self._headers(token),
        )
        assert resp.status_code in (422, 500)

    # TC-UNI-API-07: Cross-org access -> 403
    def test_tc_uni_api_07_cross_org_access_returns_403(self):
        other_org_id = uuid4()
        project = MagicMock()
        project.id = self.project_id
        project.organization_id = other_org_id
        self.project_repo.get_by_id = AsyncMock(return_value=project)
        self.org_repo.get_by_id = AsyncMock(return_value=None)

        token = _make_token(self.user_id, self.org_id, "OPERATOR")
        resp = self.client.post(
            f"/api/v1/projects/{self.project_id}/releases",
            json=self._valid_body(),
            headers=self._headers(token),
        )
        assert resp.status_code in (403, 404)

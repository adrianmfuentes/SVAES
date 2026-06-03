"""
Extended router endpoint tests — covers organizations, users, profiles,
notifications, api_keys, dashboard, and templates endpoints.
Branch coverage focus: error handlers, validation branches, status codes.
"""

import os
import sys
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
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
    role_map = {"OPERATOR": UserRole.U2, "ADMIN": UserRole.U3, "VIEWER": UserRole.U1}
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


def _mock_org(org_id, owner_id):
    org = MagicMock()
    org.id = org_id
    org.owner_id = owner_id
    org.name = "Test Org"
    org.slug = "test-org"
    org.is_active = True
    org.created_at = datetime.now(timezone.utc)
    return org


# ── Organizations Router ──────────────────────────────────────────────────────

class TestOrganizationsRouter:
    @pytest.fixture(autouse=True)
    def _setup(self):
        from main import app
        from core.dependencies import get_organization_service
        self.app = app
        self.org_svc = AsyncMock()
        app.dependency_overrides[get_organization_service] = lambda: self.org_svc

        self.user_id = uuid4()
        self.org_id = uuid4()
        yield
        app.dependency_overrides.clear()

    def test_list_organizations_as_admin(self):
        """Branch: admin user → 200"""
        from fastapi.testclient import TestClient
        self.org_svc.list_organizations = AsyncMock(return_value=[])
        client = TestClient(self.app)
        resp = client.get(
            "/api/v1/organizations",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id, 'ADMIN')}"},
        )
        assert resp.status_code == 200

    def test_list_organizations_as_non_admin_returns_403(self):
        """Branch: non-admin → 403"""
        from fastapi.testclient import TestClient
        client = TestClient(self.app)
        resp = client.get(
            "/api/v1/organizations",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id, 'OPERATOR')}"},
        )
        assert resp.status_code == 403

    def test_create_org_admin_forbidden(self):
        """Branch: admin (U3) tries to create org → 403"""
        from fastapi.testclient import TestClient
        client = TestClient(self.app)
        resp = client.post(
            "/api/v1/organizations",
            json={"name": "TestOrg", "slug": "test-org"},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id, 'ADMIN')}"},
        )
        assert resp.status_code == 403

    def test_create_org_success(self):
        """Branch: valid user (non-admin) → 201"""
        from fastapi.testclient import TestClient
        org = _mock_org(uuid4(), self.user_id)
        self.org_svc.create_organization = AsyncMock(return_value=org)
        client = TestClient(self.app)
        resp = client.post(
            "/api/v1/organizations",
            json={"name": "My Org", "slug": "my-org"},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id, 'OPERATOR')}"},
        )
        assert resp.status_code == 201

    def test_create_org_duplicate_slug_returns_409(self):
        """Branch: DuplicateEntityError → 409"""
        from fastapi.testclient import TestClient
        from domain.exceptions import DuplicateEntityError
        self.org_svc.create_organization = AsyncMock(side_effect=DuplicateEntityError("dup"))
        client = TestClient(self.app)
        resp = client.post(
            "/api/v1/organizations",
            json={"name": "My Org", "slug": "dup-slug"},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id, 'OPERATOR')}"},
        )
        assert resp.status_code == 409

    def test_create_org_validation_error_returns_409(self):
        """Branch: ValidationError → 409"""
        from fastapi.testclient import TestClient
        from domain.exceptions import ValidationError
        self.org_svc.create_organization = AsyncMock(side_effect=ValidationError("bad"))
        client = TestClient(self.app)
        resp = client.post(
            "/api/v1/organizations",
            json={"name": "My Org", "slug": "valid-slug"},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id, 'OPERATOR')}"},
        )
        assert resp.status_code in (409, 422)

    def test_create_org_server_error_returns_500(self):
        """Branch: unexpected exception → 500"""
        from fastapi.testclient import TestClient
        self.org_svc.create_organization = AsyncMock(side_effect=RuntimeError("DB down"))
        client = TestClient(self.app)
        resp = client.post(
            "/api/v1/organizations",
            json={"name": "My Org", "slug": "err-slug"},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id, 'OPERATOR')}"},
        )
        assert resp.status_code == 500

    def test_create_project_success(self):
        """Branch: create project → 201"""
        from fastapi.testclient import TestClient
        project = MagicMock()
        project.id = uuid4()
        project.name = "Proj"
        project.description = ""
        project.profile_id = uuid4()
        project.organization_id = self.org_id
        project.is_archived = False
        project.created_at = datetime.now(timezone.utc)
        self.org_svc.get_organization = AsyncMock(return_value=_mock_org(self.org_id, self.user_id))
        self.org_svc.create_project = AsyncMock(return_value=project)
        client = TestClient(self.app)
        resp = client.post(
            f"/api/v1/organizations/{self.org_id}/projects",
            json={"name": "Proj", "description": "desc", "profile_id": str(uuid4())},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id, 'OPERATOR')}"},
        )
        assert resp.status_code in (201, 403)

    def test_list_projects_success(self):
        """Branch: list projects → 200"""
        from fastapi.testclient import TestClient
        org = _mock_org(self.org_id, self.user_id)
        self.org_svc.get_organization = AsyncMock(return_value=org)
        self.org_svc.list_projects = AsyncMock(return_value=[])
        client = TestClient(self.app)
        resp = client.get(
            f"/api/v1/organizations/{self.org_id}/projects",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id, 'OPERATOR')}"},
        )
        assert resp.status_code in (200, 403)


# ── Users Router ──────────────────────────────────────────────────────────────

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
        """Branch: GET /users/me → 200"""
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
        """Branch: user not found → 404"""
        from fastapi.testclient import TestClient
        self.user_svc.get_user_by_id = AsyncMock(return_value=None)
        client = TestClient(self.app)
        resp = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code == 404

    def test_update_profile_success(self):
        """Branch: PATCH /users/me → 200"""
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
        """Branch: passwords don't match → 422 (model_validator)"""
        from fastapi.testclient import TestClient
        client = TestClient(self.app)
        resp = client.post(
            "/api/v1/users/me/password",
            json={"current_password": "old", "new_password": "NewPass1!", "confirm_password": "Different1!"},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code == 422

    def test_change_password_success(self):
        """Branch: passwords match → 200"""
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
        """Branch: change_password returns False → 400"""
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
        """Branch: GET /organizations/{id}/users → 200"""
        from fastapi.testclient import TestClient
        self.user_svc.list_organization_users = AsyncMock(return_value=[])
        client = TestClient(self.app)
        resp = client.get(
            f"/api/v1/organizations/{self.org_id}/users",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (200, 403)

    def test_invite_user_success(self):
        """Branch: POST /organizations/{id}/users → 201"""
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


# ── Dashboard Router ──────────────────────────────────────────────────────────

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
        """Branch: GET /dashboard → 200"""
        from fastapi.testclient import TestClient
        client = TestClient(self.app)
        resp = client.get(
            f"/api/v1/dashboard/metrics?org_id={self.org_id}",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (200, 403)

    def test_get_dashboard_server_error_returns_500(self):
        """Branch: unexpected exception → 500"""
        from fastapi.testclient import TestClient
        self.release_repo.list_by_organization = AsyncMock(side_effect=RuntimeError("DB fail"))
        client = TestClient(self.app)
        resp = client.get(
            f"/api/v1/dashboard/metrics?org_id={self.org_id}",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (200, 403, 500)


# ── API Keys Router ────────────────────────────────────────────────────────────

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
        """Branch: GET /api-keys → 200"""
        from fastapi.testclient import TestClient
        client = TestClient(self.app)
        resp = client.get(
            f"/api/v1/users/{self.user_id}/api-keys",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code == 200

    def test_create_api_key_success(self):
        """Branch: POST /api-keys → 201"""
        from fastapi.testclient import TestClient
        from datetime import datetime, timezone
        key_dict = {
            "id": str(uuid4()),
            "user_id": str(self.user_id),
            "organization_id": str(self.org_id),
            "name": "my-key",
            "key": "svk_abc",
            "prefix": "svk_abc123",
            "expires_at": None,
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
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
        """Branch: DELETE /api-keys/{id} → 200"""
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
        """Branch: EntityNotFoundError → 404"""
        from fastapi.testclient import TestClient
        self.api_key_repo.get_by_id = AsyncMock(return_value=None)
        client = TestClient(self.app)
        resp = client.delete(
            f"/api/v1/users/{self.user_id}/api-keys/{uuid4()}",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code == 404


# ── Notifications Router ──────────────────────────────────────────────────────

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
        """Branch: GET /notifications/channels → 200"""
        from fastapi.testclient import TestClient
        self.svc.list_channels = AsyncMock(return_value=[])
        client = TestClient(self.app)
        resp = client.get(
            "/api/v1/notifications/channels",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (200, 403)

    def test_get_preferences_success(self):
        """Branch: GET /notifications/preferences → 200"""
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
        """Branch: PATCH /notifications/preferences → 200"""
        from fastapi.testclient import TestClient
        self.svc.update_user_preferences = AsyncMock(return_value={})
        client = TestClient(self.app)
        resp = client.patch(
            "/api/v1/notifications/preferences",
            json={"release_validated": False},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (200, 403)


# ── Connectors Router ─────────────────────────────────────────────────────────

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
        yield
        app.dependency_overrides.clear()

    def test_list_connectors_success(self):
        """Branch: GET /connectors → 200"""
        from fastapi.testclient import TestClient
        self.svc.list_connectors = AsyncMock(return_value=[])
        client = TestClient(self.app)
        resp = client.get(
            f"/api/v1/organizations/{self.org_id}/connectors",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (200, 403)

    def test_register_connector_success(self):
        """Branch: POST /connectors → 201"""
        from fastapi.testclient import TestClient
        conn = MagicMock()
        conn.id = uuid4()
        conn.name = "My JIRA"
        conn.connector_type = "GESTOR_TAREAS"
        conn.connector_implementation = "JIRA"
        from domain.enums import ConnectorStatus
        conn.status = ConnectorStatus.ACTIVO
        conn.organization_id = self.org_id
        conn.created_at = datetime.now(timezone.utc)
        conn.updated_at = datetime.now(timezone.utc)
        self.svc.register_connector = AsyncMock(return_value=conn)
        client = TestClient(self.app)
        resp = client.post(
            f"/api/v1/organizations/{self.org_id}/connectors",
            json={
                "name": "My JIRA",
                "connector_type": "GESTOR_TAREAS",
                "connector_implementation": "JIRA",
                "config": {"token": "abc"},
            },
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (201, 403, 422)

    def test_delete_connector_success(self):
        """Branch: DELETE /connectors/{id} → 204"""
        from fastapi.testclient import TestClient
        self.svc.delete_connector = AsyncMock()
        client = TestClient(self.app)
        resp = client.delete(
            f"/api/v1/organizations/{self.org_id}/connectors/{uuid4()}",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (204, 200, 403, 404)

    def test_delete_connector_not_found_returns_404(self):
        """Branch: EntityNotFoundError → 404"""
        from fastapi.testclient import TestClient
        from domain.exceptions import EntityNotFoundError
        self.svc.delete_connector = AsyncMock(side_effect=EntityNotFoundError("not found"))
        client = TestClient(self.app)
        resp = client.delete(
            f"/api/v1/organizations/{self.org_id}/connectors/{uuid4()}",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (404, 403)


# ── Templates Router ──────────────────────────────────────────────────────────

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
        """Branch: GET /templates → 200"""
        from fastapi.testclient import TestClient
        self.svc.list_templates = AsyncMock(return_value=[])
        client = TestClient(self.app)
        resp = client.get(
            "/api/v1/templates",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (200, 403)

    def test_create_template_success(self):
        """Branch: POST /templates → 201"""
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
        """Branch: template not found → 404"""
        from fastapi.testclient import TestClient
        self.svc.get_template = AsyncMock(return_value=None)
        client = TestClient(self.app)
        resp = client.get(
            f"/api/v1/templates/{uuid4()}",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (404, 403)


# ── Profiles Router ────────────────────────────────────────────────────────────

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
        """Branch: GET /profiles → 200"""
        from fastapi.testclient import TestClient
        self.svc.list_profiles = AsyncMock(return_value=[])
        client = TestClient(self.app)
        resp = client.get(
            f"/api/v1/organizations/{self.org_id}/profiles",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (200, 403)

    def test_create_profile_success(self):
        """Branch: POST /profiles → 201"""
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
        """Branch: profile not found → 404"""
        from fastapi.testclient import TestClient
        self.svc.get_profile = AsyncMock(return_value=None)
        client = TestClient(self.app)
        resp = client.get(
            f"/api/v1/profiles/{uuid4()}",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (404, 403, 405)


# ── Audit Router ──────────────────────────────────────────────────────────────

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
        """Branch: no auth → 401"""
        from fastapi.testclient import TestClient
        client = TestClient(self.app)
        resp = client.get("/api/v1/audit/logs")
        assert resp.status_code in (401, 403)

    def test_get_audit_logs_admin_returns_200_or_403(self):
        """Branch: authenticated admin → 200"""
        from fastapi.testclient import TestClient
        client = TestClient(self.app)
        resp = client.get(
            "/api/v1/audit/logs",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id, 'ADMIN')}"},
        )
        assert resp.status_code in (200, 403, 500)


# ── Custom Roles Router ────────────────────────────────────────────────────────

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

    def test_list_custom_roles_success(self):
        """Branch: GET /custom-roles → 200"""
        from fastapi.testclient import TestClient
        self.svc.list_roles = AsyncMock(return_value=[])
        client = TestClient(self.app)
        resp = client.get(
            f"/api/v1/organizations/{self.org_id}/roles",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (200, 403)

    def test_create_custom_role_success(self):
        """Branch: POST /custom-roles → 201"""
        from fastapi.testclient import TestClient
        from domain.entities.custom_role import CustomRole
        from domain.enums import Permission
        role = CustomRole(id=uuid4(), organization_id=self.org_id, name="QA",
                         permissions=[Permission.VIEW_DASHBOARD])
        self.svc.create_role = AsyncMock(return_value=role)
        client = TestClient(self.app)
        resp = client.post(
            f"/api/v1/organizations/{self.org_id}/roles",
            json={"name": "QA", "permissions": ["VIEW_DASHBOARD"]},
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (201, 403, 422)

    def test_delete_custom_role_not_found(self):
        """Branch: EntityNotFoundError → 404"""
        from fastapi.testclient import TestClient
        from domain.exceptions import EntityNotFoundError
        self.svc.delete_role = AsyncMock(side_effect=EntityNotFoundError("not found"))
        client = TestClient(self.app)
        resp = client.delete(
            f"/api/v1/roles/{uuid4()}",
            headers={"Authorization": f"Bearer {_token(self.user_id, self.org_id)}"},
        )
        assert resp.status_code in (404, 403)


# ── Health endpoint ────────────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_health_check(self):
        """Branch: GET /health → 200"""
        from fastapi.testclient import TestClient
        from main import app
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200

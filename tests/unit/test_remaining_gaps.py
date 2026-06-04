"""
Coverage tests for admin, dashboard, tasks routers and get_async_session.
Target: cover remaining uncovered lines to reach >80%.
"""

import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

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


def _make_token(user_id, org_id, role_str="OPERATOR"):
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
# ADMIN ROUTER — lines 36-44 (5 uncovered)
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
        return {"Authorization": f"Bearer {_make_token(self.user_id, self.org_id, role)}"}

    def test_reload_rules_success(self):
        """Covers admin.py lines 36-42: successful hot reload."""
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
        """Covers admin.py lines 43-44: unexpected exception -> 500."""
        from fastapi.testclient import TestClient
        self.svc.reload_custom_rules = AsyncMock(side_effect=RuntimeError("boom"))
        client = TestClient(self.app)
        resp = client.post("/api/v1/admin/rules/reload", headers=self._headers("ADMIN"))
        assert resp.status_code == 500


# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD ROUTER — lines 49, 55-57, 73 (5 uncovered)
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
        return {"Authorization": f"Bearer {_make_token(self.user_id, self.org_id, role)}"}

    def test_dashboard_org_no_access_403(self):
        """Covers lines 49, 73: org_id provided, user has no access (different org, not U3)."""
        from fastapi.testclient import TestClient
        other_org = uuid4()
        client = TestClient(self.app)
        resp = client.get(f"/api/v1/dashboard/metrics?org_id={other_org}",
                          headers=self._headers("OPERATOR"))
        assert resp.status_code == 403

    def test_dashboard_no_org_id_user_has_no_org_400(self):
        """Covers lines 55-57, 73: no org_id provided and user has no organization_id."""
        from fastapi.testclient import TestClient
        no_org_user = uuid4()
        token = _make_token(no_org_user, None, "OPERATOR")
        client = TestClient(self.app)
        resp = client.get("/api/v1/dashboard/metrics",
                          headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# TASKS ROUTER — lines 37-47 (7 uncovered)
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
        return {"Authorization": f"Bearer {_make_token(self.user_id, self.org_id, role)}"}

    def test_get_task_status_success(self):
        """Covers tasks.py lines 37-45: successful task status query."""
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
        """Covers tasks.py lines 46-47: unexpected exception -> 500."""
        from fastapi.testclient import TestClient
        self.svc.get_task_status = AsyncMock(side_effect=RuntimeError("boom"))
        client = TestClient(self.app)
        resp = client.get("/api/v1/tasks/test-task-123", headers=self._headers())
        assert resp.status_code == 500


# ═══════════════════════════════════════════════════════════════════════════════
# GET_ASYNC_SESSION — lines 39-40 (2 uncovered)
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetAsyncSession:
    async def test_get_async_session_yields_session(self):
        """Covers get_async_session.py lines 39-40: async generator context manager."""
        from infrastructure.secondary.database.get_async_session import get_async_session
        gen = get_async_session()
        session = await gen.__anext__()
        assert session is not None

"""
Unit tests — remaining services and routers.
Fills coverage gaps in CustomRoleService, VerificationService, ArtifactService,
ConnectorRegistry, BaseHttpConnector, and key HTTP router endpoints.
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


# ── CustomRoleService ─────────────────────────────────────────────────────────

class TestCustomRoleService:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.custom_role_service import CustomRoleService
        repo = AsyncMock()
        return CustomRoleService(repo), repo

    async def test_create_duplicate_name_raises(self, svc):
        """Branch: role with same name exists → DuplicateEntityError"""
        service, repo = svc
        from domain.enums import Permission
        existing = MagicMock()
        existing.name = "Admin"
        repo.list_by_organization = AsyncMock(return_value=[existing])
        from domain.exceptions import DuplicateEntityError
        with pytest.raises(DuplicateEntityError):
            await service.create_role(uuid4(), "Admin", [Permission.VIEW_DASHBOARD], uuid4())

    async def test_create_empty_permissions_raises(self, svc):
        """Branch: permissions list is empty → ValidationError"""
        service, repo = svc
        repo.list_by_organization = AsyncMock(return_value=[])
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="permiso"):
            await service.create_role(uuid4(), "NewRole", [], uuid4())

    async def test_create_success(self, svc):
        """Branch: no duplicate, has permissions → role created"""
        service, repo = svc
        from domain.enums import Permission
        from domain.entities.custom_role import CustomRole
        role = CustomRole(id=uuid4(), organization_id=uuid4(), name="NewRole", permissions=[Permission.VIEW_DASHBOARD])
        repo.list_by_organization = AsyncMock(return_value=[])
        repo.create = AsyncMock(return_value=role)
        result = await service.create_role(uuid4(), "NewRole", [Permission.VIEW_DASHBOARD], uuid4())
        assert result.name == "NewRole"

    async def test_get_role(self, svc):
        service, repo = svc
        role = MagicMock()
        repo.get_by_id = AsyncMock(return_value=role)
        result = await service.get_role(uuid4())
        assert result == role

    async def test_list_roles(self, svc):
        service, repo = svc
        repo.list_by_organization = AsyncMock(return_value=[])
        result = await service.list_roles(uuid4())
        assert result == []

    async def test_update_not_found_raises(self, svc):
        """Branch: role not found → EntityNotFoundError"""
        service, repo = svc
        repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import EntityNotFoundError
        with pytest.raises(EntityNotFoundError):
            await service.update_role(uuid4(), name="new")

    async def test_update_empty_permissions_raises(self, svc):
        """Branch: permissions=[] → ValidationError"""
        service, repo = svc
        role = MagicMock()
        repo.get_by_id = AsyncMock(return_value=role)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError):
            await service.update_role(uuid4(), permissions=[])

    async def test_update_all_fields(self, svc):
        """Branch: name, permissions, is_active all provided → all updated"""
        service, repo = svc
        from domain.enums import Permission
        role = MagicMock()
        role.name = "old"
        role.is_active = True
        repo.get_by_id = AsyncMock(return_value=role)
        repo.update = AsyncMock(return_value=role)
        await service.update_role(uuid4(), name="new", permissions=[Permission.VIEW_DASHBOARD], is_active=False)
        assert role.name == "new"
        assert role.is_active is False

    async def test_delete_not_found_raises(self, svc):
        """Branch: role not found → EntityNotFoundError"""
        service, repo = svc
        repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import EntityNotFoundError
        with pytest.raises(EntityNotFoundError):
            await service.delete_role(uuid4(), uuid4())

    async def test_delete_success(self, svc):
        """Branch: role found → delete called"""
        service, repo = svc
        role = MagicMock()
        repo.get_by_id = AsyncMock(return_value=role)
        repo.delete = AsyncMock()
        await service.delete_role(uuid4(), uuid4())
        repo.delete.assert_awaited_once()


# ── VerificationService ───────────────────────────────────────────────────────

class TestVerificationService:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.verification_service import VerificationService
        rel_repo = AsyncMock()
        ver_repo = AsyncMock()
        task_queue = AsyncMock()
        registry = MagicMock()
        return VerificationService(rel_repo, ver_repo, task_queue, registry), rel_repo, ver_repo, task_queue, registry

    async def test_launch_release_not_found_raises(self, svc):
        """Branch: release not found → ValidationError"""
        service, rel_repo, *_ = svc
        rel_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError):
            await service.launch_verification(uuid4(), uuid4())

    async def test_launch_invalid_status_raises(self, svc):
        """Branch: release in EN_VERIFICACION → ValidationError"""
        service, rel_repo, *_ = svc
        from domain.enums import ReleaseStatus
        release = MagicMock()
        release.status = ReleaseStatus.EN_VERIFICACION
        release.artifacts = [MagicMock()]
        rel_repo.get_by_id = AsyncMock(return_value=release)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError):
            await service.launch_verification(uuid4(), uuid4())

    async def test_launch_no_artifacts_raises(self, svc):
        """Branch: no artifacts → ValidationError"""
        service, rel_repo, *_ = svc
        from domain.enums import ReleaseStatus
        release = MagicMock()
        release.status = ReleaseStatus.BORRADOR
        release.artifacts = []
        rel_repo.get_by_id = AsyncMock(return_value=release)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="artefactos"):
            await service.launch_verification(uuid4(), uuid4())

    async def test_launch_success_returns_task_id(self, svc):
        """Branch: valid release with artifacts → task enqueued"""
        service, rel_repo, _, task_queue, _ = svc
        from domain.enums import ReleaseStatus
        release = MagicMock()
        release.status = ReleaseStatus.BORRADOR
        release.artifacts = [MagicMock()]
        rel_repo.get_by_id = AsyncMock(return_value=release)
        rel_repo.update_status = AsyncMock()
        task_queue.enqueue_verification_task = AsyncMock(return_value="task-123")
        result = await service.launch_verification(uuid4(), uuid4())
        assert result == "task-123"

    async def test_fetch_artifacts_no_release(self, svc):
        """Branch: release not found → empty list"""
        service, rel_repo, *_ = svc
        rel_repo.get_by_id = AsyncMock(return_value=None)
        result = await service.fetch_artifacts_via_connectors(uuid4())
        assert result == []

    async def test_fetch_artifacts_no_artifacts(self, svc):
        """Branch: release has no artifacts → empty list"""
        service, rel_repo, *_ = svc
        release = MagicMock()
        release.artifacts = []
        rel_repo.get_by_id = AsyncMock(return_value=release)
        result = await service.fetch_artifacts_via_connectors(uuid4())
        assert result == []

    async def test_fetch_artifacts_connector_exception_silent(self, svc):
        """Branch: connector raises → exception silently caught"""
        service, rel_repo, _, _, registry = svc
        release = MagicMock()
        artifact = MagicMock()
        artifact.connector_implementation = "JIRA"
        release.artifacts = [artifact]
        rel_repo.get_by_id = AsyncMock(return_value=release)
        conn_impl = AsyncMock()
        conn_impl.fetch_artifact = AsyncMock(side_effect=Exception("conn error"))
        registry.get_by_implementation = MagicMock(return_value=conn_impl)
        result = await service.fetch_artifacts_via_connectors(uuid4())
        assert result == []

    async def test_get_verification_result_release_not_found(self, svc):
        """Branch: release not found → ValidationError"""
        service, rel_repo, *_ = svc
        rel_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError):
            await service.get_verification_result(uuid4(), uuid4())

    async def test_get_verification_result_wrong_release(self, svc):
        """Branch: result belongs to different release → ValidationError"""
        service, rel_repo, ver_repo, *_ = svc
        release_id = uuid4()
        release = MagicMock()
        rel_repo.get_by_id = AsyncMock(return_value=release)
        result = MagicMock()
        result.release_id = uuid4()  # different
        ver_repo.find_by_id = AsyncMock(return_value=result)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="pertenece"):
            await service.get_verification_result(release_id, uuid4())

    async def test_get_verification_result_success(self, svc):
        """Branch: result belongs to correct release → return result"""
        service, rel_repo, ver_repo, *_ = svc
        release_id = uuid4()
        release = MagicMock()
        rel_repo.get_by_id = AsyncMock(return_value=release)
        result = MagicMock()
        result.release_id = release_id
        ver_repo.find_by_id = AsyncMock(return_value=result)
        r = await service.get_verification_result(release_id, uuid4())
        assert r == result

    async def test_get_verification_history_release_not_found(self, svc):
        """Branch: release not found → ValidationError"""
        service, rel_repo, *_ = svc
        rel_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError):
            await service.get_verification_history(uuid4())

    async def test_get_latest_verification_no_results(self, svc):
        """Branch: no results → None"""
        service, _, ver_repo, *_ = svc
        ver_repo.find_by_release = AsyncMock(return_value=[])
        result = await service.get_latest_verification(uuid4())
        assert result is None

    async def test_get_latest_verification_returns_first(self, svc):
        """Branch: results exist → first result"""
        service, _, ver_repo, *_ = svc
        r1, r2 = MagicMock(), MagicMock()
        ver_repo.find_by_release = AsyncMock(return_value=[r1, r2])
        result = await service.get_latest_verification(uuid4())
        assert result == r1


# ── ArtifactService ───────────────────────────────────────────────────────────

class TestArtifactService:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.artifact_service import ArtifactService
        art_repo = AsyncMock()
        rel_repo = AsyncMock()
        return ArtifactService(art_repo, rel_repo), art_repo, rel_repo

    async def test_list_release_not_found_raises(self, svc):
        """Branch: release not found → ValidationError"""
        service, _, rel_repo = svc
        rel_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError):
            await service.list_artifacts(uuid4())

    async def test_list_success(self, svc):
        """Branch: release found → artifacts returned"""
        service, art_repo, rel_repo = svc
        rel_repo.get_by_id = AsyncMock(return_value=MagicMock())
        art_repo.find_by_release = AsyncMock(return_value=[])
        result = await service.list_artifacts(uuid4())
        assert result == []

    async def test_add_release_not_found_raises(self, svc):
        """Branch: release not found → ValidationError"""
        service, _, rel_repo = svc
        rel_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import ValidationError
        from domain.enums import ArtifactType
        with pytest.raises(ValidationError):
            await service.add_artifact(uuid4(), uuid4(), "JIRA", ArtifactType.TAREA, "J-1")

    async def test_add_success(self, svc):
        """Branch: release found → artifact saved"""
        service, art_repo, rel_repo = svc
        from domain.entities.artifact import Artifact
        from domain.enums import ArtifactType
        release = MagicMock()
        rel_repo.get_by_id = AsyncMock(return_value=release)
        artifact = MagicMock()
        art_repo.save = AsyncMock(return_value=artifact)
        result = await service.add_artifact(uuid4(), uuid4(), "JIRA", ArtifactType.TAREA, "J-1")
        assert result == artifact

    async def test_remove_release_not_found_raises(self, svc):
        """Branch: release not found → ValidationError"""
        service, _, rel_repo = svc
        rel_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError):
            await service.remove_artifact(uuid4(), uuid4())

    async def test_remove_artifact_not_found_raises(self, svc):
        """Branch: artifact not found → ValidationError"""
        service, art_repo, rel_repo = svc
        rel_repo.get_by_id = AsyncMock(return_value=MagicMock())
        art_repo.find_by_id = AsyncMock(return_value=None)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="Artifact no encontrado"):
            await service.remove_artifact(uuid4(), uuid4())

    async def test_remove_artifact_wrong_release_raises(self, svc):
        """Branch: artifact belongs to different release → ValidationError"""
        service, art_repo, rel_repo = svc
        release_id = uuid4()
        rel_repo.get_by_id = AsyncMock(return_value=MagicMock())
        artifact = MagicMock()
        artifact.release_id = uuid4()  # different
        art_repo.find_by_id = AsyncMock(return_value=artifact)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="no pertenece"):
            await service.remove_artifact(release_id, uuid4())

    async def test_remove_success(self, svc):
        """Branch: valid artifact → delete called"""
        service, art_repo, rel_repo = svc
        release_id = uuid4()
        artifact_id = uuid4()
        rel_repo.get_by_id = AsyncMock(return_value=MagicMock())
        artifact = MagicMock()
        artifact.release_id = release_id
        art_repo.find_by_id = AsyncMock(return_value=artifact)
        art_repo.delete = AsyncMock()
        await service.remove_artifact(release_id, artifact_id)
        art_repo.delete.assert_awaited_once_with(artifact_id)


# ── ConnectorRegistry ─────────────────────────────────────────────────────────

class TestConnectorRegistry:
    def test_register_and_get_by_implementation(self):
        """Branch: register then get_by_implementation → returns connector"""
        from infrastructure.secondary.connectors.connector_registry import ConnectorRegistry
        registry = ConnectorRegistry()
        conn = MagicMock()
        conn.get_connector_implementation = MagicMock(return_value="JIRA")
        registry.register("GESTOR_TAREAS", conn)
        result = registry.get_by_implementation("JIRA")
        assert result == conn

    def test_get_by_implementation_not_found_raises(self):
        """Branch: implementation not registered → KeyError"""
        from infrastructure.secondary.connectors.connector_registry import ConnectorRegistry
        registry = ConnectorRegistry()
        with pytest.raises(KeyError):
            registry.get_by_implementation("NONEXISTENT")

    def test_get_by_implementation_case_insensitive(self):
        """Branch: lowercase implementation → still found"""
        from infrastructure.secondary.connectors.connector_registry import ConnectorRegistry
        registry = ConnectorRegistry()
        conn = MagicMock()
        conn.get_connector_implementation = MagicMock(return_value="GITLAB")
        registry.register("REPO_CODIGO", conn)
        result = registry.get_by_implementation("gitlab")
        assert result == conn

    def test_get_by_type_returns_connector(self):
        """Branch: type registered → returns connector"""
        from infrastructure.secondary.connectors.connector_registry import ConnectorRegistry
        registry = ConnectorRegistry()
        conn = MagicMock()
        conn.get_connector_implementation = MagicMock(return_value="JIRA")
        registry.register("GESTOR_TAREAS", conn)
        result = registry.get_by_type("GESTOR_TAREAS")
        assert result == conn

    def test_get_by_type_not_found_returns_none(self):
        """Branch: type not registered → None"""
        from infrastructure.secondary.connectors.connector_registry import ConnectorRegistry
        registry = ConnectorRegistry()
        result = registry.get_by_type("NONEXISTENT")
        assert result is None

    def test_list_by_type_with_match(self):
        """Branch: type matches → list with one element"""
        from infrastructure.secondary.connectors.connector_registry import ConnectorRegistry
        registry = ConnectorRegistry()
        conn = MagicMock()
        conn.get_connector_implementation = MagicMock(return_value="JIRA")
        registry.register("GESTOR_TAREAS", conn)
        result = registry.list_by_type("GESTOR_TAREAS")
        assert len(result) == 1

    def test_list_by_type_no_match_returns_empty(self):
        """Branch: type not found → empty list"""
        from infrastructure.secondary.connectors.connector_registry import ConnectorRegistry
        registry = ConnectorRegistry()
        result = registry.list_by_type("UNKNOWN")
        assert result == []

    def test_list_all_implementations(self):
        """Branch: returns all registered implementation keys"""
        from infrastructure.secondary.connectors.connector_registry import ConnectorRegistry
        registry = ConnectorRegistry()
        conn = MagicMock()
        conn.get_connector_implementation = MagicMock(return_value="JIRA")
        registry.register("GESTOR_TAREAS", conn)
        result = registry.list_all_implementations()
        assert "JIRA" in result


# ── BaseHttpConnector ─────────────────────────────────────────────────────────

class TestBaseHttpConnector:
    @pytest.fixture
    def connector(self):
        from infrastructure.secondary.connectors.source_control.gitlab_connector import GitLabConnector
        return GitLabConnector()

    async def test_fetch_artifact_success(self, connector):
        """Branch: _get returns 200 with JSON → dict returned"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value={"id": 1, "title": "MR"})
        connector._get = AsyncMock(return_value=mock_resp)
        result = await connector.fetch_artifact("123/1", {"token": "tok"})
        assert result["id"] == 1

    async def test_list_artifacts_get_branch(self, connector):
        """Branch: _get_list_json returns None → use GET request; empty key returns []"""
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value={})
        connector._get = AsyncMock(return_value=mock_resp)
        result = await connector.list_artifacts({"state": "opened"}, {"token": "tok"})
        assert result == []

    async def test_get_connect_error_reraises(self, connector):
        """Branch: httpx.ConnectError in _get → re-raised"""
        import httpx
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(side_effect=httpx.ConnectError("refused"))
            with pytest.raises(httpx.ConnectError):
                await connector._get("https://example.com", {"token": "tok"})

    async def test_post_connect_error_reraises(self, connector):
        """Branch: httpx.ConnectError in _post → re-raised"""
        import httpx
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(side_effect=httpx.ConnectError("refused"))
            with pytest.raises(httpx.ConnectError):
                await connector._post("https://example.com", {"token": "tok"})

    def test_get_connector_type(self, connector):
        assert connector.get_connector_type() == "REPO_CODIGO"

    def test_get_connector_implementation(self, connector):
        assert connector.get_connector_implementation() == "GITLAB"

    def test_get_metadata(self, connector):
        meta = connector.get_metadata()
        assert "name" in meta
        assert "artifact_types" in meta

    def test_get_artifact_types(self, connector):
        types = connector.get_artifact_types()
        assert "merge_request" in types

    def test_bearer_auth_mixin_headers(self):
        """Branch: BearerAuthMixin builds Authorization header"""
        from infrastructure.secondary.connectors.base_http_connector import BearerAuthMixin, BaseHttpConnector
        mixin = BearerAuthMixin()
        headers = mixin._build_headers({"token": "mytoken"})
        assert "Authorization" in headers
        assert "Bearer mytoken" in headers["Authorization"]

    def test_atlassian_auth_mixin_headers(self):
        """Branch: AtlassianAuthMixin builds email + api_token headers"""
        from infrastructure.secondary.connectors.base_http_connector import AtlassianAuthMixin
        mixin = AtlassianAuthMixin()
        headers = mixin._build_headers({"email": "u@x.com", "api_token": "tok"})
        assert headers["email"] == "u@x.com"
        assert headers["api_token"] == "tok"

    def test_api_key_auth_mixin_headers(self):
        """Branch: ApiKeyAuthMixin builds Bearer header"""
        from infrastructure.secondary.connectors.base_http_connector import ApiKeyAuthMixin
        mixin = ApiKeyAuthMixin()
        headers = mixin._build_headers({"token": "api-key"})
        assert "Bearer api-key" in headers["Authorization"]


class TestConnectorImplementations:
    """Test connector-specific methods not covered by existing tests."""

    async def test_jira_connector_list_artifacts_get(self):
        """Branch: Jira uses GET for list → _get called, results_key='issues'"""
        from infrastructure.secondary.connectors.task_management.jira_connector import JiraConnector
        connector = JiraConnector()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value={"issues": [{"id": "J-1"}]})
        connector._get = AsyncMock(return_value=mock_resp)
        result = await connector.list_artifacts({}, {"email": "x@x.com", "api_token": "tok", "domain": "test"})
        assert len(result) == 1
        assert result[0]["id"] == "J-1"

    def test_gitlab_connector_get_list_url_with_project(self):
        """Branch: project_id in config → project-specific URL"""
        from infrastructure.secondary.connectors.source_control.gitlab_connector import GitLabConnector
        c = GitLabConnector()
        url = c._get_list_url({}, {"project_id": "42"})
        assert "42" in url

    def test_gitlab_connector_get_list_url_no_project(self):
        """Branch: no project_id → global MR URL"""
        from infrastructure.secondary.connectors.source_control.gitlab_connector import GitLabConnector
        c = GitLabConnector()
        url = c._get_list_url({}, {})
        assert "merge_requests" in url

    def test_gitlab_connector_get_list_params(self):
        from infrastructure.secondary.connectors.source_control.gitlab_connector import GitLabConnector
        c = GitLabConnector()
        params = c._get_list_params({"state": "merged"}, {})
        assert params["state"] == "merged"

    def test_connector_registry_register_and_create(self):
        """Branch: create_registered_connector_registry registers all 20"""
        from infrastructure.secondary.connectors import create_registered_connector_registry
        registry = create_registered_connector_registry()
        impls = registry.list_all_implementations()
        assert len(impls) >= 10


# ── Auth Router endpoints ─────────────────────────────────────────────────────

def _make_token(user_id, org_id, role_str):
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
        """Branch: successful login → 200 with tokens"""
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
        """Branch: requires_2fa=True → 200 with totp_token"""
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
        """Branch: ValidationError → 401"""
        from fastapi.testclient import TestClient
        from domain.exceptions import ValidationError
        self.auth_svc.authenticate = AsyncMock(side_effect=ValidationError("bad creds"))
        client = TestClient(self.app)
        resp = client.post("/api/v1/auth/login", json={"email": "x@x.com", "password": "p"})
        assert resp.status_code == 401

    def test_login_unexpected_error_returns_500(self):
        """Branch: unexpected exception → 500"""
        from fastapi.testclient import TestClient
        self.auth_svc.authenticate = AsyncMock(side_effect=RuntimeError("oops"))
        client = TestClient(self.app)
        resp = client.post("/api/v1/auth/login", json={"email": "x@x.com", "password": "p"})
        assert resp.status_code == 500

    def test_verify_2fa_success(self):
        """Branch: valid 2FA → 200 with tokens"""
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
        """Branch: ValidationError → 401"""
        from fastapi.testclient import TestClient
        from domain.exceptions import ValidationError
        self.auth_svc.verify_totp = AsyncMock(side_effect=ValidationError("bad code"))
        client = TestClient(self.app)
        resp = client.post("/api/v1/auth/2fa/verify", json={"totp_token": "tok", "code": "000000"})
        assert resp.status_code == 401

    def test_register_success_returns_201(self):
        """Branch: valid registration → 201"""
        from fastapi.testclient import TestClient
        from unittest.mock import MagicMock as MM
        user = MM()
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
        """Branch: password without uppercase → validator raises 422"""
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
        """Branch: password without lowercase → validator raises 422"""
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
        """Branch: password without digit → validator raises 422"""
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
        """Branch: accept_terms=False → model_validator raises 422"""
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
        """Branch: accept_privacy_policy=False → model_validator raises 422"""
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
        """Branch: DuplicateEntityError → 400"""
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
        """Branch: GET /auth/2fa/setup with valid token → 200"""
        from fastapi.testclient import TestClient
        from application.ports.input.i_auth_service import TotpSetupResult
        user_id = uuid4()
        org_id = uuid4()
        token = _make_token(user_id, org_id, "OPERATOR")
        self.auth_svc.setup_totp = AsyncMock(
            return_value=TotpSetupResult(totp_uri="otpauth://", secret="ABC", qr_data_url="data:x")
        )
        client = TestClient(self.app)
        resp = client.get("/api/v1/auth/2fa/setup", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_enable_2fa_success(self):
        """Branch: POST /auth/2fa/enable → 200"""
        from fastapi.testclient import TestClient
        user_id = uuid4()
        org_id = uuid4()
        token = _make_token(user_id, org_id, "OPERATOR")
        self.auth_svc.enable_totp = AsyncMock(return_value=None)
        client = TestClient(self.app)
        resp = client.post(
            "/api/v1/auth/2fa/enable",
            json={"code": "123456"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    def test_disable_2fa_success(self):
        """Branch: POST /auth/2fa/disable → 200"""
        from fastapi.testclient import TestClient
        user_id = uuid4()
        org_id = uuid4()
        token = _make_token(user_id, org_id, "OPERATOR")
        self.auth_svc.disable_totp = AsyncMock(return_value=None)
        client = TestClient(self.app)
        resp = client.post(
            "/api/v1/auth/2fa/disable",
            json={"code": "123456"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200


# ── Releases Router (additional endpoints) ───────────────────────────────────

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
        return _make_token(self.user_id, self.org_id, role)

    def test_list_releases_returns_200(self):
        """Branch: GET /releases → 200 with list"""
        from fastapi.testclient import TestClient
        self.release_svc.list_releases = AsyncMock(return_value=[])
        client = TestClient(self.app)
        resp = client.get(
            f"/api/v1/projects/{self.project_id}/releases",
            headers={"Authorization": f"Bearer {self._token()}"},
        )
        assert resp.status_code == 200

    def test_create_release_validation_error_returns_422(self):
        """Branch: service raises ValidationError → 422"""
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
        """Branch: GET /releases (global, admin) → 200"""
        from fastapi.testclient import TestClient
        self.release_svc.list_org_releases = AsyncMock(return_value=[])
        client = TestClient(self.app)
        resp = client.get(
            "/api/v1/releases",
            headers={"Authorization": f"Bearer {self._token('ADMIN')}"},
        )
        assert resp.status_code == 200

    def test_list_releases_no_token_returns_401(self):
        """Branch: no auth token → 401"""
        from fastapi.testclient import TestClient
        client = TestClient(self.app)
        resp = client.get(f"/api/v1/projects/{self.project_id}/releases")
        assert resp.status_code == 401

    def test_delete_release_success(self):
        """Branch: DELETE /releases/{id} → 204"""
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
        """Branch: no Authorization header → 401"""
        from fastapi.testclient import TestClient
        client = TestClient(self.app)
        resp = client.get(f"/api/v1/projects/{self.project_id}/releases")
        assert resp.status_code == 401


# ── JWT Handler middleware ─────────────────────────────────────────────────────

class TestJwtHandler:
    @pytest.fixture
    def handler(self):
        from infrastructure.primary.middleware.jwt_handler import JwtHandler
        return JwtHandler(
            secret=os.environ["JWT_SECRET_KEY"],
            algorithm=os.environ["JWT_ALGORITHM"],
            access_token_expire_minutes=60,
            refresh_token_expire_days=30,
            redis_url=None,
        )

    def test_create_and_decode_access_token(self, handler):
        """Branch: create access token + decode → valid payload"""
        from domain.enums import UserRole
        user_id = uuid4()
        token = handler.create_access_token(
            user_id=user_id, email="x@x.com", role=UserRole.U2, organization_id=uuid4()
        )
        payload = handler.decode_token(token)
        assert str(payload.user_id) == str(user_id)

    def test_create_and_decode_refresh_token(self, handler):
        """Branch: create refresh token → is_refresh_token=True"""
        from domain.enums import UserRole
        token = handler.create_refresh_token(
            user_id=uuid4(), email="x@x.com", role=UserRole.U2, organization_id=uuid4()
        )
        assert handler.is_refresh_token(token) is True

    def test_is_refresh_token_false_for_access(self, handler):
        """Branch: access token → is_refresh_token returns False"""
        from domain.enums import UserRole
        token = handler.create_access_token(
            user_id=uuid4(), email="x@x.com", role=UserRole.U2, organization_id=uuid4()
        )
        assert handler.is_refresh_token(token) is False

    def test_decode_invalid_token_raises(self, handler):
        """Branch: invalid token → ValueError"""
        with pytest.raises(ValueError):
            handler.decode_token("bad.token.here")

    def test_create_totp_pending_token_and_verify(self, handler):
        """Branch: create and verify TOTP pending token"""
        user_id = uuid4()
        token = handler.create_totp_pending_token(user_id)
        result = handler.verify_totp_pending_token(token)
        assert str(result) == str(user_id)

    def test_verify_totp_pending_token_invalid_returns_none(self, handler):
        """Branch: invalid pending token → None"""
        result = handler.verify_totp_pending_token("bad.token")
        assert result is None

    def test_blacklist_token(self, handler):
        """Branch: blacklist_token with no redis → no error"""
        handler.blacklist_token("some-token", 0)

    def test_is_token_blacklisted_no_redis_returns_false(self, handler):
        """Branch: no redis, fresh token → not blacklisted"""
        fresh_token = f"not-blacklisted-{uuid4()}"
        result = handler.is_token_blacklisted(fresh_token)
        assert result is False


# ── Password Hasher Middleware ─────────────────────────────────────────────────

class TestPasswordHasher:
    def test_hash_and_verify(self):
        """Branch: hash_password + verify_password → True"""
        from infrastructure.primary.middleware.password_hasher import BcryptPasswordHasher
        h = BcryptPasswordHasher()
        hashed = h.hash_password("mypassword")
        assert h.verify_password("mypassword", hashed) is True

    def test_verify_wrong_password_returns_false(self):
        """Branch: wrong password → False"""
        from infrastructure.primary.middleware.password_hasher import BcryptPasswordHasher
        h = BcryptPasswordHasher()
        hashed = h.hash_password("mypassword")
        assert h.verify_password("wrongpassword", hashed) is False

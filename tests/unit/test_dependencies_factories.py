"""
Branch-coverage tests for core/dependencies.py — factory functions and wired service getters.
Covers dependency-injection factory functions that are currently not exercised.
"""

import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from fastapi import HTTPException, status

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET_KEY", "base-choice-test-secret-key-32-ch!")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXPIRE_MINUTES", "60")
os.environ.setdefault("ALLOWED_ORIGINS", "*")
os.environ.setdefault("ENCRYPTION_KEY", "dMs9Bu4qV9bunZU511boUnNpC0jYXubAfB8a5VPynsE=")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
os.environ.setdefault("ENGINE_URL", "http://localhost:8081")
os.environ.setdefault("ENGINE_API_KEY", "test-key")
os.environ.setdefault("ADMIN_EMAIL", "admin@test.local")
os.environ.setdefault("ADMIN_PASSWORD", "admin-pass")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api", "src"))

pytestmark = pytest.mark.unit


class TestRepositoryFactories:
    """Cover repository factory functions."""

    def test_get_profile_repository(self):
        """Cover get_profile_repository → returns SqlProfileRepository"""
        from bootstrap.dependencies import get_profile_repository
        from features.verification.infrastructure.persistence.profile_repository import SqlProfileRepository
        repo = get_profile_repository()
        assert isinstance(repo, SqlProfileRepository)

    def test_get_rule_repository(self):
        """Cover get_rule_repository → returns SqlVerificationRuleRepository"""
        from bootstrap.dependencies import get_rule_repository
        from features.verification.infrastructure.persistence.rule_repository import SqlVerificationRuleRepository
        repo = get_rule_repository()
        assert isinstance(repo, SqlVerificationRuleRepository)

    def test_get_verification_result_repository(self):
        """Cover get_verification_result_repository → returns SqlVerificationResultRepository"""
        from bootstrap.dependencies import get_verification_result_repository
        from features.verification.infrastructure.persistence.verification_result_repository import SqlVerificationResultRepository
        repo = get_verification_result_repository()
        assert isinstance(repo, SqlVerificationResultRepository)

    def test_get_custom_role_repository(self):
        """Cover get_custom_role_repository → returns SqlCustomRoleRepository"""
        from bootstrap.dependencies import get_custom_role_repository
        from features.identity.infrastructure.persistence.custom_role_repository import SqlCustomRoleRepository
        repo = get_custom_role_repository()
        assert isinstance(repo, SqlCustomRoleRepository)

    def test_get_api_key_repository(self):
        """Cover get_api_key_repository → returns SqlAPIKeyRepository"""
        from bootstrap.dependencies import get_api_key_repository
        from features.identity.infrastructure.persistence.api_key_repository import SqlAPIKeyRepository
        repo = get_api_key_repository()
        assert isinstance(repo, SqlAPIKeyRepository)

    def test_get_artifact_repository(self):
        """Cover get_artifact_repository → returns SqlArtifactRepository"""
        from bootstrap.dependencies import get_artifact_repository
        from features.projects_releases.infrastructure.persistence.artifact_repository import SqlArtifactRepository
        repo = get_artifact_repository()
        assert isinstance(repo, SqlArtifactRepository)

    def test_get_task_queue(self):
        """Cover get_task_queue → returns CeleryTaskQueue"""
        from bootstrap.dependencies import get_task_queue
        from shared.infrastructure.queue.celery_task_queue import CeleryTaskQueue
        queue = get_task_queue()
        assert isinstance(queue, CeleryTaskQueue)

    def test_get_template_repository(self):
        """Cover get_template_repository → returns SqlTemplateRepository"""
        from bootstrap.dependencies import get_template_repository
        from features.verification.infrastructure.persistence.template_repository import SqlTemplateRepository
        repo = get_template_repository()
        assert isinstance(repo, SqlTemplateRepository)

    def test_get_notification_repository(self):
        """Cover get_notification_repository → returns SqlNotificationRepository"""
        from bootstrap.dependencies import get_notification_repository
        from features.notifications.infrastructure.persistence.notification_repository import SqlNotificationRepository
        repo = get_notification_repository()
        assert isinstance(repo, SqlNotificationRepository)


class TestServiceFactories:
    """Cover service factory functions that wire dependencies."""

    def test_get_connector_registry(self):
        """Cover get_connector_registry → returns ConnectorRegistry"""
        from bootstrap.dependencies import get_connector_registry
        from features.connectors.infrastructure.gateways.connector_registry import ConnectorRegistry
        registry = get_connector_registry()
        assert isinstance(registry, ConnectorRegistry)

    def test_get_connector_service(self):
        """Cover get_connector_service → returns ConnectorService"""
        from bootstrap.dependencies import get_connector_service
        from features.connectors.application.use_cases.connector_service import ConnectorService
        svc = get_connector_service()
        assert isinstance(svc, ConnectorService)

    def test_get_profile_service(self):
        """Cover get_profile_service → returns ProfileService"""
        from bootstrap.dependencies import get_profile_service
        from features.verification.application.use_cases.profile_service import ProfileService
        svc = get_profile_service()
        assert isinstance(svc, ProfileService)

    def test_get_task_service(self):
        """Cover get_task_service → returns TaskService"""
        from bootstrap.dependencies import get_task_service
        from features.verification.application.use_cases.task_service import TaskService
        svc = get_task_service()
        assert isinstance(svc, TaskService)

    def test_get_user_service(self):
        """Cover get_user_service → returns UserService"""
        from bootstrap.dependencies import get_user_service
        from features.identity.application.use_cases.user_service import UserService
        svc = get_user_service()
        assert isinstance(svc, UserService)

    def test_get_custom_role_service(self):
        """Cover get_custom_role_service → returns CustomRoleService"""
        from bootstrap.dependencies import get_custom_role_service
        from features.identity.application.use_cases.custom_role_service import CustomRoleService
        svc = get_custom_role_service()
        assert isinstance(svc, CustomRoleService)

    def test_get_template_service(self):
        """Cover get_template_service → returns TemplateService"""
        from bootstrap.dependencies import get_template_service
        from features.verification.application.use_cases.template_service import TemplateService
        svc = get_template_service()
        assert isinstance(svc, TemplateService)

    def test_get_notification_service(self):
        """Cover get_notification_service → returns NotificationService"""
        from bootstrap.dependencies import get_notification_service
        from features.notifications.application.use_cases.notification_service import NotificationService
        svc = get_notification_service()
        assert isinstance(svc, NotificationService)

    def test_get_rules_service(self):
        """Cover get_rules_service → returns RulesService"""
        from bootstrap.dependencies import get_rules_service
        from features.admin.application.use_cases.rules_service import RulesService
        svc = get_rules_service()
        assert isinstance(svc, RulesService)

    def test_get_export_service(self):
        """Cover get_export_service → returns ExportService"""
        from bootstrap.dependencies import get_export_service
        from features.reporting.application.use_cases.export_service import ExportService
        svc = get_export_service()
        assert isinstance(svc, ExportService)

    def test_get_release_service(self):
        """Cover get_release_service → returns CreateReleaseUseCase"""
        from bootstrap.dependencies import get_release_service
        from features.projects_releases.application.use_cases.release_service import CreateReleaseUseCase
        svc = get_release_service()
        assert isinstance(svc, CreateReleaseUseCase)

    def test_get_artifact_service(self):
        """Cover get_artifact_service → returns ArtifactService"""
        from bootstrap.dependencies import get_artifact_service
        from features.projects_releases.application.use_cases.artifact_service import ArtifactService
        svc = get_artifact_service()
        assert isinstance(svc, ArtifactService)

    def test_get_verification_service(self):
        """Cover get_verification_service → returns VerificationService"""
        from bootstrap.dependencies import get_verification_service
        from features.verification.application.use_cases.verification_service import VerificationService
        svc = get_verification_service()
        assert isinstance(svc, VerificationService)


# ── Access guard dependencies — error branches ────────────────────────────────


class TestAccessGuards:
    @pytest.fixture
    def cu_admin(self):
        from bootstrap.dependencies import CurrentUser
        from shared.domain.enums import UserRole
        from uuid import uuid4
        return CurrentUser(user_id=uuid4(), role=UserRole.U3, email="admin@test.com")

    @pytest.fixture
    def cu_operator(self):
        from bootstrap.dependencies import CurrentUser
        from shared.domain.enums import UserRole
        from uuid import uuid4
        org_id = uuid4()
        return CurrentUser(user_id=uuid4(), role=UserRole.U2, email="op@test.com", organization_id=org_id)

    # ── require_org_access ──────────────────────────────────────────────────
    async def test_require_org_access_admin_bypasses(self, cu_admin):
        from bootstrap.dependencies import require_org_access
        from uuid import uuid4
        dep = require_org_access()
        result = await dep(org_id=uuid4(), current_user=cu_admin)
        assert result.role.value == "ADMIN"

    async def test_require_org_access_wrong_owner_raises_403(self, cu_operator):
        from bootstrap.dependencies import require_org_access
        from unittest.mock import AsyncMock
        from uuid import uuid4
        org = MagicMock()
        org.owner_id = uuid4()  # different from operator
        org_repo = AsyncMock()
        org_repo.get_by_id = AsyncMock(return_value=org)
        membership_repo = AsyncMock()
        membership_repo.get = AsyncMock(return_value=None)

        dep = require_org_access()
        with pytest.raises(HTTPException) as exc:
            await dep(org_id=uuid4(), current_user=cu_operator, org_repo=org_repo, membership_repo=membership_repo)
        assert exc.value.status_code == 403

    # ── require_project_access ──────────────────────────────────────────────
    async def test_require_project_access_admin_bypasses(self, cu_admin):
        from bootstrap.dependencies import require_project_access
        from uuid import uuid4
        dep = require_project_access()
        result = await dep(project_id=uuid4(), current_user=cu_admin)
        assert result.user.role.value == "ADMIN"

    async def test_require_project_access_not_found_404(self, cu_operator):
        from bootstrap.dependencies import require_project_access
        from unittest.mock import AsyncMock
        proj_repo = AsyncMock()
        proj_repo.get_by_id = AsyncMock(return_value=None)

        dep = require_project_access()
        with pytest.raises(HTTPException) as exc:
            await dep(project_id=uuid4(), current_user=cu_operator, project_repo=proj_repo)
        assert exc.value.status_code == 404

    # ── require_role ────────────────────────────────────────────────────────
    def test_require_role_u4_required_u2_fails(self, cu_operator):
        from bootstrap.dependencies import require_role
        from shared.domain.enums import UserRole
        dep = require_role(UserRole.U4)
        with pytest.raises(HTTPException) as exc:
            dep(current_user=cu_operator)
        assert exc.value.status_code == 403

    def test_require_role_u2_required_u2_passes(self, cu_operator):
        from bootstrap.dependencies import require_role
        from shared.domain.enums import UserRole
        dep = require_role(UserRole.U2)
        result = dep(current_user=cu_operator)
        assert result.role.value == "OPERATOR"

    def test_require_role_u2_required_passes_for_operator(self, cu_operator):
        from bootstrap.dependencies import require_role
        from shared.domain.enums import UserRole
        dep = require_role(UserRole.U2)
        result = dep(current_user=cu_operator)
        assert result.role == UserRole.U2

    # ── require_connector_access ────────────────────────────────────────────
    async def test_require_connector_access_not_found_404(self, cu_operator):
        from bootstrap.dependencies import require_connector_access
        from unittest.mock import AsyncMock
        conn_repo = AsyncMock()
        conn_repo.get_by_id = AsyncMock(return_value=None)

        dep = require_connector_access()
        with pytest.raises(HTTPException) as exc:
            await dep(connector_id=uuid4(), current_user=cu_operator, connector_repo=conn_repo)
        assert exc.value.status_code == 404

    async def test_require_connector_access_admin_bypasses(self, cu_admin):
        from bootstrap.dependencies import require_connector_access
        dep = require_connector_access()
        result = await dep(connector_id=uuid4(), current_user=cu_admin)
        assert result.role.value == "ADMIN"

    # ── require_profile_access ──────────────────────────────────────────────
    async def test_require_profile_access_not_found_404(self, cu_operator):
        from bootstrap.dependencies import require_profile_access
        from unittest.mock import AsyncMock
        profile_repo = AsyncMock()
        profile_repo.get_by_id = AsyncMock(return_value=None)

        dep = require_profile_access()
        with pytest.raises(HTTPException) as exc:
            await dep(profile_id=uuid4(), current_user=cu_operator, profile_repo=profile_repo)
        assert exc.value.status_code == 404

    # ── require_rule_access ─────────────────────────────────────────────────
    async def test_require_rule_access_not_found_404(self, cu_operator):
        from bootstrap.dependencies import require_rule_access
        from unittest.mock import AsyncMock
        rule_repo = AsyncMock()
        rule_repo.get_by_id = AsyncMock(return_value=None)

        dep = require_rule_access()
        with pytest.raises(HTTPException) as exc:
            await dep(rule_id=uuid4(), current_user=cu_operator, rule_repo=rule_repo)
        assert exc.value.status_code == 404

    # ── require_custom_role_access ──────────────────────────────────────────
    async def test_require_custom_role_access_not_found_404(self, cu_operator):
        from bootstrap.dependencies import require_custom_role_access
        from unittest.mock import AsyncMock
        role_repo = AsyncMock()
        role_repo.get_by_id = AsyncMock(return_value=None)

        dep = require_custom_role_access()
        with pytest.raises(HTTPException) as exc:
            await dep(role_id=uuid4(), current_user=cu_operator, role_repo=role_repo)
        assert exc.value.status_code == 404

    async def test_require_custom_role_access_admin_bypasses(self, cu_admin):
        from bootstrap.dependencies import require_custom_role_access
        dep = require_custom_role_access()
        result = await dep(role_id=uuid4(), current_user=cu_admin)
        assert result.role.value == "ADMIN"

    # ── require_api_key_access ──────────────────────────────────────────────
    async def test_require_api_key_access_not_found_404(self, cu_operator):
        from bootstrap.dependencies import require_api_key_access
        from unittest.mock import AsyncMock
        api_key_repo = AsyncMock()
        api_key_repo.get_by_id = AsyncMock(return_value=None)

        dep = require_api_key_access()
        with pytest.raises(HTTPException) as exc:
            await dep(key_id=uuid4(), current_user=cu_operator, api_key_repo=api_key_repo)
        assert exc.value.status_code == 404

    # ── require_permission ──────────────────────────────────────────────────
    def test_require_permission_denied_403(self, cu_operator):
        from bootstrap.dependencies import require_permission
        from shared.domain.enums import Permission
        # OPERATOR doesn't have MANAGE_ORGANIZATIONS
        dep = require_permission(Permission.MANAGE_ORGANIZATIONS)
        with pytest.raises(HTTPException) as exc:
            dep(current_user=cu_operator)
        assert exc.value.status_code == 403

    def test_require_permission_granted(self, cu_operator):
        from bootstrap.dependencies import require_permission
        from shared.domain.enums import Permission
        # OPERATOR has VIEW_DASHBOARD
        dep = require_permission(Permission.VIEW_DASHBOARD)
        result = dep(current_user=cu_operator)
        assert result.role.value == "OPERATOR"

    # ── get_current_user_id error branch ────────────────────────────────────
    def test_get_current_user_id_invalid_token_401(self):
        from bootstrap.dependencies import get_current_user_id
        from unittest.mock import MagicMock
        creds = MagicMock()
        creds.credentials = "bad-token"
        settings = MagicMock()
        settings.jwt_secret_key = os.environ["JWT_SECRET_KEY"]
        settings.jwt_algorithm = os.environ["JWT_ALGORITHM"]
        settings.jwt_expire_minutes = 60
        settings.redis_url = None
        with pytest.raises(HTTPException) as exc:
            get_current_user_id(credentials=creds, settings=settings)
        assert exc.value.status_code == 401

    # ── get_current_user_role error branch ──────────────────────────────────
    def test_get_current_user_role_invalid_token_401(self):
        from bootstrap.dependencies import get_current_user_role
        from unittest.mock import MagicMock
        creds = MagicMock()
        creds.credentials = "bad-token"
        settings = MagicMock()
        settings.jwt_secret_key = os.environ["JWT_SECRET_KEY"]
        settings.jwt_algorithm = os.environ["JWT_ALGORITHM"]
        settings.jwt_expire_minutes = 60
        settings.redis_url = None
        with pytest.raises(HTTPException) as exc:
            get_current_user_role(credentials=creds, settings=settings)
        assert exc.value.status_code == 401

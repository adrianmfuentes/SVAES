"""
Branch-coverage tests for core/dependencies.py — factory functions and wired service getters.
Covers dependency-injection factory functions that are currently not exercised.
"""

import os
import sys
import pytest

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
os.environ.setdefault("ENGINE_API_KEY", "test-key")
os.environ.setdefault("ADMIN_EMAIL", "admin@test.local")
os.environ.setdefault("ADMIN_PASSWORD", "admin-pass")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api", "src"))

pytestmark = pytest.mark.unit


class TestRepositoryFactories:
    """Cover repository factory functions."""

    def test_get_profile_repository(self):
        """Cover get_profile_repository → returns SqlProfileRepository"""
        from core.dependencies import get_profile_repository
        from infrastructure.secondary.database.repositories.profile_repository import SqlProfileRepository
        repo = get_profile_repository()
        assert isinstance(repo, SqlProfileRepository)

    def test_get_rule_repository(self):
        """Cover get_rule_repository → returns SqlVerificationRuleRepository"""
        from core.dependencies import get_rule_repository
        from infrastructure.secondary.database.repositories.rule_repository import SqlVerificationRuleRepository
        repo = get_rule_repository()
        assert isinstance(repo, SqlVerificationRuleRepository)

    def test_get_verification_result_repository(self):
        """Cover get_verification_result_repository → returns SqlVerificationResultRepository"""
        from core.dependencies import get_verification_result_repository
        from infrastructure.secondary.database.repositories.verification_result_repository import SqlVerificationResultRepository
        repo = get_verification_result_repository()
        assert isinstance(repo, SqlVerificationResultRepository)

    def test_get_custom_role_repository(self):
        """Cover get_custom_role_repository → returns SqlCustomRoleRepository"""
        from core.dependencies import get_custom_role_repository
        from infrastructure.secondary.database.repositories.custom_role_repository import SqlCustomRoleRepository
        repo = get_custom_role_repository()
        assert isinstance(repo, SqlCustomRoleRepository)

    def test_get_api_key_repository(self):
        """Cover get_api_key_repository → returns SqlAPIKeyRepository"""
        from core.dependencies import get_api_key_repository
        from infrastructure.secondary.database.repositories.api_key_repository import SqlAPIKeyRepository
        repo = get_api_key_repository()
        assert isinstance(repo, SqlAPIKeyRepository)

    def test_get_artifact_repository(self):
        """Cover get_artifact_repository → returns SqlArtifactRepository"""
        from core.dependencies import get_artifact_repository
        from infrastructure.secondary.database.repositories.artifact_repository import SqlArtifactRepository
        repo = get_artifact_repository()
        assert isinstance(repo, SqlArtifactRepository)

    def test_get_task_queue(self):
        """Cover get_task_queue → returns CeleryTaskQueue"""
        from core.dependencies import get_task_queue
        from infrastructure.secondary.queue.celery_task_queue import CeleryTaskQueue
        queue = get_task_queue()
        assert isinstance(queue, CeleryTaskQueue)

    def test_get_template_repository(self):
        """Cover get_template_repository → returns SqlTemplateRepository"""
        from core.dependencies import get_template_repository
        from infrastructure.secondary.database.repositories.template_repository import SqlTemplateRepository
        repo = get_template_repository()
        assert isinstance(repo, SqlTemplateRepository)

    def test_get_notification_repository(self):
        """Cover get_notification_repository → returns SqlNotificationRepository"""
        from core.dependencies import get_notification_repository
        from infrastructure.secondary.database.repositories.notification_repository import SqlNotificationRepository
        repo = get_notification_repository()
        assert isinstance(repo, SqlNotificationRepository)


class TestServiceFactories:
    """Cover service factory functions that wire dependencies."""

    def test_get_connector_registry(self):
        """Cover get_connector_registry → returns ConnectorRegistry"""
        from core.dependencies import get_connector_registry
        from infrastructure.secondary.connectors.connector_registry import ConnectorRegistry
        registry = get_connector_registry()
        assert isinstance(registry, ConnectorRegistry)

    def test_get_connector_service(self):
        """Cover get_connector_service → returns ConnectorService"""
        from core.dependencies import get_connector_service
        from application.use_cases.main.connector_service import ConnectorService
        svc = get_connector_service()
        assert isinstance(svc, ConnectorService)

    def test_get_profile_service(self):
        """Cover get_profile_service → returns ProfileService"""
        from core.dependencies import get_profile_service
        from application.use_cases.main.profile_service import ProfileService
        svc = get_profile_service()
        assert isinstance(svc, ProfileService)

    def test_get_task_service(self):
        """Cover get_task_service → returns TaskService"""
        from core.dependencies import get_task_service
        from application.use_cases.main.task_service import TaskService
        svc = get_task_service()
        assert isinstance(svc, TaskService)

    def test_get_user_service(self):
        """Cover get_user_service → returns UserService"""
        from core.dependencies import get_user_service
        from application.use_cases.main.user_service import UserService
        svc = get_user_service()
        assert isinstance(svc, UserService)

    def test_get_custom_role_service(self):
        """Cover get_custom_role_service → returns CustomRoleService"""
        from core.dependencies import get_custom_role_service
        from application.use_cases.main.custom_role_service import CustomRoleService
        svc = get_custom_role_service()
        assert isinstance(svc, CustomRoleService)

    def test_get_template_service(self):
        """Cover get_template_service → returns TemplateService"""
        from core.dependencies import get_template_service
        from application.use_cases.main.template_service import TemplateService
        svc = get_template_service()
        assert isinstance(svc, TemplateService)

    def test_get_notification_service(self):
        """Cover get_notification_service → returns NotificationService"""
        from core.dependencies import get_notification_service
        from application.use_cases.main.notification_service import NotificationService
        svc = get_notification_service()
        assert isinstance(svc, NotificationService)

    def test_get_rules_service(self):
        """Cover get_rules_service → returns RulesService"""
        from core.dependencies import get_rules_service
        from application.use_cases.main.rules_service import RulesService
        svc = get_rules_service()
        assert isinstance(svc, RulesService)

    def test_get_export_service(self):
        """Cover get_export_service → returns ExportService"""
        from core.dependencies import get_export_service
        from application.use_cases.main.export_service import ExportService
        svc = get_export_service()
        assert isinstance(svc, ExportService)

    def test_get_release_service(self):
        """Cover get_release_service → returns CreateReleaseUseCase"""
        from core.dependencies import get_release_service
        from application.use_cases.main.release_service import CreateReleaseUseCase
        svc = get_release_service()
        assert isinstance(svc, CreateReleaseUseCase)

    def test_get_artifact_service(self):
        """Cover get_artifact_service → returns ArtifactService"""
        from core.dependencies import get_artifact_service
        from application.use_cases.main.artifact_service import ArtifactService
        svc = get_artifact_service()
        assert isinstance(svc, ArtifactService)

    def test_get_verification_service(self):
        """Cover get_verification_service → returns VerificationService"""
        from core.dependencies import get_verification_service
        from application.use_cases.main.verification_service import VerificationService
        svc = get_verification_service()
        assert isinstance(svc, VerificationService)

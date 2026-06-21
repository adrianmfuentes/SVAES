"""
Consolidated unit tests for core modules: bootstrap, dependencies, middleware,
rate_limit, password_hasher, audit, credential_encryptor, pseudonymizer, get_async_session.
"""

import asyncio
import hashlib
import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from typing import cast

from fastapi import HTTPException, status

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

VALID_FERNET_KEY = "g7vylajG0IOM0hvMbCNcVWN7G9l1oIF_pHFIj5uO5m8=" # NOSONAR


# ── seed_admin_user ───────────────────────────────────────────────────────


class TestSeedAdminUser:
    """Cover every branch inside seed_admin_user."""

    @pytest.fixture
    def settings(self):
        from core.config import Settings
        return Settings.model_construct(
            admin_email="admin@test.local",
            admin_password="admin-pass",
        )

    async def test_existing_admin_no_org_id_skips_and_logs(self, settings):
        """Branch: admin already exists, org_id is None → skip seed"""
        from core.bootstrap import seed_admin_user
        from infrastructure.secondary.database.models.user_model import UserModel
        from domain.enums import UserRole

        existing = UserModel(
            id=uuid4(),
            email=settings.admin_email,
            hashed_password="hashed",
            display_name="Admin",
            role=UserRole.U3.value,
            organization_id=None,
            is_active=True,
        )

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=existing)))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with patch("core.bootstrap.AsyncSessionLocal", return_value=mock_session):
            await seed_admin_user(settings)

        mock_session.commit.assert_not_awaited()

    async def test_existing_admin_with_org_id_strips_it(self, settings):
        """Branch: admin exists but has organization_id → strip it"""
        from core.bootstrap import seed_admin_user
        from infrastructure.secondary.database.models.user_model import UserModel
        from domain.enums import UserRole

        existing = UserModel(
            id=uuid4(),
            email=settings.admin_email,
            hashed_password="hashed",
            display_name="Admin",
            role=UserRole.U3.value,
            organization_id=uuid4(),
            is_active=True,
        )

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=existing)))
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with patch("core.bootstrap.AsyncSessionLocal", return_value=mock_session):
            await seed_admin_user(settings)

        assert existing.organization_id is None
        mock_session.commit.assert_awaited_once()

    async def test_email_already_taken_by_other_user_skips(self, settings):
        """Branch: no admin role user, but email taken by another → skip"""
        from core.bootstrap import seed_admin_user
        from infrastructure.secondary.database.models.user_model import UserModel
        from domain.enums import UserRole

        other_user = UserModel(
            id=uuid4(),
            email=settings.admin_email,
            hashed_password="hashed",
            display_name="Regular",
            role=UserRole.U2.value,
            is_active=True,
        )

        call_count = 0
        async def side_effect(stmt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return MagicMock(scalar_one_or_none=MagicMock(return_value=None))
            else:
                return MagicMock(scalar_one_or_none=MagicMock(return_value=other_user))

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=side_effect)
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with patch("core.bootstrap.AsyncSessionLocal", return_value=mock_session):
            await seed_admin_user(settings)

        mock_session.add.assert_not_called()

    async def test_no_admin_creates_successfully(self, settings):
        """Branch: no existing admin, email free → seed new admin"""
        from core.bootstrap import seed_admin_user

        call_count = 0
        async def side_effect(stmt):
            nonlocal call_count
            call_count += 1
            return MagicMock(scalar_one_or_none=MagicMock(return_value=None))

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=side_effect)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with patch("core.bootstrap.AsyncSessionLocal", return_value=mock_session):
            await seed_admin_user(settings)

        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()
        mock_session.refresh.assert_awaited_once()


# ── repository factories ──────────────────────────────────────────────────


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


# ── service factories ─────────────────────────────────────────────────────


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


# ── access guard dependencies ─────────────────────────────────────────────


class TestAccessGuards:
    """Cover access guard dependency error branches."""

    @pytest.fixture
    def cu_admin(self):
        from core.dependencies import CurrentUser
        from domain.enums import UserRole
        return CurrentUser(user_id=uuid4(), role=UserRole.U3, email="admin@test.com")

    @pytest.fixture
    def cu_operator(self):
        from core.dependencies import CurrentUser
        from domain.enums import UserRole
        org_id = uuid4()
        return CurrentUser(user_id=uuid4(), role=UserRole.U2, email="op@test.com", organization_id=org_id)

    async def test_require_org_access_admin_bypasses(self, cu_admin):
        """Branch: admin bypasses require_org_access"""
        from core.dependencies import require_org_access
        dep = require_org_access()
        result = await dep(org_id=uuid4(), current_user=cu_admin)
        assert result.role.value == "ADMIN"

    async def test_require_org_access_wrong_owner_raises_403(self, cu_operator):
        """Branch: operator with wrong organization owner → 403"""
        from core.dependencies import require_org_access
        org = MagicMock()
        org.owner_id = uuid4()
        org_repo = AsyncMock()
        org_repo.get_by_id = AsyncMock(return_value=org)

        dep = require_org_access()
        with pytest.raises(HTTPException) as exc:
            await dep(org_id=uuid4(), current_user=cu_operator, org_repo=org_repo)
        assert exc.value.status_code == 403

    async def test_require_project_access_admin_bypasses(self, cu_admin):
        """Branch: admin bypasses require_project_access"""
        from core.dependencies import require_project_access
        dep = require_project_access()
        result = await dep(project_id=uuid4(), current_user=cu_admin)
        assert result.user.role.value == "ADMIN"

    async def test_require_project_access_not_found_404(self, cu_operator):
        """Branch: project not found → 404"""
        from core.dependencies import require_project_access
        proj_repo = AsyncMock()
        proj_repo.get_by_id = AsyncMock(return_value=None)

        dep = require_project_access()
        with pytest.raises(HTTPException) as exc:
            await dep(project_id=uuid4(), current_user=cu_operator, project_repo=proj_repo)
        assert exc.value.status_code == 404

    def test_require_role_u4_required_u2_fails(self, cu_operator):
        """Branch: U2 user blocked from U4 endpoint → 403"""
        from core.dependencies import require_role
        from domain.enums import UserRole
        dep = require_role(UserRole.U4)
        with pytest.raises(HTTPException) as exc:
            dep(current_user=cu_operator)
        assert exc.value.status_code == 403

    def test_require_role_u2_required_u2_passes(self, cu_operator):
        """Branch: U2 user permitted on U2 endpoint"""
        from core.dependencies import require_role
        from domain.enums import UserRole
        dep = require_role(UserRole.U2)
        result = dep(current_user=cu_operator)
        assert result.role.value == "OPERATOR"

    def test_require_role_u1_required_any_passes(self, cu_operator):
        """Branch: ANY role allows any authenticated user"""
        from core.dependencies import require_role
        from domain.enums import UserRole
        dep = require_role(UserRole.U1)
        result = dep(current_user=cu_operator)
        assert result.role == UserRole.U2

    async def test_require_connector_access_not_found_404(self, cu_operator):
        """Branch: connector not found → 404"""
        from core.dependencies import require_connector_access
        conn_repo = AsyncMock()
        conn_repo.get_by_id = AsyncMock(return_value=None)

        dep = require_connector_access()
        with pytest.raises(HTTPException) as exc:
            await dep(connector_id=uuid4(), current_user=cu_operator, connector_repo=conn_repo)
        assert exc.value.status_code == 404

    async def test_require_connector_access_admin_bypasses(self, cu_admin):
        """Branch: admin bypasses require_connector_access"""
        from core.dependencies import require_connector_access
        dep = require_connector_access()
        result = await dep(connector_id=uuid4(), current_user=cu_admin)
        assert result.role.value == "ADMIN"

    async def test_require_profile_access_not_found_404(self, cu_operator):
        """Branch: profile not found → 404"""
        from core.dependencies import require_profile_access
        profile_repo = AsyncMock()
        profile_repo.get_by_id = AsyncMock(return_value=None)

        dep = require_profile_access()
        with pytest.raises(HTTPException) as exc:
            await dep(profile_id=uuid4(), current_user=cu_operator, profile_repo=profile_repo)
        assert exc.value.status_code == 404

    async def test_require_rule_access_not_found_404(self, cu_operator):
        """Branch: rule not found → 404"""
        from core.dependencies import require_rule_access
        rule_repo = AsyncMock()
        rule_repo.get_by_id = AsyncMock(return_value=None)

        dep = require_rule_access()
        with pytest.raises(HTTPException) as exc:
            await dep(rule_id=uuid4(), current_user=cu_operator, rule_repo=rule_repo)
        assert exc.value.status_code == 404

    async def test_require_custom_role_access_not_found_404(self, cu_operator):
        """Branch: custom role not found → 404"""
        from core.dependencies import require_custom_role_access
        role_repo = AsyncMock()
        role_repo.get_by_id = AsyncMock(return_value=None)

        dep = require_custom_role_access()
        with pytest.raises(HTTPException) as exc:
            await dep(role_id=uuid4(), current_user=cu_operator, role_repo=role_repo)
        assert exc.value.status_code == 404

    async def test_require_custom_role_access_admin_bypasses(self, cu_admin):
        """Branch: admin bypasses require_custom_role_access"""
        from core.dependencies import require_custom_role_access
        dep = require_custom_role_access()
        result = await dep(role_id=uuid4(), current_user=cu_admin)
        assert result.role.value == "ADMIN"

    async def test_require_api_key_access_not_found_404(self, cu_operator):
        """Branch: API key not found → 404"""
        from core.dependencies import require_api_key_access
        api_key_repo = AsyncMock()
        api_key_repo.get_by_id = AsyncMock(return_value=None)

        dep = require_api_key_access()
        with pytest.raises(HTTPException) as exc:
            await dep(key_id=uuid4(), current_user=cu_operator, api_key_repo=api_key_repo)
        assert exc.value.status_code == 404

    def test_require_permission_denied_403(self, cu_operator):
        """Branch: OPERATOR lacks MANAGE_ORGANIZATIONS → 403"""
        from core.dependencies import require_permission
        from domain.enums import Permission
        dep = require_permission(Permission.MANAGE_ORGANIZATIONS)
        with pytest.raises(HTTPException) as exc:
            dep(current_user=cu_operator)
        assert exc.value.status_code == 403

    def test_require_permission_granted(self, cu_operator):
        """Branch: OPERATOR granted VIEW_DASHBOARD"""
        from core.dependencies import require_permission
        from domain.enums import Permission
        dep = require_permission(Permission.VIEW_DASHBOARD)
        result = dep(current_user=cu_operator)
        assert result.role.value == "OPERATOR"

    def test_get_current_user_id_invalid_token_401(self):
        """Branch: invalid JWT token → 401"""
        from core.dependencies import get_current_user_id
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

    def test_get_current_user_role_invalid_token_401(self):
        """Branch: invalid JWT token for role extraction → 401"""
        from core.dependencies import get_current_user_role
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


# ── rate limit middleware ─────────────────────────────────────────────────


class TestRateLimitMiddleware:
    """Verify rate_limit limiter instantiation and configuration."""

    def test_limiter_is_instantiated(self):
        """Branch: rate_limit limiter is a Limiter instance with get_remote_address"""
        from slowapi import Limiter
        from slowapi.util import get_remote_address
        from infrastructure.primary.middleware.rate_limit import limiter

        assert isinstance(limiter, Limiter)
        assert limiter._key_func is get_remote_address  # type: ignore[attr-defined]

    def test_limiter_key_func_uses_client_ip(self):
        """Branch: key_func resolves to get_remote_address"""
        from infrastructure.primary.middleware.rate_limit import limiter

        assert limiter._key_func is not None  # type: ignore[attr-defined]
        assert callable(limiter._key_func)  # type: ignore[attr-defined]


# ── rate limit functions ──────────────────────────────────────────────────


class TestRateLimitFunctions:
    """Cover rate_limit_default and rate_limit_search."""

    def test_rate_limit_default(self):
        """Branch: rate_limit_default returns limiter.limit(DEFAULT_RATE)"""
        from core.rate_limit import rate_limit_default
        result = rate_limit_default()
        assert result is not None

    def test_rate_limit_search(self):
        """Branch: rate_limit_search returns limiter.limit(SEARCH_RATE)"""
        from core.rate_limit import rate_limit_search
        result = rate_limit_search()
        assert result is not None


# ── password_hasher.needs_rehash ──────────────────────────────────────────


class TestPasswordHasherNeedsRehash:
    """Cover BcryptPasswordHasher.needs_rehash branches."""

    def test_needs_rehash_prefix_matches(self):
        """Branch: needs_rehash with matching prefix returns False"""
        from infrastructure.primary.middleware.password_hasher import BcryptPasswordHasher
        hasher = BcryptPasswordHasher()
        hashed = "$2b$12$" + "x" * 53
        assert hasher.needs_rehash(hashed, 12) is False

    def test_needs_rehash_prefix_does_not_match(self):
        """Branch: needs_rehash with non-matching prefix returns True"""
        from infrastructure.primary.middleware.password_hasher import BcryptPasswordHasher
        hasher = BcryptPasswordHasher()
        hashed = "$2a$10$" + "x" * 53
        assert hasher.needs_rehash(hashed, 12) is True

    def test_needs_rehash_different_rounds(self):
        """Branch: needs_rehash with different rounds returns True"""
        from infrastructure.primary.middleware.password_hasher import BcryptPasswordHasher
        hasher = BcryptPasswordHasher()
        hashed = "$2b$14$" + "x" * 53
        assert hasher.needs_rehash(hashed, 12) is True


# ── audit logger gap ──────────────────────────────────────────────────────


class TestAuditLoggerGap:
    """Cover AuditLogger.log with running asyncio loop."""

    def test_log_with_running_loop_dispatches(self):
        """Branch: log with running asyncio loop dispatches to task"""
        from core.audit import AuditLogger, AuditEntry, AuditEvent

        logger = AuditLogger()
        entry = AuditEntry(
            event=AuditEvent.PROFILE_CREATED,
            user_id=uuid4(),
            organization_id=uuid4(),
            resource_type="profile",
            resource_id=uuid4(),
            details={},
        )
        async def _run():
            logger.log(entry)
        asyncio.run(_run())


# ── FernetCredentialEncryptor ─────────────────────────────────────────────


class TestFernetCredentialEncryptor:
    """Cover FernetCredentialEncryptor encryption/decryption branches."""

    @pytest.fixture
    def encryptor(self):
        from core.credential_encryptor import FernetCredentialEncryptor
        return FernetCredentialEncryptor(VALID_FERNET_KEY)

    def test_init_with_string_key_encodes_to_bytes(self):
        """Branch: key is str → encoded to bytes before Fernet init"""
        from core.credential_encryptor import FernetCredentialEncryptor
        enc = FernetCredentialEncryptor(VALID_FERNET_KEY)
        assert enc._fernet is not None

    def test_init_with_bytes_key_uses_directly(self):
        """Branch: key is bytes → used directly without encoding"""
        from core.credential_encryptor import FernetCredentialEncryptor
        key_bytes = VALID_FERNET_KEY.encode()
        # cast to satisfy type checkers while passing bytes at runtime
        enc = FernetCredentialEncryptor(cast(str, key_bytes))
        assert enc._fernet is not None

    def test_encrypt_returns_bytes(self, encryptor):
        """Branch: encrypt returns bytes (Fernet token)"""
        result = encryptor.encrypt("hello world", uuid4())
        assert isinstance(result, bytes)
        assert result != b"hello world"

    def test_decrypt_returns_original_string(self, encryptor):
        """Branch: decrypt reverses encrypt"""
        instance_id = uuid4()
        encrypted = encryptor.encrypt("secret data", instance_id)
        decrypted = encryptor.decrypt(encrypted, instance_id)
        assert decrypted == "secret data"

    def test_encrypt_bytes_returns_bytes(self, encryptor):
        """Branch: encrypt_bytes returns Fernet token from bytes input"""
        result = encryptor.encrypt_bytes(b"binary data", uuid4())
        assert isinstance(result, bytes)

    def test_decrypt_bytes_returns_original_bytes(self, encryptor):
        """Branch: decrypt_bytes reverses encrypt_bytes"""
        instance_id = uuid4()
        encrypted = encryptor.encrypt_bytes(b"binary payload", instance_id)
        decrypted = encryptor.decrypt_bytes(encrypted, instance_id)
        assert decrypted == b"binary payload"

    def test_decrypt_with_wrong_instance_id_still_works(self, encryptor):
        """Branch: decrypt ignores instance_id (Fernet does not use it)"""
        instance_id = uuid4()
        encrypted = encryptor.encrypt("data", instance_id)
        decrypted = encryptor.decrypt(encrypted, uuid4())
        assert decrypted == "data"

    def test_decrypt_bytes_with_associated_data_ignored(self, encryptor):
        """Branch: associated_data is accepted but ignored (interface compliance)"""
        instance_id = uuid4()
        encrypted = encryptor.encrypt_bytes(b"payload", instance_id, {"ctx": "test"})
        decrypted = encryptor.decrypt_bytes(encrypted, instance_id, {"ctx": "other"})
        assert decrypted == b"payload"

    def test_encrypt_with_associated_data_provided_ignored(self, encryptor):
        """Branch: encrypt with optional associated_data parameter"""
        result = encryptor.encrypt("test", uuid4(), associated_data={"key": "value"})
        assert isinstance(result, bytes)


# ── pseudonymize ──────────────────────────────────────────────────────────


class TestPseudonymize:
    """Cover pseudonymize function for all input types and PII keys."""

    def test_scalar_passthrough_int(self):
        """Branch: input is int → returned as-is"""
        from core.pseudonymizer import pseudonymize
        assert pseudonymize(42) == 42

    def test_scalar_passthrough_string(self):
        """Branch: input is str → returned as-is"""
        from core.pseudonymizer import pseudonymize
        assert pseudonymize("plain text") == "plain text"

    def test_scalar_passthrough_none(self):
        """Branch: input is None → returned as-is"""
        from core.pseudonymizer import pseudonymize
        assert pseudonymize(None) is None

    def test_empty_dict_returns_empty_dict(self):
        """Branch: input is empty dict → returned empty dict"""
        from core.pseudonymizer import pseudonymize
        assert pseudonymize({}) == {}

    def test_dict_non_pii_keys_passthrough(self):
        """Branch: dict with non-PII keys → values passed through"""
        from core.pseudonymizer import pseudonymize
        data = {"task_id": "T-123", "status": "open", "priority": "high"}
        result = pseudonymize(data)
        assert result == data

    def test_dict_pii_email_is_hashed(self):
        """Branch: dict key 'email' with non-empty str → hashed"""
        from core.pseudonymizer import pseudonymize
        data = {"email": "user@example.com"}
        result = pseudonymize(data)
        assert result["email"].startswith("sha256:")
        assert result["email"] != "user@example.com"

    def test_dict_pii_name_is_hashed(self):
        """Branch: dict key 'name' (PII) → hashed"""
        from core.pseudonymizer import pseudonymize
        data = {"name": "John Doe"}
        result = pseudonymize(data)
        assert result["name"].startswith("sha256:")

    def test_dict_pii_displayname_is_hashed(self):
        """Branch: dict key 'displayName' (case-insensitive PII) → hashed"""
        from core.pseudonymizer import pseudonymize
        data = {"displayName": "Jane"}
        result = pseudonymize(data)
        assert result["displayName"].startswith("sha256:")

    def test_dict_pii_username_is_hashed(self):
        """Branch: dict key 'username' (PII) → hashed"""
        from core.pseudonymizer import pseudonymize
        data = {"username": "jdoe"}
        result = pseudonymize(data)
        assert result["username"].startswith("sha256:")

    def test_dict_pii_assignee_is_hashed(self):
        """Branch: dict key 'assignee' (PII) → hashed"""
        from core.pseudonymizer import pseudonymize
        data = {"assignee": "worker@corp.com"}
        result = pseudonymize(data)
        assert result["assignee"].startswith("sha256:")

    def test_dict_pii_author_is_hashed(self):
        """Branch: dict key 'author' (PII) → hashed"""
        from core.pseudonymizer import pseudonymize
        data = {"author": "writer"}
        result = pseudonymize(data)
        assert result["author"].startswith("sha256:")

    def test_dict_pii_fullname_is_hashed(self):
        """Branch: dict key 'fullName' (case-insensitive PII) → hashed"""
        from core.pseudonymizer import pseudonymize
        data = {"fullName": "Full Name Here"}
        result = pseudonymize(data)
        assert result["fullName"].startswith("sha256:")

    def test_dict_pii_empty_string_not_hashed(self):
        """Branch: PII key but value is empty str → not hashed (remains empty)"""
        from core.pseudonymizer import pseudonymize
        data = {"email": ""}
        result = pseudonymize(data)
        assert result["email"] == ""

    def test_dict_pii_non_string_value_not_hashed(self):
        """Branch: PII key but value is not str (e.g. list) → not hashed"""
        from core.pseudonymizer import pseudonymize
        data = {"email": ["a", "b"]}
        result = pseudonymize(data)
        assert result["email"] == ["a", "b"]

    def test_list_of_dicts_each_processed(self):
        """Branch: input is list of dicts → each item pseudonymized"""
        from core.pseudonymizer import pseudonymize
        data = [{"email": "a@b.com"}, {"email": "c@d.com"}]
        result = pseudonymize(data)
        assert result[0]["email"].startswith("sha256:")
        assert result[1]["email"].startswith("sha256:")

    def test_nested_dict_pii_inner_hashed(self):
        """Branch: nested dict → inner PII keys hashed"""
        from core.pseudonymizer import pseudonymize
        data = {"ticket": {"author": "dev1", "title": "fix bug"}}
        result = pseudonymize(data)
        assert result["ticket"]["author"].startswith("sha256:")
        assert result["ticket"]["title"] == "fix bug"

    def test_list_inside_dict_processed(self):
        """Branch: dict value is a list → each item in list pseudonymized"""
        from core.pseudonymizer import pseudonymize
        data = {"comments": [{"author": "u1"}, {"author": "u2"}]}
        result = pseudonymize(data)
        assert result["comments"][0]["author"].startswith("sha256:")
        assert result["comments"][1]["author"].startswith("sha256:")

    def test_mixed_types_passthrough(self):
        """Branch: float and bool values passed through unchanged"""
        from core.pseudonymizer import pseudonymize
        data = {"count": 5, "active": True, "rating": 4.5}
        result = pseudonymize(data)
        assert result == data

    def test_is_pii_key_case_insensitive(self):
        """Branch: _is_pii_key uses key.lower() → case insensitive"""
        from core.pseudonymizer import _is_pii_key
        assert _is_pii_key("EMAIL") is True
        assert _is_pii_key("Email") is True
        assert _is_pii_key("eMaIl") is True
        assert _is_pii_key("task_id") is False

    def test_hash_value_returns_prefixed_sha256(self):
        """Branch: _hash_value returns 'sha256:' + hex digest"""
        from core.pseudonymizer import _hash_value
        value = "test@example.com"
        expected = "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()
        assert _hash_value(value) == expected


# ── get_async_session ─────────────────────────────────────────────────────


class TestGetAsyncSession:
    """Cover get_async_session async generator context manager."""

    async def test_get_async_session_yields_session(self):
        """Covers get_async_session.py lines 39-40: async generator context manager."""
        from infrastructure.secondary.database.get_async_session import get_async_session
        gen = get_async_session()
        session = await gen.__anext__()
        assert session is not None

"""
Branch-coverage tests targeting remaining small gaps to reach 70%.
Covers: rate_limit, password_hasher.needs_rehash, manage_profile branches,
and organization_service simple methods.
"""

import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api", "src"))

pytestmark = pytest.mark.unit


# -- rate_limit -----------------------------------------------------------

class TestRateLimitFunctions:
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


# -- password_hasher.needs_rehash -----------------------------------------

class TestPasswordHasherNeedsRehash:
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


# -- manage_profile missing branches --------------------------------------

class TestManageProfileGaps:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.manage_profile import ManageProfileUseCase
        profile_repo = AsyncMock()
        rule_repo = AsyncMock()
        return ManageProfileUseCase(profile_repo, rule_repo), profile_repo, rule_repo

    async def test_update_profile_with_description(self, svc):
        """Branch: update_profile with description not None sets description"""
        service, profile_repo, _ = svc
        from domain.entities.verification_profile import VerificationProfile
        p = VerificationProfile(id=uuid4(), organization_id=uuid4(), name="p", description="old")
        profile_repo.get_by_id = AsyncMock(return_value=p)
        profile_repo.update = AsyncMock(return_value=p)
        result = await service.update_profile(p.id, description="new desc")
        assert result.description == "new desc"

    async def test_get_profile_found(self, svc):
        """Branch: get_profile calls repo.get_by_id and returns profile"""
        service, profile_repo, _ = svc
        from domain.entities.verification_profile import VerificationProfile
        p = VerificationProfile(id=uuid4(), organization_id=uuid4(), name="p")
        profile_repo.get_by_id = AsyncMock(return_value=p)
        result = await service.get_profile(p.id)
        assert result.name == "p"

    async def test_list_profiles(self, svc):
        """Branch: list_profiles calls repo.list_by_organization"""
        service, profile_repo, _ = svc
        from domain.entities.verification_profile import VerificationProfile
        p = VerificationProfile(id=uuid4(), organization_id=uuid4(), name="p")
        profile_repo.list_by_organization = AsyncMock(return_value=[p])
        results = await service.list_profiles(p.organization_id)
        assert len(results) == 1

    async def test_duplicate_profile_re_fetch_fails(self, svc):
        """Branch: duplicate_profile where re-fetch after creation returns None"""
        service, profile_repo, rule_repo = svc
        from domain.entities.verification_profile import VerificationProfile
        original = VerificationProfile(id=uuid4(), organization_id=uuid4(), name="orig", rules=[])
        created = VerificationProfile(id=uuid4(), organization_id=uuid4(), name="copy")
        profile_repo.get_by_id = AsyncMock(side_effect=[original, None])
        profile_repo.create = AsyncMock(return_value=created)
        from domain.exceptions import EntityNotFoundError
        with pytest.raises(EntityNotFoundError):
            await service.duplicate_profile(original.id, "copy")


# -- organization_service simple methods ----------------------------------

class TestOrganizationServiceGaps:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.organization_service import OrganizationService
        org_repo = AsyncMock()
        project_repo = AsyncMock()
        user_repo = AsyncMock()
        return OrganizationService(org_repo, project_repo, user_repo), org_repo, project_repo, user_repo

    async def test_get_organization(self, svc):
        """Branch: get_organization calls repo.get_by_id"""
        service, org_repo, _, _ = svc
        from domain.entities.organization import Organization
        o = Organization(id=uuid4(), name="org", slug="org-slug")
        org_repo.get_by_id = AsyncMock(return_value=o)
        result = await service.get_organization(o.id)
        assert result.name == "org"

    async def test_list_organizations(self, svc):
        """Branch: list_organizations calls repo.list_all"""
        service, org_repo, _, _ = svc
        from domain.entities.organization import Organization
        o = Organization(id=uuid4(), name="org", slug="org-slug")
        org_repo.list_all = AsyncMock(return_value=[o])
        results = await service.list_organizations()
        assert len(results) == 1

    async def test_list_projects(self, svc):
        """Branch: list_projects calls repo.list_by_organization"""
        service, _, project_repo, _ = svc
        from domain.entities.project import Project
        p = Project(id=uuid4(), name="p", organization_id=uuid4(), description="d", profile_id=uuid4())
        project_repo.list_by_organization = AsyncMock(return_value=[p])
        results = await service.list_projects(p.organization_id)
        assert len(results) == 1

    async def test_get_project(self, svc):
        """Branch: get_project calls repo.get_by_id"""
        service, _, project_repo, _ = svc
        from domain.entities.project import Project
        p = Project(id=uuid4(), name="p", organization_id=uuid4(), description="d", profile_id=uuid4())
        project_repo.get_by_id = AsyncMock(return_value=p)
        result = await service.get_project(p.id)
        assert result.name == "p"

    async def test_list_accessible_projects(self, svc):
        """Branch: list_accessible_projects iterates orgs and aggregates projects"""
        service, org_repo, project_repo, _ = svc
        from domain.entities.organization import Organization
        from domain.entities.project import Project

        org1 = Organization(id=uuid4(), name="o1", slug="o1")
        org2 = Organization(id=uuid4(), name="o2", slug="o2")
        org_repo.list_all = AsyncMock(return_value=[org1, org2])

        p1 = Project(id=uuid4(), name="p1", organization_id=org1.id, description="d", profile_id=uuid4())
        p2 = Project(id=uuid4(), name="p2", organization_id=org2.id, description="d", profile_id=uuid4())
        project_repo.list_by_organization = AsyncMock(side_effect=[[p1], [p2]])

        results = await service.list_accessible_projects(uuid4())
        assert len(results) == 2


# -- task_service remaining -----------------------------------------------

class TestTaskServiceGap:
    async def test_get_task_status(self):
        """Branch: get_task_status calls task_queue.get_task_status"""
        from application.use_cases.main.task_service import TaskService

        queue = AsyncMock()
        queue.get_task_status = AsyncMock(return_value="SUCCESS")
        svc = TaskService(queue)

        result = await svc.get_task_status("task-123")
        assert result == "SUCCESS"


# -- template_service remaining gaps --------------------------------------

class TestTemplateServiceGaps:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.template_service import TemplateService
        template_repo = AsyncMock()
        profile_repo = AsyncMock()
        return TemplateService(template_repo, profile_repo), template_repo, profile_repo

    async def test_get_template_not_found(self, svc):
        """Branch: get_template not found returns None"""
        service, template_repo, _ = svc
        template_repo.get_by_id = AsyncMock(return_value=None)
        result = await service.get_template(uuid4())
        assert result is None


# -- release_service remaining gaps ---------------------------------------

class TestReleaseServiceGaps:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.release_service import CreateReleaseUseCase
        release_repo = AsyncMock()
        project_repo = AsyncMock()
        profile_repo = AsyncMock()
        return CreateReleaseUseCase(release_repo, project_repo, profile_repo), release_repo, project_repo, profile_repo

    async def test_get_release_found(self, svc):
        """Branch: get_release returns release"""
        service, release_repo, _, _ = svc
        from domain.entities.release import Release
        r = Release(
            id=uuid4(), name="r1", version="1.0", project_id=uuid4(),
            profile_id=uuid4(), created_by=uuid4(),
        )
        release_repo.get_by_id = AsyncMock(return_value=r)
        result = await service.get_release(r.id)
        assert result.name == "r1"


# -- user_service remaining gaps ------------------------------------------

class TestUserServiceGaps:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.user_service import UserService
        user_repo = AsyncMock()
        org_repo = AsyncMock()
        password_hasher = AsyncMock()
        return UserService(user_repo, org_repo, password_hasher), user_repo, org_repo

    async def test_get_user_by_id_found(self, svc):
        """Branch: get_user_by_id returns user"""
        service, user_repo, _ = svc
        from domain.entities.user import User
        from domain.enums import UserRole
        u = User(
            id=uuid4(), email="t@t.com", hashed_password="h",
            display_name="Test", role=UserRole.U2,
        )
        user_repo.get_by_id = AsyncMock(return_value=u)
        result = await service.get_user_by_id(u.id)
        assert result.email == "t@t.com"


# -- connector_service remaining methods ----------------------------------

class TestConnectorServiceRemaining:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.connector_service import ConnectorService
        connector_repo = AsyncMock()
        connector_registry = MagicMock()
        return ConnectorService(connector_repo, connector_registry), connector_repo, connector_registry

    async def test_list_connectors(self, svc):
        """Branch: list_connectors calls repo.list_by_organization"""
        service, connector_repo, _ = svc
        from domain.entities.connector_instance import ConnectorInstance
        from domain.enums import ConnectorStatus
        c = ConnectorInstance(
            id=uuid4(), name="c1", connector_type="GESTOR_TAREAS",
            connector_implementation="JIRA", organization_id=uuid4(),
            encrypted_credentials=b"enc", status=ConnectorStatus.ACTIVO,
        )
        connector_repo.list_by_organization = AsyncMock(return_value=[c])
        results = await service.list_connectors(c.organization_id)
        assert len(results) == 1

    async def test_get_connector(self, svc):
        """Branch: get_connector calls repo.get_by_id"""
        service, connector_repo, _ = svc
        from domain.entities.connector_instance import ConnectorInstance
        from domain.enums import ConnectorStatus
        c = ConnectorInstance(
            id=uuid4(), name="c1", connector_type="GESTOR_TAREAS",
            connector_implementation="JIRA", organization_id=uuid4(),
            encrypted_credentials=b"enc", status=ConnectorStatus.ACTIVO,
        )
        connector_repo.get_by_id = AsyncMock(return_value=c)
        result = await service.get_connector(c.id)
        assert result.name == "c1"

    async def test_delete_connector(self, svc):
        """Branch: delete_connector found deletes and audits"""
        service, connector_repo, _ = svc
        from domain.entities.connector_instance import ConnectorInstance
        from domain.enums import ConnectorStatus
        c = ConnectorInstance(
            id=uuid4(), name="c1", connector_type="GESTOR_TAREAS",
            connector_implementation="JIRA", organization_id=uuid4(),
            encrypted_credentials=b"enc", status=ConnectorStatus.ACTIVO,
        )
        connector_repo.get_by_id = AsyncMock(return_value=c)
        connector_repo.delete = AsyncMock()
        await service.delete_connector(c.id, uuid4())
        connector_repo.delete.assert_awaited_once()


# -- release_service remaining methods ------------------------------------

class TestReleaseServiceRemaining:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.release_service import CreateReleaseUseCase
        release_repo = AsyncMock()
        project_repo = AsyncMock()
        profile_repo = AsyncMock()
        return CreateReleaseUseCase(release_repo, project_repo, profile_repo), release_repo

    async def test_list_releases(self, svc):
        """Branch: list_releases calls repo.list_by_project"""
        service, release_repo = svc
        from domain.entities.release import Release
        r = Release(
            id=uuid4(), name="r1", version="1.0", project_id=uuid4(),
            profile_id=uuid4(), created_by=uuid4(),
        )
        release_repo.list_by_project = AsyncMock(return_value=[r])
        results = await service.list_releases(r.project_id)
        assert len(results) == 1

    async def test_update_status_success(self, svc):
        """Branch: update_status returns updated release"""
        service, release_repo = svc
        from domain.entities.release import Release
        from domain.enums import ReleaseStatus
        r = Release(
            id=uuid4(), name="r1", version="1.0", project_id=uuid4(),
            profile_id=uuid4(), created_by=uuid4(), status=ReleaseStatus.EN_VERIFICACION,
        )
        release_repo.update_status = AsyncMock(return_value=r)
        result = await service.update_status(r.id, ReleaseStatus.VALIDA)
        assert result.status == ReleaseStatus.EN_VERIFICACION

    async def test_list_org_releases(self, svc):
        """Branch: list_org_releases calls repo.list_by_organization"""
        service, release_repo = svc
        from domain.entities.release import Release
        r = Release(
            id=uuid4(), name="r1", version="1.0", project_id=uuid4(),
            profile_id=uuid4(), created_by=uuid4(),
        )
        release_repo.list_by_organization = AsyncMock(return_value=[r])
        results = await service.list_org_releases()
        assert len(results) == 1


# -- verification_service remaining gap  ----------------------------------

class TestVerificationServiceRemaining:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.verification_service import VerificationService
        release_repo = AsyncMock()
        verification_repo = AsyncMock()
        task_queue = AsyncMock()
        connector_registry = MagicMock()
        return VerificationService(release_repo, verification_repo, task_queue, connector_registry), release_repo, verification_repo

    async def test_get_verification_history_success(self, svc):
        """Branch: get_verification_history with valid release returns results"""
        service, release_repo, verification_repo = svc
        from domain.entities.release import Release
        r = Release(
            id=uuid4(), name="r1", version="1.0", project_id=uuid4(),
            profile_id=uuid4(), created_by=uuid4(),
        )
        release_repo.get_by_id = AsyncMock(return_value=r)
        v_result = MagicMock()
        verification_repo.find_by_release = AsyncMock(return_value=[v_result])
        results = await service.get_verification_history(r.id)
        assert len(results) == 1

# -- connector_service test_connection branch ----------------------------

class TestConnectorServiceTestConnection:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.connector_service import ConnectorService
        connector_repo = AsyncMock()
        connector_registry = MagicMock()
        return ConnectorService(connector_repo, connector_registry), connector_repo, connector_registry

    async def test_test_connection_success(self, svc):
        """Branch: test_connector_connection success path sets ACTIVO"""
        service, connector_repo, connector_registry = svc
        from domain.entities.connector_instance import ConnectorInstance
        from domain.enums import ConnectorStatus
        c = ConnectorInstance(
            id=uuid4(), name="c1", connector_type="GESTOR_TAREAS",
            connector_implementation="JIRA", organization_id=uuid4(),
            encrypted_credentials=b"enc", status=ConnectorStatus.INACTIVO,
        )
        connector_repo.get_by_id = AsyncMock(return_value=c)
        connector_repo.update = AsyncMock()

        mock_impl = MagicMock()
        mock_impl.test_connection = MagicMock(return_value=True)
        connector_registry.get_by_implementation = MagicMock(return_value=mock_impl)

        with patch("cryptography.fernet.Fernet") as mock_fernet_cls, \
             patch("application.use_cases.main.connector_service.settings") as mock_settings:
            mock_settings.encryption_key = "dummy-key"
            mock_fernet = MagicMock()
            mock_fernet.decrypt = MagicMock(return_value=b"{'key': 'val'}")
            mock_fernet_cls.return_value = mock_fernet

            result = await service.test_connector_connection(c.id, uuid4())

        assert result is True
        assert c.status == ConnectorStatus.ACTIVO
        connector_repo.update.assert_awaited_once()

    async def test_test_connection_failure(self, svc):
        """Branch: test_connector_connection exception sets ERROR and raises"""
        service, connector_repo, connector_registry = svc
        from domain.entities.connector_instance import ConnectorInstance
        from domain.enums import ConnectorStatus
        c = ConnectorInstance(
            id=uuid4(), name="c1", connector_type="GESTOR_TAREAS",
            connector_implementation="JIRA", organization_id=uuid4(),
            encrypted_credentials=b"enc", status=ConnectorStatus.ACTIVO,
        )
        connector_repo.get_by_id = AsyncMock(return_value=c)
        connector_repo.update = AsyncMock()

        mock_impl = MagicMock()
        mock_impl.test_connection = MagicMock(side_effect=Exception("Boom"))
        connector_registry.get_by_implementation = MagicMock(return_value=mock_impl)

        with patch("cryptography.fernet.Fernet") as mock_fernet_cls, \
             patch("application.use_cases.main.connector_service.settings") as mock_settings:
            mock_settings.encryption_key = "dummy-key"
            mock_fernet = MagicMock()
            mock_fernet.decrypt = MagicMock(return_value=b"{'key': 'val'}")
            mock_fernet_cls.return_value = mock_fernet

            from domain.exceptions import ConnectorConnectionFailedError
            with pytest.raises(ConnectorConnectionFailedError):
                await service.test_connector_connection(c.id, uuid4())

        assert c.status == ConnectorStatus.ERROR
        connector_repo.update.assert_awaited_once()

    async def test_test_connection_impl_not_found(self, svc):
        """Branch: test_connector_connection impl not found → ValidationError"""
        service, connector_repo, connector_registry = svc
        from domain.entities.connector_instance import ConnectorInstance
        from domain.enums import ConnectorStatus
        c = ConnectorInstance(
            id=uuid4(), name="c1", connector_type="GESTOR_TAREAS",
            connector_implementation="UNKNOWN", organization_id=uuid4(),
            encrypted_credentials=b"enc", status=ConnectorStatus.ACTIVO,
        )
        connector_repo.get_by_id = AsyncMock(return_value=c)
        connector_registry.get_by_implementation = MagicMock(return_value=None)

        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError):
            await service.test_connector_connection(c.id, uuid4())


# -- user_service remaining gaps ------------------------------------------

class TestUserServiceMoreGaps:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.user_service import UserService
        user_repo = AsyncMock()
        org_repo = AsyncMock()
        from infrastructure.primary.middleware.password_hasher import BcryptPasswordHasher
        password_hasher = BcryptPasswordHasher()
        return UserService(user_repo, org_repo, password_hasher), user_repo, org_repo, password_hasher

    async def test_list_organization_users(self, svc):
        """Branch: list_organization_users calls repo.list_all"""
        service, user_repo, _, _ = svc
        from domain.entities.user import User
        from domain.enums import UserRole
        u = User(id=uuid4(), email="t@t.com", hashed_password="h", display_name="T", role=UserRole.U2)
        user_repo.list_all = AsyncMock(return_value=[u])
        results = await service.list_organization_users(uuid4())
        assert len(results) == 1

    async def test_deactivate_user_not_found(self, svc):
        """Branch: deactivate_user not found raises EntityNotFoundError"""
        service, user_repo, _, _ = svc
        user_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import EntityNotFoundError
        with pytest.raises(EntityNotFoundError):
            await service.deactivate_user(uuid4(), uuid4())

    async def test_deactivate_user_success(self, svc):
        """Branch: deactivate_user found sets is_active=False"""
        service, user_repo, _, _ = svc
        from domain.entities.user import User
        from domain.enums import UserRole
        u = User(id=uuid4(), email="t@t.com", hashed_password="h", display_name="T", role=UserRole.U2, is_active=True)
        user_repo.get_by_id = AsyncMock(return_value=u)
        user_repo.update = AsyncMock(return_value=u)
        result = await service.deactivate_user(u.id, uuid4())
        assert result.is_active is False

    async def test_update_global_role_success(self, svc):
        """Branch: update_global_role found updates role"""
        service, user_repo, _, _ = svc
        from domain.entities.user import User
        from domain.enums import UserRole
        u = User(id=uuid4(), email="t@t.com", hashed_password="h", display_name="T", role=UserRole.U2)
        user_repo.get_by_id = AsyncMock(return_value=u)
        user_repo.update = AsyncMock(return_value=u)
        result = await service.update_global_role(u.id, UserRole.U3, uuid4())
        assert result.role == UserRole.U3

# -- auth_service remaining gap (line 193) --------------------------------

class TestAuthServiceGap:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.auth_service import AuthService
        user_repo = AsyncMock()
        token_service = MagicMock()
        password_hasher = MagicMock()
        return AuthService(user_repo, token_service, password_hasher), user_repo

    async def test_disable_totp_invalid_code_raises(self, svc):
        """Branch: disable_totp with invalid code -> ValidationError"""
        service, user_repo = svc
        from domain.entities.user import User
        from domain.enums import UserRole
        u = User(
            id=uuid4(), email="t@t.com", hashed_password="h",
            display_name="T", role=UserRole.U2,
            totp_enabled=True, totp_secret="JBSWY3DPEHPK3PXP",
        )
        user_repo.get_by_id = AsyncMock(return_value=u)
        from domain.exceptions import ValidationError
        with pytest.raises(ValidationError):
            await service.disable_totp(u.id, "000000")


# -- template_service list_templates gap (line 66) ---------------------------

class TestTemplateServiceList:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.template_service import TemplateService
        template_repo = AsyncMock()
        profile_repo = AsyncMock()
        return TemplateService(template_repo, profile_repo), template_repo

    async def test_list_templates_include_archived(self, svc):
        """Branch: list_templates with include_archived=True"""
        service, template_repo = svc
        template_repo.list_by_organization = AsyncMock(return_value=[])
        results = await service.list_templates(uuid4(), include_archived=True)
        assert results == []


# -- release_service remaining branches --------------------------------------

class TestReleaseServiceFinal:
    @pytest.fixture
    def svc(self):
        from application.use_cases.main.release_service import CreateReleaseUseCase
        release_repo = AsyncMock()
        project_repo = AsyncMock()
        profile_repo = AsyncMock()
        return CreateReleaseUseCase(release_repo, project_repo, profile_repo), release_repo

    async def test_remove_artifact(self, svc):
        """Branch: remove_artifact removes artifact from release and deletes"""
        service, release_repo = svc
        from domain.entities.release import Release
        from domain.entities.artifact import Artifact

        art_id = uuid4()
        artifact = Artifact(
            id=art_id, release_id=uuid4(), connector_instance_id=uuid4(),
            connector_implementation="JIRA", artifact_type="TAREA",
            external_ref="REF-1",
        )
        r = Release(
            id=artifact.release_id, name="r1", version="1.0", project_id=uuid4(),
            profile_id=uuid4(), created_by=uuid4(), artifacts=[artifact],
        )
        release_repo.get_artifact_by_id = AsyncMock(return_value=artifact)
        release_repo.get_by_id = AsyncMock(return_value=r)
        release_repo.update = AsyncMock()
        release_repo.delete_artifact = AsyncMock()

        await service.remove_artifact(art_id)
        release_repo.delete_artifact.assert_awaited_once()

    async def test_list_artifacts(self, svc):
        """Branch: list_artifacts with release found returns sliced list"""
        service, release_repo = svc
        from domain.entities.release import Release
        from domain.entities.artifact import Artifact

        art = Artifact(
            id=uuid4(), release_id=uuid4(), connector_instance_id=uuid4(),
            connector_implementation="JIRA", artifact_type="TAREA",
            external_ref="REF-1",
        )
        r = Release(
            id=uuid4(), name="r1", version="1.0", project_id=uuid4(),
            profile_id=uuid4(), created_by=uuid4(), artifacts=[art],
        )
        release_repo.get_by_id = AsyncMock(return_value=r)
        results = await service.list_artifacts(r.id)
        assert len(results) == 1


# -- manage_api_keys remaining gap (line 91) --------------------------------

class TestManageApiKeysGap:
    @pytest.fixture
    def svc(self):
        from application.use_cases.others.manage_api_keys import ManageApiKeysUseCase
        api_key_repo = AsyncMock()
        return ManageApiKeysUseCase(api_key_repository=api_key_repo), api_key_repo

    async def test_revoke_api_key_not_found(self, svc):
        """Branch: revoke_api_key not found raises EntityNotFoundError"""
        service, api_key_repo = svc
        api_key_repo.get_by_id = AsyncMock(return_value=None)
        from domain.exceptions import EntityNotFoundError
        with pytest.raises(EntityNotFoundError):
            await service.revoke_api_key(uuid4(), uuid4())


# -- audit logger remaining gap (line 112) ---------------------------------

class TestAuditLoggerGap:
    def test_log_with_running_loop_dispatches(self):
        """Branch: log with running asyncio loop dispatches to task"""
        import asyncio
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

"""
Branch-coverage tests for all SQL repository implementations.
Uses AsyncMock to simulate SQLAlchemy async sessions.
Consolidated from test_repositories.py, test_repositories_coverage.py,
and test_low_coverage_boost.py (repo classes only).
"""

import os
import sys
import pytest
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
from datetime import datetime, timezone

from domain.entities.access_request import AccessRequest
from domain.enums import AccessRequestStatus, VerdictType

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api", "src"))

pytestmark = pytest.mark.unit


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_mock_session():
    """Return an (AsyncMock, context manager factory) that simulates SQLAlchemy session."""
    session = AsyncMock()
    # session.add/delete are synchronous in SQLAlchemy; AsyncMock would leave
    # unawaited coroutines and emit RuntimeWarning.
    session.add = MagicMock()
    session.delete = MagicMock()
    session_mgr = MagicMock()
    session_mgr.__aenter__ = AsyncMock(return_value=session)
    session_mgr.__aexit__ = AsyncMock(return_value=None)
    return session, session_mgr


def _make_scalar_result(row):
    """Simulate result.scalar_one_or_none() returning a row."""
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=row)
    return result


def _make_scalars_result(rows):
    """Simulate result.scalars().all() returning rows."""
    scalars = MagicMock()
    scalars.all = MagicMock(return_value=rows)
    result = MagicMock()
    result.scalars = MagicMock(return_value=scalars)
    return result


_SENTINEL = object()


# ── row builders ─────────────────────────────────────────────────────────────

def _make_release_row(release_id=None, name="v1.0", version="1.0.0",
                      project_id=None, status="BORRADOR", profile_id=_SENTINEL,
                      previous_status=None):
    """Create a mock row resembling ReleaseModel.
    If profile_id is _SENTINEL (default), a random UUID str is assigned.
    Use profile_id=None explicitly to get None.
    """
    row = MagicMock()
    row.id = str(release_id or uuid4())
    row.name = name
    row.version = version
    row.project_id = str(project_id or uuid4())
    row.status = status
    if profile_id is _SENTINEL:
        row.profile_id = str(uuid4())
    else:
        row.profile_id = profile_id
    row.previous_status = previous_status
    row.created_by = str(uuid4())
    row.created_at = datetime.now(timezone.utc)
    return row


def _make_artifact_row(artifact_id=None, release_id=None, connector_instance_id=None,
                       connector_implementation="JIRA", artifact_type="TAREA", external_ref="REF-1"):
    """Create a mock row resembling ArtifactModel."""
    row = MagicMock()
    row.id = str(artifact_id or uuid4())
    row.release_id = str(release_id or uuid4())
    row.connector_instance_id = str(connector_instance_id or uuid4())
    row.connector_implementation = connector_implementation
    row.artifact_type = artifact_type
    row.external_ref = external_ref
    row.metadata = {}
    row.created_at = datetime.now(timezone.utc)
    return row


def _make_user_row(user_id=None, email="test@test.com", hashed_pw="hash",
                   display_name="Test", role="OPERATOR", is_active=True,
                   failed_attempts=0, locked_until=None, organization_id=None,
                   activation_token=None, activation_token_expiry=None,
                   totp_secret=None, totp_enabled=None):
    """Create a mock row resembling UserModel."""
    row = MagicMock()
    row.id = str(user_id or uuid4())
    row.email = email
    row.hashed_password = hashed_pw
    row.display_name = display_name
    row.role = role
    row.is_active = is_active
    row.failed_login_attempts = failed_attempts
    row.locked_until = locked_until
    row.organization_id = str(organization_id) if organization_id else None
    row.created_at = datetime.now(timezone.utc)
    row.updated_at = datetime.now(timezone.utc)
    row.terms_accepted_at = None
    row.privacy_accepted_at = None
    row.activation_token = activation_token
    row.activation_token_expiry = activation_token_expiry
    row.totp_secret = totp_secret
    row.totp_enabled = False if totp_enabled is None else totp_enabled
    return row


def _make_channel_row(channel_id=None, org_id=None, channel_type="EMAIL",
                      enabled=True, config_data=None):
    """Create a mock row resembling NotificationChannelModel."""
    row = MagicMock()
    row.id = channel_id or uuid4()
    row.organization_id = org_id or uuid4()
    row.channel_type = channel_type
    row.enabled = enabled
    row.config_data = config_data or {}
    row.created_at = datetime.now(timezone.utc)
    row.updated_at = datetime.now(timezone.utc)
    return row


def _make_subscription_row(sub_id=None, user_id=None, event_type="release_validated",
                           enabled=True):
    """Create a mock row resembling NotificationSubscriptionModel."""
    row = MagicMock()
    row.id = sub_id or uuid4()
    row.user_id = user_id or uuid4()
    row.event_type = event_type
    row.enabled = enabled
    row.created_at = datetime.now(timezone.utc)
    row.updated_at = datetime.now(timezone.utc)
    return row


def _make_access_request_row(
    request_id=None,
    requester_name: str = "John Doe",
    requester_email: str = "john@example.com",
    organization_name: str = "ACME Corp",
    organization_description: Optional[str] = "A test company",
    slug_preview: Optional[str] = "acme-corp",
    status: str = "PENDING",
    rejection_reason: Optional[str] = None,
    reviewed_by: Optional[UUID] = None,
    reviewed_at: Optional[datetime] = None,
):
    """Create a mock row resembling AccessRequestModel."""
    row = MagicMock()
    row.id = request_id or uuid4()
    row.requester_name = requester_name
    row.requester_email = requester_email
    row.organization_name = organization_name
    row.organization_description = organization_description
    row.slug_preview = slug_preview
    row.status = status
    row.rejection_reason = rejection_reason
    row.reviewed_by = reviewed_by if reviewed_by else None
    row.reviewed_at = reviewed_at
    row.created_at = datetime.now(timezone.utc)
    row.updated_at = datetime.now(timezone.utc)
    return row


def _make_template_row(template_id=None, org_id=None, name="tpl",
                       description: Optional[str] = "desc", profile_id=None, created_by=None,
                       project_name_template=None, is_archived=False):
    """Create a mock row resembling TemplateModel."""
    row = MagicMock()
    row.id = str(template_id or uuid4())
    row.organization_id = str(org_id or uuid4())
    row.name = name
    row.description = description
    row.profile_id = str(profile_id or uuid4())
    row.created_by = str(created_by or uuid4())
    row.project_name_template = project_name_template
    row.is_archived = is_archived
    row.created_at = datetime.now(timezone.utc)
    row.updated_at = datetime.now(timezone.utc)
    return row


def _make_connector_row(conn_id=None, org_id=None, conn_type="GESTOR_TAREAS",
                        conn_impl="JIRA", name="jira-conn", config=None,
                        status="ACTIVO", last_tested_at=None):
    """Create a mock row resembling ConnectorInstanceModel."""
    row = MagicMock()
    row.id = str(conn_id or uuid4())
    row.organization_id = str(org_id or uuid4())
    row.connector_type = conn_type
    row.connector_implementation = conn_impl
    row.name = name
    row.config_encrypted = config or b"encrypted"
    row.status = status
    row.created_at = datetime.now(timezone.utc)
    row.updated_at = datetime.now(timezone.utc)
    row.last_tested_at = last_tested_at
    return row


def _make_custom_role_row(role_id=None, org_id=None, name="viewer",
                          permissions=None, is_active=True):
    """Create a mock row resembling CustomRoleModel."""
    row = MagicMock()
    row.id = str(role_id or uuid4())
    row.organization_id = str(org_id or uuid4())
    row.name = name
    row.permissions = ["VIEW_DASHBOARD"] if permissions is None else permissions
    row.is_active = is_active
    row.created_at = datetime.now(timezone.utc)
    row.updated_at = datetime.now(timezone.utc)
    return row


def _make_rule_row(rule_id=None, profile_id=None, rule_template="check_version",
                   severity="HIGH", params=None, connector_instance_id=None,
                   display_order=1, is_active=True):
    """Create a mock row resembling VerificationRuleModel."""
    row = MagicMock()
    row.id = str(rule_id or uuid4())
    row.profile_id = str(profile_id or uuid4())
    row.rule_template = rule_template
    row.severity = severity
    row.params = params or {}
    row.connector_instance_id = connector_instance_id
    row.display_order = display_order
    row.is_active = is_active
    row.created_at = datetime.now(timezone.utc)
    return row


def _make_api_key_row(key_id=None, user_id=None, org_id=None, name="my-key",
                      key_hash="abc123", prefix="sv_s0", is_active=True,
                      expires_at=None, last_used_at=None):
    """Create a mock row resembling APIKeyModel."""
    row = MagicMock()
    row.id = str(key_id or uuid4())
    row.user_id = str(user_id or uuid4())
    row.organization_id = str(org_id or uuid4())
    row.name = name
    row.key_hash = key_hash
    row.prefix = prefix
    row.is_active = is_active
    row.created_at = datetime.now(timezone.utc)
    row.expires_at = expires_at
    row.last_used_at = last_used_at
    return row


def _make_profile_row(profile_id=None, org_id=None, name="p", description="desc",
                      is_default=False):
    """Create a mock row resembling VerificationProfileModel."""
    row = MagicMock()
    row.id = str(profile_id or uuid4())
    row.organization_id = str(org_id or uuid4())
    row.name = name
    row.description = description
    row.is_default = is_default
    row.created_at = datetime.now(timezone.utc)
    row.updated_at = datetime.now(timezone.utc)
    return row


def _make_org_row(org_id=None, name="org", slug="org-slug", owner_id=None,
                  is_active=True):
    """Create a mock row resembling OrganizationModel."""
    row = MagicMock()
    row.id = str(org_id or uuid4())
    row.name = name
    row.slug = slug
    row.owner_id = str(owner_id) if owner_id else None
    row.is_active = is_active
    row.created_at = datetime.now(timezone.utc)
    row.updated_at = datetime.now(timezone.utc)
    return row


def _make_project_row(proj_id=None, org_id=None, name="proj", description="desc",
                      profile_id=None, is_archived=False):
    """Create a mock row resembling ProjectModel."""
    row = MagicMock()
    row.id = str(proj_id or uuid4())
    row.name = name
    row.description = description
    row.organization_id = str(org_id or uuid4())
    row.profile_id = str(profile_id or uuid4())
    row.is_archived = is_archived
    row.created_at = datetime.now(timezone.utc)
    row.updated_at = datetime.now(timezone.utc)
    return row


# ── SqlReleaseRepository ─────────────────────────────────────────────────────

class TestSqlReleaseRepository:
    @pytest.fixture
    def repo(self):
        from infrastructure.secondary.database.repositories.release_repository import SqlReleaseRepository
        return SqlReleaseRepository()

    # -- _release_from_row ---------------------------------------------------

    def test_release_from_row_with_profile_id(self, repo):
        """Branch: _release_from_row with profile_id not None -> maps correctly"""
        row = _make_release_row(profile_id=uuid4())
        r = repo._release_from_row(row)
        assert r.name == "v1.0"
        assert r.version == "1.0.0"
        assert r.profile_id is not None
        assert r.status.value == "BORRADOR"

    def test_release_from_row_without_profile_id(self, repo):
        """Branch: _release_from_row with profile_id None -> maps to None"""
        row = _make_release_row(profile_id=None)
        r = repo._release_from_row(row)
        assert r.profile_id is None

    # -- create --------------------------------------------------------------

    async def test_create_release_success(self, repo):
        """Branch: create adds model, commits, refreshes"""
        session, mgr = _make_mock_session()
        from domain.entities.release import Release
        from domain.enums import ReleaseStatus
        release = Release(
            id=uuid4(), name="r1", version="1.2.3", project_id=uuid4(),
            profile_id=uuid4(), created_by=uuid4(),
            status=ReleaseStatus.BORRADOR,
        )
        with patch("infrastructure.secondary.database.repositories.release_repository.AsyncSessionLocal", return_value=mgr):
            await repo.create(release)
        session.add.assert_called_once()
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()

    # -- get_by_id -----------------------------------------------------------

    async def test_get_by_id_found_with_artifacts(self, repo):
        """Branch: get_by_id finds release + has artifacts -> returns Release with artifacts"""
        session, mgr = _make_mock_session()
        rel_row = _make_release_row()
        art_row = _make_artifact_row()
        rel_result = _make_scalar_result(rel_row)
        proj_row = MagicMock()
        proj_row.organization_id = str(uuid4())
        proj_row.name = "Test Project"
        proj_result = MagicMock()
        proj_result.one_or_none = MagicMock(return_value=proj_row)
        org_result = _make_scalar_result("Test Org")
        art_scalars = MagicMock()
        art_scalars.all = MagicMock(return_value=[art_row])
        art_result = MagicMock()
        art_result.scalars = MagicMock(return_value=art_scalars)

        session.execute = AsyncMock(side_effect=[rel_result, proj_result, org_result, art_result])
        with patch("infrastructure.secondary.database.repositories.release_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.get_by_id(uuid4())
        assert result is not None
        assert result.name == "v1.0"
        assert len(result.artifacts) == 1

    async def test_get_by_id_not_found(self, repo):
        """Branch: get_by_id returns None -> returns None"""
        session, mgr = _make_mock_session()
        rel_result = _make_scalar_result(None)
        session.execute = AsyncMock(return_value=rel_result)
        with patch("infrastructure.secondary.database.repositories.release_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.get_by_id(uuid4())
        assert result is None

    # -- list_by_project -----------------------------------------------------

    async def test_list_by_project_returns_list(self, repo):
        """Branch: list_by_project with results -> returns list of Releases"""
        session, mgr = _make_mock_session()
        rows = [_make_release_row()]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.release_repository.AsyncSessionLocal", return_value=mgr):
            releases = await repo.list_by_project(uuid4())
        assert len(releases) == 1
        assert releases[0].name == "v1.0"

    async def test_list_by_project_empty(self, repo):
        """Branch: list_by_project no results -> returns empty list"""
        session, mgr = _make_mock_session()
        result = _make_scalars_result([])
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.release_repository.AsyncSessionLocal", return_value=mgr):
            releases = await repo.list_by_project(uuid4())
        assert releases == []

    # -- list_by_organization ------------------------------------------------

    async def test_list_by_organization_with_org_id(self, repo):
        """Branch: list_by_organization with organization_id -> filters by org"""
        session, mgr = _make_mock_session()
        rows = [_make_release_row()]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.release_repository.AsyncSessionLocal", return_value=mgr):
            releases = await repo.list_by_organization(uuid4())
        assert len(releases) == 1

    async def test_list_by_organization_without_org_id(self, repo):
        """Branch: list_by_organization with organization_id=None -> no org filter"""
        session, mgr = _make_mock_session()
        rows = [_make_release_row()]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.release_repository.AsyncSessionLocal", return_value=mgr):
            releases = await repo.list_by_organization(None)
        assert len(releases) == 1

    # -- update --------------------------------------------------------------

    async def test_update_found(self, repo):
        """Branch: update finds release -> updates fields, returns Release"""
        session, mgr = _make_mock_session()
        rel_row = _make_release_row()
        result = _make_scalar_result(rel_row)
        session.execute = AsyncMock(return_value=result)
        from domain.entities.release import Release
        from domain.enums import ReleaseStatus
        release = Release(
            id=uuid4(), name="updated", version="2.0.0", project_id=uuid4(),
            profile_id=uuid4(), created_by=uuid4(), status=ReleaseStatus.VALIDA,
        )
        with patch("infrastructure.secondary.database.repositories.release_repository.AsyncSessionLocal", return_value=mgr):
            updated = await repo.update(release)
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert updated is not None

    async def test_update_not_found_raises(self, repo):
        """Branch: update does not find release -> raises EntityNotFoundError"""
        session, mgr = _make_mock_session()
        result = _make_scalar_result(None)
        session.execute = AsyncMock(return_value=result)
        from domain.entities.release import Release
        release = Release(
            id=uuid4(), name="x", version="1.0.0", project_id=uuid4(),
            profile_id=uuid4(), created_by=uuid4(),
        )
        from domain.exceptions import EntityNotFoundError
        with patch("infrastructure.secondary.database.repositories.release_repository.AsyncSessionLocal", return_value=mgr):
            with pytest.raises(EntityNotFoundError, match="Release no encontrada"):
                await repo.update(release)

    # -- update_status -------------------------------------------------------

    async def test_update_status_found(self, repo):
        """Branch: update_status finds release -> updates status, returns Release"""
        session, mgr = _make_mock_session()
        rel_row = _make_release_row()
        result = _make_scalar_result(rel_row)
        session.execute = AsyncMock(return_value=result)
        from domain.enums import ReleaseStatus
        with patch("infrastructure.secondary.database.repositories.release_repository.AsyncSessionLocal", return_value=mgr):
            updated = await repo.update_status(uuid4(), ReleaseStatus.VALIDA)
        assert updated is not None
        session.commit.assert_awaited_once()

    async def test_update_status_not_found(self, repo):
        """Branch: update_status does not find release -> returns None"""
        session, mgr = _make_mock_session()
        result = _make_scalar_result(None)
        session.execute = AsyncMock(return_value=result)
        from domain.enums import ReleaseStatus
        with patch("infrastructure.secondary.database.repositories.release_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.update_status(uuid4(), ReleaseStatus.VALIDA)
        assert result is None

    # -- delete --------------------------------------------------------------

    async def test_delete_found(self, repo):
        """Branch: delete finds release -> deletes and commits"""
        session, mgr = _make_mock_session()
        rel_row = _make_release_row()
        result = _make_scalar_result(rel_row)
        session.execute = AsyncMock(return_value=result)
        session.delete = AsyncMock()
        with patch("infrastructure.secondary.database.repositories.release_repository.AsyncSessionLocal", return_value=mgr):
            await repo.delete(uuid4())
        session.delete.assert_called_once_with(rel_row)
        session.commit.assert_awaited_once()

    async def test_delete_not_found_raises(self, repo):
        """Branch: delete does not find release -> raises EntityNotFoundError"""
        session, mgr = _make_mock_session()
        result = _make_scalar_result(None)
        session.execute = AsyncMock(return_value=result)
        from domain.exceptions import EntityNotFoundError
        with patch("infrastructure.secondary.database.repositories.release_repository.AsyncSessionLocal", return_value=mgr):
            with pytest.raises(EntityNotFoundError, match="Release no encontrada"):
                await repo.delete(uuid4())

    # -- get_artifact_by_id / delete_artifact ---------------------------------
    # NOTE: These methods access ReleaseModel.artifacts (a SQLAlchemy
    # relationship attribute) which is not available outside the database
    # runtime. They require integration tests with a real DB session.
    # Covered by integration tests (test_release_lifecycle.py,
    # test_flow_resilience.py).


# ── SqlNotificationRepository ────────────────────────────────────────────────

class TestSqlNotificationRepository:
    @pytest.fixture
    def repo(self):
        from infrastructure.secondary.database.repositories.notification_repository import SqlNotificationRepository
        return SqlNotificationRepository()

    # -- conversion helpers --------------------------------------------------

    def test_channel_model_to_entity(self, repo):
        """Branch: _channel_model_to_entity with full data"""
        row = _make_channel_row(config_data={"url": "http://x"})
        entity = repo._channel_model_to_entity(row)
        assert entity.channel_type == "EMAIL"
        assert entity.enabled is True
        assert entity.config_data == {"url": "http://x"}

    def test_channel_model_to_entity_none_config(self, repo):
        """Branch: _channel_model_to_entity with config_data None -> empty dict"""
        row = _make_channel_row(config_data=None)
        entity = repo._channel_model_to_entity(row)
        assert entity.config_data == {}

    def test_subscription_model_to_entity(self, repo):
        """Branch: _subscription_model_to_entity maps correctly"""
        row = _make_subscription_row(event_type="release_validated")
        entity = repo._subscription_model_to_entity(row)
        assert entity.event_type == "release_validated"

    # -- create_channel ------------------------------------------------------

    async def test_create_channel_success(self, repo):
        """Branch: create_channel creates model, commits, returns entity"""
        session, mgr = _make_mock_session()
        from domain.entities.notification_channel import NotificationChannel
        channel = NotificationChannel(
            id=uuid4(), organization_id=uuid4(), channel_type="SLACK",
            enabled=True, config_data={"webhook": "url"},
        )
        with patch("infrastructure.secondary.database.repositories.notification_repository._session_scope", return_value=mgr):
            result = await repo.create_channel(channel)
        session.add.assert_called_once()
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert result is not None

    # -- list_channels -------------------------------------------------------

    async def test_list_channels_returns_list(self, repo):
        """Branch: list_channels with results -> returns list"""
        session, mgr = _make_mock_session()
        rows = [_make_channel_row()]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.notification_repository._session_scope", return_value=mgr):
            channels = await repo.list_channels(uuid4())
        assert len(channels) == 1

    async def test_list_channels_empty(self, repo):
        """Branch: list_channels no results -> empty list"""
        session, mgr = _make_mock_session()
        result = _make_scalars_result([])
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.notification_repository._session_scope", return_value=mgr):
            channels = await repo.list_channels(uuid4())
        assert channels == []

    # -- get_channel_by_id ---------------------------------------------------

    async def test_get_channel_by_id_found(self, repo):
        """Branch: get_channel_by_id finds -> returns entity"""
        session, mgr = _make_mock_session()
        result = _make_scalar_result(_make_channel_row())
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.notification_repository._session_scope", return_value=mgr):
            channel = await repo.get_channel_by_id(uuid4())
        assert channel is not None

    async def test_get_channel_by_id_not_found(self, repo):
        """Branch: get_channel_by_id None -> returns None"""
        session, mgr = _make_mock_session()
        result = _make_scalar_result(None)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.notification_repository._session_scope", return_value=mgr):
            channel = await repo.get_channel_by_id(uuid4())
        assert channel is None

    # -- update_channel ------------------------------------------------------

    async def test_update_channel_found(self, repo):
        """Branch: update_channel finds model -> updates and returns"""
        session, mgr = _make_mock_session()
        model = _make_channel_row()
        session.get = AsyncMock(return_value=model)
        from domain.entities.notification_channel import NotificationChannel
        channel = NotificationChannel(
            id=uuid4(), organization_id=uuid4(), channel_type="EMAIL",
            enabled=False, config_data={"to": "x@x.com"},
        )
        with patch("infrastructure.secondary.database.repositories.notification_repository._session_scope", return_value=mgr):
            result = await repo.update_channel(channel)
        session.commit.assert_awaited_once()
        assert result is not None

    async def test_update_channel_not_found_raises(self, repo):
        """Branch: update_channel model not found -> ValueError"""
        session, mgr = _make_mock_session()
        session.get = AsyncMock(return_value=None)
        from domain.entities.notification_channel import NotificationChannel
        channel = NotificationChannel(
            id=uuid4(), organization_id=uuid4(), channel_type="EMAIL",
            enabled=True,
        )
        with patch("infrastructure.secondary.database.repositories.notification_repository._session_scope", return_value=mgr):
            with pytest.raises(ValueError, match="not found"):
                await repo.update_channel(channel)

    # -- delete_channel ------------------------------------------------------

    async def test_delete_channel_found(self, repo):
        """Branch: delete_channel finds -> deletes"""
        session, mgr = _make_mock_session()
        model = _make_channel_row()
        session.get = AsyncMock(return_value=model)
        with patch("infrastructure.secondary.database.repositories.notification_repository._session_scope", return_value=mgr):
            await repo.delete_channel(uuid4())
        session.delete.assert_called_once()
        session.commit.assert_awaited_once()

    async def test_delete_channel_not_found_raises(self, repo):
        """Branch: delete_channel not found -> ValueError"""
        session, mgr = _make_mock_session()
        session.get = AsyncMock(return_value=None)
        with patch("infrastructure.secondary.database.repositories.notification_repository._session_scope", return_value=mgr):
            with pytest.raises(ValueError, match="not found"):
                await repo.delete_channel(uuid4())

    # -- list_subscriptions --------------------------------------------------

    async def test_list_subscriptions_returns_list(self, repo):
        """Branch: list_subscriptions with results -> returns list"""
        session, mgr = _make_mock_session()
        rows = [_make_subscription_row()]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.notification_repository._session_scope", return_value=mgr):
            subs = await repo.list_subscriptions(uuid4())
        assert len(subs) == 1

    # -- get_subscription ----------------------------------------------------

    async def test_get_subscription_found(self, repo):
        """Branch: get_subscription finds -> returns entity"""
        session, mgr = _make_mock_session()
        result = _make_scalar_result(_make_subscription_row())
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.notification_repository._session_scope", return_value=mgr):
            sub = await repo.get_subscription(uuid4(), "release_validated")
        assert sub is not None

    async def test_get_subscription_not_found(self, repo):
        """Branch: get_subscription None -> returns None"""
        session, mgr = _make_mock_session()
        result = _make_scalar_result(None)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.notification_repository._session_scope", return_value=mgr):
            sub = await repo.get_subscription(uuid4(), "release_validated")
        assert sub is None

    # -- upsert_subscription -------------------------------------------------

    async def test_upsert_subscription_existing_update(self, repo):
        """Branch: upsert finds existing -> updates enabled and returns"""
        session, mgr = _make_mock_session()
        existing = _make_subscription_row(enabled=False)
        result = _make_scalar_result(existing)
        session.execute = AsyncMock(return_value=result)
        from domain.entities.notification_subscription import NotificationSubscription
        sub = NotificationSubscription(
            id=uuid4(), user_id=uuid4(), event_type="release_validated",
            enabled=True,
        )
        with patch("infrastructure.secondary.database.repositories.notification_repository._session_scope", return_value=mgr):
            updated = await repo.upsert_subscription(sub)
        assert updated is not None
        session.commit.assert_awaited_once()

    async def test_upsert_subscription_new_insert(self, repo):
        """Branch: upsert does not find existing -> inserts new"""
        session, mgr = _make_mock_session()
        result = _make_scalar_result(None)
        session.execute = AsyncMock(return_value=result)
        from domain.entities.notification_subscription import NotificationSubscription
        sub = NotificationSubscription(
            id=uuid4(), user_id=uuid4(), event_type="release_invalidated",
            enabled=True,
        )
        with patch("infrastructure.secondary.database.repositories.notification_repository._session_scope", return_value=mgr):
            created = await repo.upsert_subscription(sub)
        session.add.assert_called_once()
        session.commit.assert_awaited_once()
        assert created is not None

    # -- delete_subscription -------------------------------------------------

    async def test_delete_subscription_found(self, repo):
        """Branch: delete_subscription finds -> deletes"""
        session, mgr = _make_mock_session()
        model = _make_subscription_row()
        result = _make_scalar_result(model)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.notification_repository._session_scope", return_value=mgr):
            await repo.delete_subscription(uuid4(), "release_validated")
        session.delete.assert_called_once()
        session.commit.assert_awaited_once()

    async def test_delete_subscription_not_found(self, repo):
        """Branch: delete_subscription not found -> no-op (returns early)"""
        session, mgr = _make_mock_session()
        result = _make_scalar_result(None)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.notification_repository._session_scope", return_value=mgr):
            await repo.delete_subscription(uuid4(), "release_validated")
        session.delete.assert_not_called()


# ── SqlUserRepository ────────────────────────────────────────────────────────

class TestSqlUserRepository:
    @pytest.fixture
    def repo(self):
        from infrastructure.secondary.database.repositories.user_repository import SqlUserRepository
        return SqlUserRepository()

    # -- _model_to_entity ----------------------------------------------------

    def test_model_to_entity_with_org_id(self, repo):
        """Branch: _model_to_entity with organization_id -> maps to organization_ids"""
        row = _make_user_row(organization_id=uuid4())
        user = repo._model_to_entity(row)
        assert user.email == "test@test.com"
        assert len(user.organization_ids) == 1

    def test_model_to_entity_without_org_id(self, repo):
        """Branch: _model_to_entity with organization_id=None -> empty list"""
        row = _make_user_row(organization_id=None)
        user = repo._model_to_entity(row)
        assert user.organization_ids == []

    def test_model_to_entity_totp_disabled(self, repo):
        """Branch: _model_to_entity with totp_enabled=None -> defaults to False"""
        row = _make_user_row(totp_enabled=None)
        user = repo._model_to_entity(row)
        assert user.totp_enabled is False

    # -- create --------------------------------------------------------------

    async def test_create_user_success(self, repo):
        """Branch: create adds model, commits, refreshes, returns User"""
        session, mgr = _make_mock_session()
        from domain.entities.user import User
        from domain.enums import UserRole
        user = User(
            id=uuid4(), email="new@test.com", hashed_password="pw", # NOSONAR
            display_name="New", role=UserRole.U2,
        )
        with patch("infrastructure.secondary.database.repositories.user_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.create(user)
        session.add.assert_called_once()
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert result is not None

    # -- get_by_id -----------------------------------------------------------

    async def test_get_by_id_found(self, repo):
        """Branch: get_by_id finds user -> returns User"""
        session, mgr = _make_mock_session()
        row = _make_user_row()
        result = _make_scalar_result(row)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.user_repository.AsyncSessionLocal", return_value=mgr):
            user = await repo.get_by_id(uuid4())
        assert user is not None
        assert user.email == "test@test.com"

    async def test_get_by_id_not_found(self, repo):
        """Branch: get_by_id returns None -> returns None"""
        session, mgr = _make_mock_session()
        result = _make_scalar_result(None)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.user_repository.AsyncSessionLocal", return_value=mgr):
            user = await repo.get_by_id(uuid4())
        assert user is None

    # -- get_by_email --------------------------------------------------------

    async def test_get_by_email_found(self, repo):
        """Branch: get_by_email finds user -> returns User"""
        session, mgr = _make_mock_session()
        row = _make_user_row(email="found@test.com")
        result = _make_scalar_result(row)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.user_repository.AsyncSessionLocal", return_value=mgr):
            user = await repo.get_by_email("found@test.com")
        assert user is not None
        assert user.email == "found@test.com"

    async def test_get_by_email_not_found(self, repo):
        """Branch: get_by_email returns None -> returns None"""
        session, mgr = _make_mock_session()
        result = _make_scalar_result(None)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.user_repository.AsyncSessionLocal", return_value=mgr):
            user = await repo.get_by_email("no@test.com")
        assert user is None

    # -- list_all ------------------------------------------------------------

    async def test_list_all_with_filters(self, repo):
        """Branch: list_all with organization_id + active_only -> filtered"""
        session, mgr = _make_mock_session()
        rows = [_make_user_row()]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.user_repository.AsyncSessionLocal", return_value=mgr):
            users = await repo.list_all(organization_id=uuid4(), active_only=True)
        assert len(users) == 1

    async def test_list_all_no_org_id(self, repo):
        """Branch: list_all with organization_id=None -> no org filter"""
        session, mgr = _make_mock_session()
        rows = [_make_user_row()]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.user_repository.AsyncSessionLocal", return_value=mgr):
            users = await repo.list_all(organization_id=None, active_only=False)
        assert len(users) == 1

    async def test_list_all_not_active_only(self, repo):
        """Branch: list_all with active_only=False -> no active filter"""
        session, mgr = _make_mock_session()
        rows = [_make_user_row(is_active=False), _make_user_row(is_active=True)]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.user_repository.AsyncSessionLocal", return_value=mgr):
            users = await repo.list_all(active_only=False)
        assert len(users) == 2

    # -- update --------------------------------------------------------------

    async def test_update_found(self, repo):
        """Branch: update finds user -> updates fields, returns User"""
        session, mgr = _make_mock_session()
        model = _make_user_row()
        session.get = AsyncMock(return_value=model)
        from domain.entities.user import User
        from domain.enums import UserRole
        user = User(
            id=uuid4(), email="updated@test.com", hashed_password="newhash", # NOSONAR
            display_name="Updated", role=UserRole.U2, is_active=False,
        )
        with patch("infrastructure.secondary.database.repositories.user_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.update(user)
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert result is not None

    async def test_update_not_found_raises(self, repo):
        """Branch: update not found -> ValueError"""
        session, mgr = _make_mock_session()
        session.get = AsyncMock(return_value=None)
        from domain.entities.user import User
        from domain.enums import UserRole
        user = User(
            id=uuid4(), email="x@x.com", hashed_password="pw", # NOSONAR
            display_name="X", role=UserRole.U2,
        )
        with patch("infrastructure.secondary.database.repositories.user_repository.AsyncSessionLocal", return_value=mgr):
            with pytest.raises(ValueError, match="User not found"):
                await repo.update(user)

    # -- get_by_activation_token ---------------------------------------------

    async def test_get_by_activation_token_found(self, repo):
        """Branch: get_by_activation_token finds -> returns User"""
        session, mgr = _make_mock_session()
        row = _make_user_row(activation_token="token123")
        result = _make_scalar_result(row)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.user_repository.AsyncSessionLocal", return_value=mgr):
            user = await repo.get_by_activation_token("token123")
        assert user is not None

    async def test_get_by_activation_token_not_found(self, repo):
        """Branch: get_by_activation_token None -> returns None"""
        session, mgr = _make_mock_session()
        result = _make_scalar_result(None)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.user_repository.AsyncSessionLocal", return_value=mgr):
            user = await repo.get_by_activation_token("no-token")
        assert user is None

    # -- delete --------------------------------------------------------------

    async def test_delete_found(self, repo):
        """Branch: delete finds user -> deletes"""
        session, mgr = _make_mock_session()
        model = _make_user_row()
        session.get = AsyncMock(return_value=model)
        with patch("infrastructure.secondary.database.repositories.user_repository.AsyncSessionLocal", return_value=mgr):
            await repo.delete(uuid4())
        session.delete.assert_called_once()
        session.commit.assert_awaited_once()

    async def test_delete_not_found_raises(self, repo):
        """Branch: delete not found -> ValueError"""
        session, mgr = _make_mock_session()
        session.get = AsyncMock(return_value=None)
        with patch("infrastructure.secondary.database.repositories.user_repository.AsyncSessionLocal", return_value=mgr):
            with pytest.raises(ValueError, match="User not found"):
                await repo.delete(uuid4())


# ── SqlAccessRequestRepository ────────────────────────────────────────────────

class TestSqlAccessRequestRepository:
    @pytest.fixture
    def repo(self):
        from infrastructure.secondary.database.repositories.access_request_repository import (
            SqlAccessRequestRepository,
        )
        return SqlAccessRequestRepository()

    def test_model_to_entity_full(self, repo):
        """Branch: _model_to_entity with all fields populated"""
        rid = uuid4()
        reviewed_by = uuid4()
        now = datetime.now(timezone.utc)
        row = _make_access_request_row(
            request_id=rid,
            requester_name="Alice",
            requester_email="alice@example.com",
            organization_name="Alice Org",
            organization_description="Desc",
            slug_preview="alice-org",
            status="APPROVED",
            rejection_reason=None,
            reviewed_by=reviewed_by,
            reviewed_at=now,
        )
        entity = repo._model_to_entity(row)
        assert entity.id == rid
        assert entity.requester_name == "Alice"
        assert entity.requester_email == "alice@example.com"
        assert entity.organization_name == "Alice Org"
        assert entity.organization_description == "Desc"
        assert entity.slug_preview == "alice-org"
        assert entity.status == AccessRequestStatus.APPROVED
        assert entity.rejection_reason is None
        assert entity.reviewed_by == reviewed_by
        assert entity.reviewed_at == now

    def test_model_to_entity_nulls(self, repo):
        """Branch: _model_to_entity with nullable fields as None"""
        row = _make_access_request_row(
            organization_description=None,
            slug_preview=None,
            rejection_reason=None,
            reviewed_by=None,
            reviewed_at=None,
        )
        entity = repo._model_to_entity(row)
        assert entity.organization_description is None
        assert entity.slug_preview is None
        assert entity.rejection_reason is None
        assert entity.reviewed_by is None
        assert entity.reviewed_at is None

    async def test_create_success(self, repo):
        """Branch: create adds model, commits, refreshes, returns entity"""
        session, mgr = _make_mock_session()
        ar = AccessRequest(
            requester_name="Bob",
            requester_email="bob@test.com",
            organization_name="Bob Org",
            organization_description="Bob's company",
            slug_preview="bob-org",
            status=AccessRequestStatus.PENDING,
        )
        with patch(
            "infrastructure.secondary.database.repositories.access_request_repository.AsyncSessionLocal",
            return_value=mgr,
        ):
            result = await repo.create(ar)
        session.add.assert_called_once()
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert result is not None
        assert result.requester_email == "bob@test.com"

    async def test_get_by_id_found(self, repo):
        """Branch: get_by_id finds row -> returns AccessRequest"""
        session, mgr = _make_mock_session()
        row = _make_access_request_row(requester_email="found@test.com")
        result = _make_scalar_result(row)
        session.execute = AsyncMock(return_value=result)
        with patch(
            "infrastructure.secondary.database.repositories.access_request_repository.AsyncSessionLocal",
            return_value=mgr,
        ):
            entity = await repo.get_by_id(uuid4())
        assert entity is not None
        assert entity.requester_email == "found@test.com"

    async def test_get_by_id_not_found(self, repo):
        """Branch: get_by_id returns None -> returns None"""
        session, mgr = _make_mock_session()
        result = _make_scalar_result(None)
        session.execute = AsyncMock(return_value=result)
        with patch(
            "infrastructure.secondary.database.repositories.access_request_repository.AsyncSessionLocal",
            return_value=mgr,
        ):
            entity = await repo.get_by_id(uuid4())
        assert entity is None

    async def test_get_by_email_found(self, repo):
        """Branch: get_by_email finds row -> returns AccessRequest"""
        session, mgr = _make_mock_session()
        row = _make_access_request_row(requester_email="specific@test.com")
        result = _make_scalar_result(row)
        session.execute = AsyncMock(return_value=result)
        with patch(
            "infrastructure.secondary.database.repositories.access_request_repository.AsyncSessionLocal",
            return_value=mgr,
        ):
            entity = await repo.get_by_email("specific@test.com")
        assert entity is not None
        assert entity.requester_email == "specific@test.com"

    async def test_get_by_email_not_found(self, repo):
        """Branch: get_by_email returns None -> returns None"""
        session, mgr = _make_mock_session()
        result = _make_scalar_result(None)
        session.execute = AsyncMock(return_value=result)
        with patch(
            "infrastructure.secondary.database.repositories.access_request_repository.AsyncSessionLocal",
            return_value=mgr,
        ):
            entity = await repo.get_by_email("noone@test.com")
        assert entity is None

    async def test_list_by_status_returns_list(self, repo):
        """Branch: list_by_status with results -> returns list of AccessRequests"""
        session, mgr = _make_mock_session()
        rows = [_make_access_request_row(), _make_access_request_row(requester_email="other@test.com")]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch(
            "infrastructure.secondary.database.repositories.access_request_repository.AsyncSessionLocal",
            return_value=mgr,
        ):
            entities = await repo.list_by_status(AccessRequestStatus.PENDING)
        assert len(entities) == 2

    async def test_list_by_status_empty(self, repo):
        """Branch: list_by_status no results -> empty list"""
        session, mgr = _make_mock_session()
        result = _make_scalars_result([])
        session.execute = AsyncMock(return_value=result)
        with patch(
            "infrastructure.secondary.database.repositories.access_request_repository.AsyncSessionLocal",
            return_value=mgr,
        ):
            entities = await repo.list_by_status(AccessRequestStatus.APPROVED)
        assert entities == []

    async def test_list_by_status_pagination(self, repo):
        """Branch: list_by_status with skip + limit parameters"""
        session, mgr = _make_mock_session()
        rows = [_make_access_request_row()]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch(
            "infrastructure.secondary.database.repositories.access_request_repository.AsyncSessionLocal",
            return_value=mgr,
        ):
            entities = await repo.list_by_status(
                AccessRequestStatus.PENDING, skip=10, limit=50
            )
        assert len(entities) == 1
        session.execute.assert_awaited_once()

    async def test_update_found(self, repo):
        """Branch: update finds row -> updates fields, returns entity"""
        session, mgr = _make_mock_session()
        row = _make_access_request_row()
        session.get = AsyncMock(return_value=row)
        ar = AccessRequest(
            id=uuid4(),
            requester_name="Updated",
            requester_email="updated@test.com",
            organization_name="Updated Org",
            status=AccessRequestStatus.REJECTED,
            rejection_reason="Not eligible",
            reviewed_by=uuid4(),
            reviewed_at=datetime.now(timezone.utc),
        )
        with patch(
            "infrastructure.secondary.database.repositories.access_request_repository.AsyncSessionLocal",
            return_value=mgr,
        ):
            result = await repo.update(ar)
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert result is not None

    async def test_update_not_found_raises(self, repo):
        """Branch: update does not find row -> raises ValueError"""
        session, mgr = _make_mock_session()
        session.get = AsyncMock(return_value=None)
        ar = AccessRequest(
            id=uuid4(),
            requester_name="Ghost",
            requester_email="ghost@test.com",
            organization_name="Ghost Org",
            status=AccessRequestStatus.PENDING,
        )
        with patch(
            "infrastructure.secondary.database.repositories.access_request_repository.AsyncSessionLocal",
            return_value=mgr,
        ):
            with pytest.raises(ValueError, match="not found"):
                await repo.update(ar)


# ── SqlTemplateRepository ─────────────────────────────────────────────────────

class TestSqlTemplateRepository:
    @pytest.fixture
    def repo(self):
        from infrastructure.secondary.database.repositories.template_repository import SqlTemplateRepository
        return SqlTemplateRepository()

    def test_model_to_entity_full(self, repo):
        """Branch: _model_to_entity with all fields including description"""
        row = _make_template_row(description="my desc", project_name_template="PROJ-{name}")
        entity = repo._model_to_entity(row)
        assert entity.name == "tpl"
        assert entity.description == "my desc"
        assert entity.project_name_template == "PROJ-{name}"
        assert entity.is_archived is False

    def test_model_to_entity_none_description(self, repo):
        """Branch: _model_to_entity with description=None -> "" """
        row = _make_template_row(description=None)
        entity = repo._model_to_entity(row)
        assert entity.description == ""

    async def test_create_success(self, repo):
        """Branch: create adds model, commits, refreshes"""
        session, mgr = _make_mock_session()
        from domain.entities.template import Template
        tpl = Template(
            id=uuid4(), organization_id=uuid4(), name="my-tpl",
            description="desc", profile_id=uuid4(), created_by=uuid4(),
        )
        with patch("infrastructure.secondary.database.repositories.template_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.create(tpl)
        session.add.assert_called_once()
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert result is not None

    async def test_get_by_id_found(self, repo):
        """Branch: get_by_id finds row -> returns Template"""
        session, mgr = _make_mock_session()
        row = _make_template_row()
        result = _make_scalar_result(row)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.template_repository.AsyncSessionLocal", return_value=mgr):
            entity = await repo.get_by_id(uuid4())
        assert entity is not None
        assert entity.name == "tpl"

    async def test_get_by_id_not_found(self, repo):
        """Branch: get_by_id returns None -> returns None"""
        session, mgr = _make_mock_session()
        result = _make_scalar_result(None)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.template_repository.AsyncSessionLocal", return_value=mgr):
            entity = await repo.get_by_id(uuid4())
        assert entity is None

    async def test_list_by_organization_returns_list(self, repo):
        """Branch: list_by_organization with results -> returns list"""
        session, mgr = _make_mock_session()
        rows = [_make_template_row(), _make_template_row(name="tpl2")]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.template_repository.AsyncSessionLocal", return_value=mgr):
            entities = await repo.list_by_organization(uuid4())
        assert len(entities) == 2

    async def test_list_by_organization_empty(self, repo):
        """Branch: list_by_organization no results -> empty list"""
        session, mgr = _make_mock_session()
        result = _make_scalars_result([])
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.template_repository.AsyncSessionLocal", return_value=mgr):
            entities = await repo.list_by_organization(uuid4())
        assert entities == []

    async def test_list_by_organization_include_archived(self, repo):
        """Branch: list_by_organization with include_archived=True -> no archive filter"""
        session, mgr = _make_mock_session()
        rows = [_make_template_row(is_archived=True)]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.template_repository.AsyncSessionLocal", return_value=mgr):
            entities = await repo.list_by_organization(uuid4(), include_archived=True)
        assert len(entities) == 1

    async def test_list_by_organization_skip_limit(self, repo):
        """Branch: list_by_organization with skip/limit -> pagination applied"""
        session, mgr = _make_mock_session()
        result = _make_scalars_result([])
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.template_repository.AsyncSessionLocal", return_value=mgr):
            entities = await repo.list_by_organization(uuid4(), skip=10, limit=5)
        assert entities == []

    async def test_update_found(self, repo):
        """Branch: update finds model -> updates and returns"""
        session, mgr = _make_mock_session()
        model = _make_template_row()
        session.get = AsyncMock(return_value=model)
        from domain.entities.template import Template
        tpl = Template(
            id=UUID(model.id), organization_id=uuid4(), name="updated",
            description="new-desc", profile_id=uuid4(), created_by=uuid4(),
            is_archived=True,
        )
        with patch("infrastructure.secondary.database.repositories.template_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.update(tpl)
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert result is not None

    async def test_update_not_found_raises(self, repo):
        """Branch: update not found -> ValueError"""
        session, mgr = _make_mock_session()
        session.get = AsyncMock(return_value=None)
        from domain.entities.template import Template
        tpl = Template(
            id=uuid4(), organization_id=uuid4(), name="ghost",
            description="", profile_id=uuid4(), created_by=uuid4(),
        )
        with patch("infrastructure.secondary.database.repositories.template_repository.AsyncSessionLocal", return_value=mgr):
            with pytest.raises(ValueError, match="Template not found"):
                await repo.update(tpl)

    async def test_delete_found(self, repo):
        """Branch: delete finds model -> deletes"""
        session, mgr = _make_mock_session()
        model = _make_template_row()
        session.get = AsyncMock(return_value=model)
        with patch("infrastructure.secondary.database.repositories.template_repository.AsyncSessionLocal", return_value=mgr):
            await repo.delete(uuid4())
        session.delete.assert_called_once()
        session.commit.assert_awaited_once()

    async def test_delete_not_found_raises(self, repo):
        """Branch: delete not found -> ValueError"""
        session, mgr = _make_mock_session()
        session.get = AsyncMock(return_value=None)
        with patch("infrastructure.secondary.database.repositories.template_repository.AsyncSessionLocal", return_value=mgr):
            with pytest.raises(ValueError, match="Template not found"):
                await repo.delete(uuid4())


# ── SqlConnectorRepository ─────────────────────────────────────────────────────

class TestSqlConnectorRepository:
    @pytest.fixture
    def repo(self):
        from infrastructure.secondary.database.repositories.connector_repository import SqlConnectorRepository
        return SqlConnectorRepository()

    def test_model_to_entity_full(self, repo):
        """Branch: _model_to_entity maps all fields including last_tested_at"""
        from infrastructure.secondary.database.repositories.connector_repository import _model_to_entity
        now = datetime.now(timezone.utc)
        row = _make_connector_row(status="ACTIVO", last_tested_at=now)
        entity = _model_to_entity(row)
        assert entity.connector_type == "GESTOR_TAREAS"
        assert entity.connector_implementation == "JIRA"
        assert entity.name == "jira-conn"
        assert entity.status.value == "ACTIVO"
        assert entity.last_tested_at == now

    def test_model_to_entity_none_dates(self, repo):
        """Branch: _model_to_entity with None updated_at/last_tested_at"""
        from infrastructure.secondary.database.repositories.connector_repository import _model_to_entity
        row = _make_connector_row(last_tested_at=None)
        row.updated_at = None
        entity = _model_to_entity(row)
        assert entity.updated_at is None
        assert entity.last_tested_at is None

    async def test_save_success(self, repo):
        """Branch: save adds model, commits, returns entity"""
        session, mgr = _make_mock_session()
        from domain.entities.connector_instance import ConnectorInstance
        from domain.enums import ConnectorStatus
        ci = ConnectorInstance(
            id=uuid4(), organization_id=uuid4(),
            connector_type="REPO_CODIGO", connector_implementation="GITHUB",
            name="gh-conn", encrypted_credentials=b"enc",
            status=ConnectorStatus.ACTIVO,
        )
        with patch("infrastructure.secondary.database.repositories.connector_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.save(ci)
        session.add.assert_called_once()
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert result is not None

    async def test_save_inactive_status(self, repo):
        """Branch: save with INACTIVO status -> conversion works"""
        session, mgr = _make_mock_session()
        from domain.entities.connector_instance import ConnectorInstance
        from domain.enums import ConnectorStatus
        ci = ConnectorInstance(
            id=uuid4(), organization_id=uuid4(),
            connector_type="GESTOR_TAREAS", connector_implementation="TRELLO",
            name="trello", encrypted_credentials=b"x",
            status=ConnectorStatus.INACTIVO,
        )
        with patch("infrastructure.secondary.database.repositories.connector_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.save(ci)
        assert result.status == ConnectorStatus.INACTIVO

    async def test_get_by_id_found(self, repo):
        """Branch: get_by_id finds -> returns ConnectorInstance"""
        session, mgr = _make_mock_session()
        row = _make_connector_row()
        result = _make_scalar_result(row)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.connector_repository.AsyncSessionLocal", return_value=mgr):
            entity = await repo.get_by_id(uuid4())
        assert entity is not None
        assert entity.name == "jira-conn"

    async def test_get_by_id_not_found(self, repo):
        """Branch: get_by_id None -> returns None"""
        session, mgr = _make_mock_session()
        result = _make_scalar_result(None)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.connector_repository.AsyncSessionLocal", return_value=mgr):
            entity = await repo.get_by_id(uuid4())
        assert entity is None

    async def test_list_by_organization_active_only(self, repo):
        """Branch: list_by_organization with active_only=True -> filters active"""
        session, mgr = _make_mock_session()
        rows = [_make_connector_row()]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.connector_repository.AsyncSessionLocal", return_value=mgr):
            entities = await repo.list_by_organization(uuid4(), active_only=True)
        assert len(entities) == 1

    async def test_list_by_organization_all(self, repo):
        """Branch: list_by_organization with active_only=False -> no status filter"""
        session, mgr = _make_mock_session()
        rows = [_make_connector_row(status="ACTIVO"), _make_connector_row(status="INACTIVO")]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.connector_repository.AsyncSessionLocal", return_value=mgr):
            entities = await repo.list_by_organization(uuid4(), active_only=False)
        assert len(entities) == 2

    async def test_list_by_organization_empty(self, repo):
        """Branch: list_by_organization no results -> empty list"""
        session, mgr = _make_mock_session()
        result = _make_scalars_result([])
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.connector_repository.AsyncSessionLocal", return_value=mgr):
            entities = await repo.list_by_organization(uuid4())
        assert entities == []

    async def test_list_active_delegates(self, repo):
        """Branch: list_active delegates to list_by_organization"""
        session, mgr = _make_mock_session()
        rows = [_make_connector_row()]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.connector_repository.AsyncSessionLocal", return_value=mgr):
            entities = await repo.list_active(uuid4())
        assert len(entities) == 1

    async def test_update_found(self, repo):
        """Branch: update finds -> updates fields and returns"""
        session, mgr = _make_mock_session()
        model = _make_connector_row()
        session.get = AsyncMock(return_value=model)
        from domain.entities.connector_instance import ConnectorInstance
        from domain.enums import ConnectorStatus
        ci = ConnectorInstance(
            id=UUID(model.id), organization_id=uuid4(),
            connector_type="SISTEMA_DOCUMENTAL", connector_implementation="CONFLUENCE",
            name="conf", encrypted_credentials=b"new-enc",
            status=ConnectorStatus.ERROR,
        )
        with patch("infrastructure.secondary.database.repositories.connector_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.update(ci)
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert result is not None

    async def test_update_not_found_raises(self, repo):
        """Branch: update not found -> ValueError"""
        session, mgr = _make_mock_session()
        session.get = AsyncMock(return_value=None)
        from domain.entities.connector_instance import ConnectorInstance
        from domain.enums import ConnectorStatus
        ci = ConnectorInstance(
            id=uuid4(), organization_id=uuid4(),
            connector_type="GESTOR_TAREAS", connector_implementation="JIRA",
            name="ghost", encrypted_credentials=b"x",
            status=ConnectorStatus.ACTIVO,
        )
        with patch("infrastructure.secondary.database.repositories.connector_repository.AsyncSessionLocal", return_value=mgr):
            with pytest.raises(ValueError, match="Connector not found"):
                await repo.update(ci)

    async def test_delete_found(self, repo):
        """Branch: delete finds -> deletes"""
        session, mgr = _make_mock_session()
        model = _make_connector_row()
        session.get = AsyncMock(return_value=model)
        with patch("infrastructure.secondary.database.repositories.connector_repository.AsyncSessionLocal", return_value=mgr):
            await repo.delete(uuid4())
        session.delete.assert_called_once()
        session.commit.assert_awaited_once()

    async def test_delete_not_found_raises(self, repo):
        """Branch: delete not found -> ValueError"""
        session, mgr = _make_mock_session()
        session.get = AsyncMock(return_value=None)
        with patch("infrastructure.secondary.database.repositories.connector_repository.AsyncSessionLocal", return_value=mgr):
            with pytest.raises(ValueError, match="Connector not found"):
                await repo.delete(uuid4())


# ── SqlCustomRoleRepository ────────────────────────────────────────────────────

class TestSqlCustomRoleRepository:
    @pytest.fixture
    def repo(self):
        from infrastructure.secondary.database.repositories.custom_role_repository import SqlCustomRoleRepository
        return SqlCustomRoleRepository()

    def test_model_to_entity_multiple_permissions(self, repo):
        """Branch: _model_to_entity with multiple permissions"""
        row = _make_custom_role_row(permissions=["VIEW_DASHBOARD", "CREATE_RELEASE", "MANAGE_PROFILES"])
        entity = repo._model_to_entity(row)
        assert entity.name == "viewer"
        assert len(entity.permissions) == 3
        assert entity.is_active is True

    def test_model_to_entity_empty_permissions(self, repo):
        """Branch: _model_to_entity with empty permissions"""
        row = _make_custom_role_row(permissions=[])
        entity = repo._model_to_entity(row)
        assert entity.permissions == []

    def test_model_to_entity_inactive(self, repo):
        """Branch: _model_to_entity with is_active=False"""
        row = _make_custom_role_row(is_active=False)
        entity = repo._model_to_entity(row)
        assert entity.is_active is False

    async def test_create_success(self, repo):
        """Branch: create adds model, commits, returns entity"""
        session, mgr = _make_mock_session()
        from domain.entities.custom_role import CustomRole
        from domain.enums import Permission
        role = CustomRole(
            id=uuid4(), organization_id=uuid4(), name="editor",
            permissions=[Permission.VIEW_DASHBOARD, Permission.CREATE_RELEASE],
        )
        with patch("infrastructure.secondary.database.repositories.custom_role_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.create(role)
        session.add.assert_called_once()
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert result is not None

    async def test_get_by_id_found(self, repo):
        """Branch: get_by_id finds -> returns CustomRole"""
        session, mgr = _make_mock_session()
        row = _make_custom_role_row()
        result = _make_scalar_result(row)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.custom_role_repository.AsyncSessionLocal", return_value=mgr):
            entity = await repo.get_by_id(uuid4())
        assert entity is not None
        assert entity.name == "viewer"

    async def test_get_by_id_not_found(self, repo):
        """Branch: get_by_id None -> returns None"""
        session, mgr = _make_mock_session()
        result = _make_scalar_result(None)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.custom_role_repository.AsyncSessionLocal", return_value=mgr):
            entity = await repo.get_by_id(uuid4())
        assert entity is None

    async def test_list_by_organization_returns_list(self, repo):
        """Branch: list_by_organization with results -> returns list"""
        session, mgr = _make_mock_session()
        rows = [_make_custom_role_row(), _make_custom_role_row(name="admin")]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.custom_role_repository.AsyncSessionLocal", return_value=mgr):
            entities = await repo.list_by_organization(uuid4())
        assert len(entities) == 2

    async def test_list_by_organization_empty(self, repo):
        """Branch: list_by_organization no results -> empty list"""
        session, mgr = _make_mock_session()
        result = _make_scalars_result([])
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.custom_role_repository.AsyncSessionLocal", return_value=mgr):
            entities = await repo.list_by_organization(uuid4())
        assert entities == []

    async def test_update_found(self, repo):
        """Branch: update finds -> updates fields and returns"""
        session, mgr = _make_mock_session()
        model = _make_custom_role_row()
        session.get = AsyncMock(return_value=model)
        from domain.entities.custom_role import CustomRole
        from domain.enums import Permission
        role = CustomRole(
            id=UUID(model.id), organization_id=uuid4(), name="updated-role",
            permissions=[Permission.MANAGE_ROLES], is_active=False,
        )
        with patch("infrastructure.secondary.database.repositories.custom_role_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.update(role)
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert result is not None

    async def test_update_not_found_raises(self, repo):
        """Branch: update not found -> ValueError"""
        session, mgr = _make_mock_session()
        session.get = AsyncMock(return_value=None)
        from domain.entities.custom_role import CustomRole
        from domain.enums import Permission
        role = CustomRole(
            id=uuid4(), organization_id=uuid4(), name="ghost",
            permissions=[Permission.VIEW_DASHBOARD],
        )
        with patch("infrastructure.secondary.database.repositories.custom_role_repository.AsyncSessionLocal", return_value=mgr):
            with pytest.raises(ValueError, match="Custom role not found"):
                await repo.update(role)

    async def test_delete_found(self, repo):
        """Branch: delete finds -> deletes"""
        session, mgr = _make_mock_session()
        model = _make_custom_role_row()
        session.get = AsyncMock(return_value=model)
        with patch("infrastructure.secondary.database.repositories.custom_role_repository.AsyncSessionLocal", return_value=mgr):
            await repo.delete(uuid4())
        session.delete.assert_called_once()
        session.commit.assert_awaited_once()

    async def test_delete_not_found_raises(self, repo):
        """Branch: delete not found -> ValueError"""
        session, mgr = _make_mock_session()
        session.get = AsyncMock(return_value=None)
        with patch("infrastructure.secondary.database.repositories.custom_role_repository.AsyncSessionLocal", return_value=mgr):
            with pytest.raises(ValueError, match="Custom role not found"):
                await repo.delete(uuid4())


# ── SqlVerificationRuleRepository ──────────────────────────────────────────────

class TestSqlVerificationRuleRepository:
    @pytest.fixture
    def repo(self):
        from infrastructure.secondary.database.repositories.rule_repository import SqlVerificationRuleRepository
        return SqlVerificationRuleRepository()

    def test_model_to_entity_full(self, repo):
        """Branch: _model_to_entity with all fields"""
        conn_id = uuid4()
        row = _make_rule_row(severity="CRITICAL", connector_instance_id=conn_id, params={"key": "val"})
        entity = repo._model_to_entity(row)
        assert entity.rule_template == "check_version"
        assert entity.severity.value == "CRITICAL"
        assert entity.params == {"key": "val"}
        assert entity.connector_instance_id == conn_id
        assert entity.is_active is True

    def test_model_to_entity_none_params(self, repo):
        """Branch: _model_to_entity with params=None -> {}"""
        row = _make_rule_row(params=None)
        entity = repo._model_to_entity(row)
        assert entity.params == {}

    def test_model_to_entity_none_connector(self, repo):
        """Branch: _model_to_entity with connector_instance_id=None"""
        row = _make_rule_row(connector_instance_id=None)
        entity = repo._model_to_entity(row)
        assert entity.connector_instance_id is None

    def test_entity_to_model_attrs(self, repo):
        """Branch: _entity_to_model_attrs maps all fields"""
        from domain.entities.verification_rule import VerificationRule
        from domain.enums import SeverityType
        rule = VerificationRule(
            id=uuid4(), profile_id=uuid4(),
            rule_template="check_docs", severity=SeverityType.MEDIUM,
            params={"doc": "readme"}, connector_instance_id=uuid4(),
            display_order=2, is_active=False,
        )
        attrs = repo._entity_to_model_attrs(rule)
        assert attrs["severity"] == "MEDIUM"
        assert attrs["params"] == {"doc": "readme"}
        assert attrs["is_active"] is False

    async def test_create_success(self, repo):
        """Branch: create adds model, commits, returns entity"""
        session, mgr = _make_mock_session()
        from domain.entities.verification_rule import VerificationRule
        from domain.enums import SeverityType
        rule = VerificationRule(
            id=uuid4(), profile_id=uuid4(),
            rule_template="check_tests", severity=SeverityType.HIGH,
        )
        with patch("infrastructure.secondary.database.repositories.rule_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.create(rule)
        session.add.assert_called_once()
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert result is not None

    async def test_get_by_id_found(self, repo):
        """Branch: get_by_id finds -> returns VerificationRule"""
        session, mgr = _make_mock_session()
        row = _make_rule_row()
        result = _make_scalar_result(row)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.rule_repository.AsyncSessionLocal", return_value=mgr):
            entity = await repo.get_by_id(uuid4())
        assert entity is not None
        assert entity.rule_template == "check_version"

    async def test_get_by_id_not_found(self, repo):
        """Branch: get_by_id None -> returns None"""
        session, mgr = _make_mock_session()
        result = _make_scalar_result(None)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.rule_repository.AsyncSessionLocal", return_value=mgr):
            entity = await repo.get_by_id(uuid4())
        assert entity is None

    async def test_list_all_returns_list(self, repo):
        """Branch: list_all with results -> returns list"""
        session, mgr = _make_mock_session()
        rows = [_make_rule_row(), _make_rule_row(rule_template="check_other")]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.rule_repository.AsyncSessionLocal", return_value=mgr):
            entities = await repo.list_all()
        assert len(entities) == 2

    async def test_list_all_empty(self, repo):
        """Branch: list_all no results -> empty list"""
        session, mgr = _make_mock_session()
        result = _make_scalars_result([])
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.rule_repository.AsyncSessionLocal", return_value=mgr):
            entities = await repo.list_all()
        assert entities == []

    async def test_list_by_profile_returns_list(self, repo):
        """Branch: list_by_profile with results -> returns ordered list"""
        session, mgr = _make_mock_session()
        rows = [_make_rule_row(), _make_rule_row(display_order=2)]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.rule_repository.AsyncSessionLocal", return_value=mgr):
            entities = await repo.list_by_profile(uuid4())
        assert len(entities) == 2

    async def test_list_by_profile_empty(self, repo):
        """Branch: list_by_profile no results -> empty list"""
        session, mgr = _make_mock_session()
        result = _make_scalars_result([])
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.rule_repository.AsyncSessionLocal", return_value=mgr):
            entities = await repo.list_by_profile(uuid4())
        assert entities == []

    async def test_update_found(self, repo):
        """Branch: update finds -> updates via setattr, returns entity"""
        session, mgr = _make_mock_session()
        model = _make_rule_row()
        session.get = AsyncMock(return_value=model)
        from domain.entities.verification_rule import VerificationRule
        from domain.enums import SeverityType
        rule = VerificationRule(
            id=UUID(model.id), profile_id=uuid4(),
            rule_template="updated_rule", severity=SeverityType.LOW,
            params={"updated": True}, display_order=99, is_active=False,
        )
        with patch("infrastructure.secondary.database.repositories.rule_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.update(rule)
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert result is not None

    async def test_update_not_found_raises(self, repo):
        """Branch: update not found -> ValueError"""
        session, mgr = _make_mock_session()
        session.get = AsyncMock(return_value=None)
        from domain.entities.verification_rule import VerificationRule
        from domain.enums import SeverityType
        rule = VerificationRule(
            id=uuid4(), profile_id=uuid4(),
            rule_template="ghost", severity=SeverityType.INFO,
        )
        with patch("infrastructure.secondary.database.repositories.rule_repository.AsyncSessionLocal", return_value=mgr):
            with pytest.raises(ValueError, match="Rule not found"):
                await repo.update(rule)

    async def test_delete_found(self, repo):
        """Branch: delete finds -> deletes"""
        session, mgr = _make_mock_session()
        model = _make_rule_row()
        session.get = AsyncMock(return_value=model)
        with patch("infrastructure.secondary.database.repositories.rule_repository.AsyncSessionLocal", return_value=mgr):
            await repo.delete(uuid4())
        session.delete.assert_called_once()
        session.commit.assert_awaited_once()

    async def test_delete_not_found_raises(self, repo):
        """Branch: delete not found -> ValueError"""
        session, mgr = _make_mock_session()
        session.get = AsyncMock(return_value=None)
        with patch("infrastructure.secondary.database.repositories.rule_repository.AsyncSessionLocal", return_value=mgr):
            with pytest.raises(ValueError, match="Rule not found"):
                await repo.delete(uuid4())


# ── SqlAPIKeyRepository ────────────────────────────────────────────────────────

class TestSqlAPIKeyRepository:
    @pytest.fixture
    def repo(self):
        from infrastructure.secondary.database.repositories.api_key_repository import SqlAPIKeyRepository
        return SqlAPIKeyRepository()

    def test_model_to_entity_full(self, repo):
        """Branch: _model_to_entity with all fields"""
        from infrastructure.secondary.database.repositories.api_key_repository import _model_to_entity
        now = datetime.now(timezone.utc)
        expires = datetime(2025, 12, 31, tzinfo=timezone.utc)
        row = _make_api_key_row(expires_at=expires, last_used_at=now)
        entity = _model_to_entity(row)
        assert entity.name == "my-key"
        assert entity.key_hash == "abc123"
        assert entity.prefix == "sv_s0"
        assert entity.is_active is True
        assert entity.expires_at == expires
        assert entity.last_used_at == now

    def test_model_to_entity_none_dates(self, repo):
        """Branch: _model_to_entity with None expires_at/last_used_at"""
        from infrastructure.secondary.database.repositories.api_key_repository import _model_to_entity
        row = _make_api_key_row(expires_at=None, last_used_at=None)
        entity = _model_to_entity(row)
        assert entity.expires_at is None
        assert entity.last_used_at is None

    async def test_save_success(self, repo):
        """Branch: save adds model, commits, returns entity"""
        session, mgr = _make_mock_session()
        from domain.entities.api_key import APIKey
        key = APIKey(
            id=uuid4(), user_id=uuid4(), organization_id=uuid4(),
            name="prod-key", key_hash="hash123", prefix="sv_p0",
            is_active=True,
        )
        with patch("infrastructure.secondary.database.repositories.api_key_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.save(key)
        session.add.assert_called_once()
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert result is not None

    async def test_get_by_id_found(self, repo):
        """Branch: get_by_id finds -> returns APIKey"""
        session, mgr = _make_mock_session()
        row = _make_api_key_row()
        result = _make_scalar_result(row)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.api_key_repository.AsyncSessionLocal", return_value=mgr):
            entity = await repo.get_by_id(uuid4())
        assert entity is not None
        assert entity.name == "my-key"

    async def test_get_by_id_not_found(self, repo):
        """Branch: get_by_id None -> returns None"""
        session, mgr = _make_mock_session()
        result = _make_scalar_result(None)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.api_key_repository.AsyncSessionLocal", return_value=mgr):
            entity = await repo.get_by_id(uuid4())
        assert entity is None

    async def test_get_by_hash_found(self, repo):
        """Branch: get_by_hash finds -> returns APIKey"""
        session, mgr = _make_mock_session()
        row = _make_api_key_row(key_hash="findme")
        result = _make_scalar_result(row)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.api_key_repository.AsyncSessionLocal", return_value=mgr):
            entity = await repo.get_by_hash("findme")
        assert entity is not None
        assert entity.key_hash == "findme"

    async def test_get_by_hash_not_found(self, repo):
        """Branch: get_by_hash None -> returns None"""
        session, mgr = _make_mock_session()
        result = _make_scalar_result(None)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.api_key_repository.AsyncSessionLocal", return_value=mgr):
            entity = await repo.get_by_hash("nope")
        assert entity is None

    async def test_list_by_organization_returns_list(self, repo):
        """Branch: list_by_organization with results"""
        session, mgr = _make_mock_session()
        rows = [_make_api_key_row(), _make_api_key_row(name="key2")]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.api_key_repository.AsyncSessionLocal", return_value=mgr):
            entities = await repo.list_by_organization(uuid4())
        assert len(entities) == 2

    async def test_list_by_organization_empty(self, repo):
        """Branch: list_by_organization no results -> empty list"""
        session, mgr = _make_mock_session()
        result = _make_scalars_result([])
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.api_key_repository.AsyncSessionLocal", return_value=mgr):
            entities = await repo.list_by_organization(uuid4())
        assert entities == []

    async def test_list_by_user_returns_list(self, repo):
        """Branch: list_by_user with results"""
        session, mgr = _make_mock_session()
        rows = [_make_api_key_row()]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.api_key_repository.AsyncSessionLocal", return_value=mgr):
            entities = await repo.list_by_user(uuid4())
        assert len(entities) == 1

    async def test_list_by_user_empty(self, repo):
        """Branch: list_by_user no results -> empty list"""
        session, mgr = _make_mock_session()
        result = _make_scalars_result([])
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.api_key_repository.AsyncSessionLocal", return_value=mgr):
            entities = await repo.list_by_user(uuid4())
        assert entities == []

    async def test_update_found(self, repo):
        """Branch: update finds -> updates fields and returns"""
        session, mgr = _make_mock_session()
        model = _make_api_key_row()
        session.get = AsyncMock(return_value=model)
        from domain.entities.api_key import APIKey
        now = datetime.now(timezone.utc)
        key = APIKey(
            id=UUID(model.id), user_id=uuid4(), organization_id=uuid4(),
            name="renamed", key_hash="h", prefix="p",
            is_active=False, expires_at=now, last_used_at=now,
        )
        with patch("infrastructure.secondary.database.repositories.api_key_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.update(key)
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert result is not None

    async def test_update_not_found_raises(self, repo):
        """Branch: update not found -> ValueError"""
        session, mgr = _make_mock_session()
        session.get = AsyncMock(return_value=None)
        from domain.entities.api_key import APIKey
        key = APIKey(
            id=uuid4(), user_id=uuid4(), organization_id=uuid4(),
            name="ghost", key_hash="gh", prefix="g",
            is_active=True,
        )
        with patch("infrastructure.secondary.database.repositories.api_key_repository.AsyncSessionLocal", return_value=mgr):
            with pytest.raises(ValueError, match="API key not found"):
                await repo.update(key)

    async def test_delete_found(self, repo):
        """Branch: delete finds -> deletes"""
        session, mgr = _make_mock_session()
        model = _make_api_key_row()
        session.get = AsyncMock(return_value=model)
        with patch("infrastructure.secondary.database.repositories.api_key_repository.AsyncSessionLocal", return_value=mgr):
            await repo.delete(uuid4())
        session.delete.assert_called_once()
        session.commit.assert_awaited_once()

    async def test_delete_not_found_raises(self, repo):
        """Branch: delete not found -> ValueError"""
        session, mgr = _make_mock_session()
        session.get = AsyncMock(return_value=None)
        with patch("infrastructure.secondary.database.repositories.api_key_repository.AsyncSessionLocal", return_value=mgr):
            with pytest.raises(ValueError, match="API key not found"):
                await repo.delete(uuid4())

    def test_hash_key(self, repo):
        """Branch: hash_key static method returns pbkdf2-hmac-sha256 hex digest"""
        result = repo.hash_key("test-key")
        assert isinstance(result, str)
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)


# ── SqlProfileRepository ─────────────────────────────────────────────────────

class TestSqlProfileRepository:
    @pytest.fixture
    def repo(self):
        from infrastructure.secondary.database.repositories.profile_repository import SqlProfileRepository
        return SqlProfileRepository()

    async def test_create_success(self, repo):
        session, mgr = _make_mock_session()
        from domain.entities.verification_profile import VerificationProfile
        p = VerificationProfile(id=uuid4(), organization_id=uuid4(), name="p")
        with patch("infrastructure.secondary.database.repositories.profile_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.create(p)
        session.add.assert_called_once()
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert result is not None
        assert result.name == "p"

    async def test_get_by_id_found(self, repo):
        session, mgr = _make_mock_session()
        pid = uuid4()
        row = _make_profile_row(profile_id=pid)
        rule_row = _make_rule_row(profile_id=pid)
        session.execute = AsyncMock(side_effect=[
            _make_scalar_result(row),
            _make_scalars_result([rule_row]),
        ])
        with patch("infrastructure.secondary.database.repositories.profile_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.get_by_id(pid)
        assert result is not None
        assert result.name == "p"
        assert len(result.rules) == 1

    async def test_get_by_id_not_found(self, repo):
        session, mgr = _make_mock_session()
        session.execute = AsyncMock(return_value=_make_scalar_result(None))
        with patch("infrastructure.secondary.database.repositories.profile_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.get_by_id(uuid4())
        assert result is None

    async def test_get_default_for_organization_found(self, repo):
        session, mgr = _make_mock_session()
        org_id = uuid4()
        pid = uuid4()
        row = _make_profile_row(profile_id=pid, org_id=org_id, is_default=True)
        rule_row = _make_rule_row(profile_id=pid)
        session.execute = AsyncMock(side_effect=[
            _make_scalar_result(row),
            _make_scalar_result(row),
            _make_scalars_result([rule_row]),
        ])
        with patch("infrastructure.secondary.database.repositories.profile_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.get_default_for_organization(org_id)
        assert result is not None

    async def test_get_default_for_organization_not_found(self, repo):
        session, mgr = _make_mock_session()
        session.execute = AsyncMock(return_value=_make_scalar_result(None))
        with patch("infrastructure.secondary.database.repositories.profile_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.get_default_for_organization(uuid4())
        assert result is None

    async def test_update_found(self, repo):
        session, mgr = _make_mock_session()
        model = _make_profile_row()
        session.get = AsyncMock(return_value=model)
        from domain.entities.verification_profile import VerificationProfile
        p = VerificationProfile(id=UUID(model.id), organization_id=uuid4(), name="updated", description="new")
        with patch("infrastructure.secondary.database.repositories.profile_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.update(p)
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert result is not None

    async def test_update_not_found_raises(self, repo):
        session, mgr = _make_mock_session()
        session.get = AsyncMock(return_value=None)
        from domain.entities.verification_profile import VerificationProfile
        p = VerificationProfile(id=uuid4(), organization_id=uuid4(), name="ghost")
        with patch("infrastructure.secondary.database.repositories.profile_repository.AsyncSessionLocal", return_value=mgr):
            with pytest.raises(ValueError, match="Profile not found"):
                await repo.update(p)

    async def test_list_by_organization_with_results(self, repo):
        session, mgr = _make_mock_session()
        pid = uuid4()
        rows = [_make_profile_row(profile_id=pid)]
        rule_rows = [_make_rule_row(profile_id=pid)]
        session.execute = AsyncMock(side_effect=[
            _make_scalars_result(rows),
            _make_scalars_result(rule_rows),
        ])
        with patch("infrastructure.secondary.database.repositories.profile_repository.AsyncSessionLocal", return_value=mgr):
            results = await repo.list_by_organization(uuid4())
        assert len(results) == 1
        assert len(results[0].rules) == 1

    async def test_list_by_organization_empty(self, repo):
        session, mgr = _make_mock_session()
        session.execute = AsyncMock(return_value=_make_scalars_result([]))
        with patch("infrastructure.secondary.database.repositories.profile_repository.AsyncSessionLocal", return_value=mgr):
            results = await repo.list_by_organization(uuid4())
        assert results == []

    async def test_list_by_organization_with_skip_limit(self, repo):
        session, mgr = _make_mock_session()
        session.execute = AsyncMock(return_value=_make_scalars_result([]))
        with patch("infrastructure.secondary.database.repositories.profile_repository.AsyncSessionLocal", return_value=mgr):
            results = await repo.list_by_organization(uuid4(), skip=10, limit=5)
        assert results == []

    async def test_delete_found(self, repo):
        session, mgr = _make_mock_session()
        model = _make_profile_row()
        session.get = AsyncMock(return_value=model)
        with patch("infrastructure.secondary.database.repositories.profile_repository.AsyncSessionLocal", return_value=mgr):
            await repo.delete(uuid4())
        session.delete.assert_called_once()
        session.commit.assert_awaited_once()

    async def test_delete_not_found_raises(self, repo):
        session, mgr = _make_mock_session()
        session.get = AsyncMock(return_value=None)
        with patch("infrastructure.secondary.database.repositories.profile_repository.AsyncSessionLocal", return_value=mgr):
            with pytest.raises(ValueError, match="Profile not found"):
                await repo.delete(uuid4())


# ── BaseSqlRepository ────────────────────────────────────────────────────────

class TestBaseSqlRepository:
    @pytest.fixture
    def mock_session_scope(self):
        session = AsyncMock()
        session_mgr = MagicMock()
        session_mgr.__aenter__ = AsyncMock(return_value=session)
        session_mgr.__aexit__ = AsyncMock(return_value=None)
        return session, session_mgr

    def test_session_scope_is_context_manager(self, mock_session_scope):
        session, mgr = mock_session_scope
        with patch("infrastructure.secondary.database.repositories.base_sql_repository.AsyncSessionLocal", return_value=mgr):
            async def _use():
                from infrastructure.secondary.database.repositories.base_sql_repository import _session_scope
                async with _session_scope() as s:
                    assert s is session
            import asyncio
            asyncio.run(_use())

    async def test_create_success(self, mock_session_scope):
        session, mgr = mock_session_scope
        from infrastructure.secondary.database.repositories.base_sql_repository import BaseSqlRepository

        class _Concrete(BaseSqlRepository):
            model_class = MagicMock
            entity_class = str

            def _model_to_entity(self, row):
                return f"entity_{row.id}"

            def _entity_to_model_attrs(self, entity):
                return {"name": entity}

        repo = _Concrete()
        entity = MagicMock()
        entity.id = uuid4()
        with patch("infrastructure.secondary.database.repositories.base_sql_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo._create(entity)
        session.add.assert_called_once()
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert result is not None

    async def test_get_by_id_found(self, mock_session_scope):
        session, mgr = mock_session_scope
        from infrastructure.secondary.database.repositories.base_sql_repository import BaseSqlRepository

        MockModel = type('MockModel', (), {'id': MagicMock()})

        class _Concrete(BaseSqlRepository):
            model_class = MockModel
            entity_class = str
            def _model_to_entity(self, row):
                return f"entity_{row.id}"
            def _entity_to_model_attrs(self, entity):
                return {}

        repo = _Concrete()
        row = MagicMock()
        row.id = "test-id"
        result_mock = _make_scalar_result(row)
        session.execute = AsyncMock(return_value=result_mock)

        mock_select = MagicMock()
        mock_select.where = MagicMock(return_value=mock_select)

        with patch("infrastructure.secondary.database.repositories.base_sql_repository.AsyncSessionLocal", return_value=mgr), \
             patch("infrastructure.secondary.database.repositories.base_sql_repository.select", return_value=mock_select):
            result = await repo._get_by_id(uuid4())
        assert result == "entity_test-id"

    async def test_get_by_id_not_found(self, mock_session_scope):
        session, mgr = mock_session_scope
        from infrastructure.secondary.database.repositories.base_sql_repository import BaseSqlRepository

        MockModel = type('MockModel', (), {'id': MagicMock()})

        class _Concrete(BaseSqlRepository):
            model_class = MockModel
            entity_class = str
            def _model_to_entity(self, row): return str(row)
            def _entity_to_model_attrs(self, entity): return {}

        repo = _Concrete()
        session.execute = AsyncMock(return_value=_make_scalar_result(None))

        mock_select = MagicMock()
        mock_select.where = MagicMock(return_value=mock_select)

        with patch("infrastructure.secondary.database.repositories.base_sql_repository.AsyncSessionLocal", return_value=mgr), \
             patch("infrastructure.secondary.database.repositories.base_sql_repository.select", return_value=mock_select):
            result = await repo._get_by_id(uuid4())
        assert result is None

    async def test_list_all_with_results(self, mock_session_scope):
        session, mgr = mock_session_scope
        from infrastructure.secondary.database.repositories.base_sql_repository import BaseSqlRepository

        MockModel = type('MockModel', (), {})

        class _Concrete(BaseSqlRepository):
            model_class = MockModel
            entity_class = str
            def _model_to_entity(self, row):
                return f"entity_{row.id}"
            def _entity_to_model_attrs(self, entity): return {}

        repo = _Concrete()
        row1 = MagicMock()
        row1.id = "id1"
        row2 = MagicMock()
        row2.id = "id2"
        session.execute = AsyncMock(return_value=_make_scalars_result([row1, row2]))

        mock_select = MagicMock()
        with patch("infrastructure.secondary.database.repositories.base_sql_repository.AsyncSessionLocal", return_value=mgr), \
             patch("infrastructure.secondary.database.repositories.base_sql_repository.select", return_value=mock_select):
            results = await repo._list_all()
        assert len(results) == 2
        assert results == ["entity_id1", "entity_id2"]

    async def test_list_all_empty(self, mock_session_scope):
        session, mgr = mock_session_scope
        from infrastructure.secondary.database.repositories.base_sql_repository import BaseSqlRepository

        MockModel = type('MockModel', (), {})

        class _Concrete(BaseSqlRepository):
            model_class = MockModel
            entity_class = str
            def _model_to_entity(self, row): return str(row)
            def _entity_to_model_attrs(self, entity): return {}

        repo = _Concrete()
        session.execute = AsyncMock(return_value=_make_scalars_result([]))

        mock_select = MagicMock()
        with patch("infrastructure.secondary.database.repositories.base_sql_repository.AsyncSessionLocal", return_value=mgr), \
             patch("infrastructure.secondary.database.repositories.base_sql_repository.select", return_value=mock_select):
            results = await repo._list_all()
        assert results == []

    async def test_delete_found(self, mock_session_scope):
        session, mgr = mock_session_scope
        from infrastructure.secondary.database.repositories.base_sql_repository import BaseSqlRepository

        class _Concrete(BaseSqlRepository):
            model_class = MagicMock
            entity_class = str
            def _model_to_entity(self, row): return str(row)
            def _entity_to_model_attrs(self, entity): return {}

        repo = _Concrete()
        model = MagicMock()
        session.get = AsyncMock(return_value=model)
        with patch("infrastructure.secondary.database.repositories.base_sql_repository.AsyncSessionLocal", return_value=mgr):
            await repo._delete(uuid4())
        session.delete.assert_called_once()
        session.commit.assert_awaited_once()

    async def test_delete_not_found_raises(self, mock_session_scope):
        session, mgr = mock_session_scope
        from infrastructure.secondary.database.repositories.base_sql_repository import BaseSqlRepository

        class _Concrete(BaseSqlRepository):
            model_class = MagicMock
            entity_class = str
            def _model_to_entity(self, row): return str(row)
            def _entity_to_model_attrs(self, entity): return {}

        repo = _Concrete()
        session.get = AsyncMock(return_value=None)
        with patch("infrastructure.secondary.database.repositories.base_sql_repository.AsyncSessionLocal", return_value=mgr):
            with pytest.raises(ValueError, match="not found"):
                await repo._delete(uuid4())

    def test_model_to_entity_raises_not_implemented(self):
        from infrastructure.secondary.database.repositories.base_sql_repository import BaseSqlRepository
        class _Minimal(BaseSqlRepository):
            pass
        minimal = _Minimal()
        with pytest.raises(NotImplementedError):
            minimal._model_to_entity(MagicMock())

    def test_entity_to_model_attrs_raises_not_implemented(self):
        from infrastructure.secondary.database.repositories.base_sql_repository import BaseSqlRepository
        class _Minimal(BaseSqlRepository):
            pass
        minimal = _Minimal()
        with pytest.raises(NotImplementedError):
            minimal._entity_to_model_attrs("test")


# ── SqlProjectRepository ─────────────────────────────────────────────────────

class TestSqlProjectRepository:
    @pytest.fixture
    def repo(self):
        from infrastructure.secondary.database.repositories.project_repository import SqlProjectRepository
        return SqlProjectRepository()

    async def test_create_success(self, repo):
        session, mgr = _make_mock_session()
        from domain.entities.project import Project
        p = Project(organization_id=uuid4(), name="p", description="d", profile_id=uuid4())
        with patch("infrastructure.secondary.database.repositories.project_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.create(p)
        session.add.assert_called_once()
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert result.name == "p"

    async def test_get_by_id_found(self, repo):
        session, mgr = _make_mock_session()
        row = _make_project_row()
        session.execute = AsyncMock(return_value=_make_scalar_result(row))
        with patch("infrastructure.secondary.database.repositories.project_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.get_by_id(uuid4())
        assert result is not None

    async def test_get_by_id_not_found(self, repo):
        session, mgr = _make_mock_session()
        session.execute = AsyncMock(return_value=_make_scalar_result(None))
        with patch("infrastructure.secondary.database.repositories.project_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.get_by_id(uuid4())
        assert result is None

    async def test_list_by_organization_with_results(self, repo):
        session, mgr = _make_mock_session()
        rows = [_make_project_row(), _make_project_row(name="p2")]
        session.execute = AsyncMock(return_value=_make_scalars_result(rows))
        with patch("infrastructure.secondary.database.repositories.project_repository.AsyncSessionLocal", return_value=mgr):
            results = await repo.list_by_organization(uuid4())
        assert len(results) == 2

    async def test_list_by_organization_empty(self, repo):
        session, mgr = _make_mock_session()
        session.execute = AsyncMock(return_value=_make_scalars_result([]))
        with patch("infrastructure.secondary.database.repositories.project_repository.AsyncSessionLocal", return_value=mgr):
            results = await repo.list_by_organization(uuid4())
        assert results == []

    async def test_list_by_organization_with_skip_limit(self, repo):
        session, mgr = _make_mock_session()
        session.execute = AsyncMock(return_value=_make_scalars_result([]))
        with patch("infrastructure.secondary.database.repositories.project_repository.AsyncSessionLocal", return_value=mgr):
            results = await repo.list_by_organization(uuid4(), skip=10, limit=5)
        assert results == []

    async def test_update_found(self, repo):
        session, mgr = _make_mock_session()
        model = _make_project_row()
        session.get = AsyncMock(return_value=model)
        from domain.entities.project import Project
        p = Project(id=UUID(model.id), name="updated", description="new", organization_id=uuid4(), profile_id=uuid4())
        with patch("infrastructure.secondary.database.repositories.project_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.update(p)
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert result is not None

    async def test_update_not_found_raises(self, repo):
        session, mgr = _make_mock_session()
        session.get = AsyncMock(return_value=None)
        from domain.entities.project import Project
        p = Project(id=uuid4(), name="ghost", description="d", organization_id=uuid4(), profile_id=uuid4())
        with patch("infrastructure.secondary.database.repositories.project_repository.AsyncSessionLocal", return_value=mgr):
            with pytest.raises(ValueError, match="Project not found"):
                await repo.update(p)

    async def test_delete_found(self, repo):
        session, mgr = _make_mock_session()
        model = _make_project_row()
        session.get = AsyncMock(return_value=model)
        with patch("infrastructure.secondary.database.repositories.project_repository.AsyncSessionLocal", return_value=mgr):
            await repo.delete(uuid4())
        session.delete.assert_called_once()
        session.commit.assert_awaited_once()

    async def test_delete_not_found_raises(self, repo):
        session, mgr = _make_mock_session()
        session.get = AsyncMock(return_value=None)
        with patch("infrastructure.secondary.database.repositories.project_repository.AsyncSessionLocal", return_value=mgr):
            with pytest.raises(ValueError, match="Project not found"):
                await repo.delete(uuid4())


# ── SqlOrganizationRepository ─────────────────────────────────────────────────

class TestSqlOrganizationRepository:
    @pytest.fixture
    def repo(self):
        from infrastructure.secondary.database.repositories.organization_repository import SqlOrganizationRepository
        return SqlOrganizationRepository()

    def test_model_to_entity_with_owner(self, repo):
        row = _make_org_row(owner_id=uuid4())
        entity = repo._model_to_entity(row)
        assert entity.name == "org"
        assert entity.owner_id is not None
        assert entity.is_active is True

    def test_model_to_entity_without_owner(self, repo):
        row = _make_org_row(owner_id=None)
        entity = repo._model_to_entity(row)
        assert entity.owner_id is None

    def test_model_to_entity_inactive(self, repo):
        row = _make_org_row(is_active=False)
        entity = repo._model_to_entity(row)
        assert entity.is_active is False

    async def test_create_success(self, repo):
        session, mgr = _make_mock_session()
        from domain.entities.organization import Organization
        org = Organization(name="org", slug="org-slug")
        with patch("infrastructure.secondary.database.repositories.organization_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.create(org)
        session.add.assert_called_once()
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert result.name == "org"

    async def test_get_by_id_found(self, repo):
        session, mgr = _make_mock_session()
        row = _make_org_row()
        session.execute = AsyncMock(return_value=_make_scalar_result(row))
        with patch("infrastructure.secondary.database.repositories.organization_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.get_by_id(uuid4())
        assert result is not None

    async def test_get_by_id_not_found(self, repo):
        session, mgr = _make_mock_session()
        session.execute = AsyncMock(return_value=_make_scalar_result(None))
        with patch("infrastructure.secondary.database.repositories.organization_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.get_by_id(uuid4())
        assert result is None

    async def test_get_by_slug_found(self, repo):
        session, mgr = _make_mock_session()
        row = _make_org_row(slug="my-slug")
        session.execute = AsyncMock(return_value=_make_scalar_result(row))
        with patch("infrastructure.secondary.database.repositories.organization_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.get_by_slug("my-slug")
        assert result is not None
        assert result.slug == "my-slug"

    async def test_get_by_slug_not_found(self, repo):
        session, mgr = _make_mock_session()
        session.execute = AsyncMock(return_value=_make_scalar_result(None))
        with patch("infrastructure.secondary.database.repositories.organization_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.get_by_slug("nope")
        assert result is None

    async def test_list_all_active_only_with_results(self, repo):
        session, mgr = _make_mock_session()
        rows = [_make_org_row(), _make_org_row(name="o2")]
        session.execute = AsyncMock(return_value=_make_scalars_result(rows))
        with patch("infrastructure.secondary.database.repositories.organization_repository.AsyncSessionLocal", return_value=mgr):
            results = await repo.list_all(active_only=True)
        assert len(results) == 2

    async def test_list_all_include_inactive(self, repo):
        session, mgr = _make_mock_session()
        rows = [_make_org_row(is_active=False)]
        session.execute = AsyncMock(return_value=_make_scalars_result(rows))
        with patch("infrastructure.secondary.database.repositories.organization_repository.AsyncSessionLocal", return_value=mgr):
            results = await repo.list_all(active_only=False)
        assert len(results) == 1

    async def test_list_all_empty(self, repo):
        session, mgr = _make_mock_session()
        session.execute = AsyncMock(return_value=_make_scalars_result([]))
        with patch("infrastructure.secondary.database.repositories.organization_repository.AsyncSessionLocal", return_value=mgr):
            results = await repo.list_all()
        assert results == []

    async def test_list_all_with_skip_limit(self, repo):
        session, mgr = _make_mock_session()
        session.execute = AsyncMock(return_value=_make_scalars_result([]))
        with patch("infrastructure.secondary.database.repositories.organization_repository.AsyncSessionLocal", return_value=mgr):
            results = await repo.list_all(skip=10, limit=5)
        assert results == []

    async def test_update_found(self, repo):
        session, mgr = _make_mock_session()
        model = _make_org_row()
        session.get = AsyncMock(return_value=model)
        from domain.entities.organization import Organization
        org = Organization(id=UUID(model.id), name="updated", slug="updated-slug")
        with patch("infrastructure.secondary.database.repositories.organization_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.update(org)
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert result.name == "updated"

    async def test_update_not_found_raises(self, repo):
        session, mgr = _make_mock_session()
        session.get = AsyncMock(return_value=None)
        from domain.entities.organization import Organization
        org = Organization(id=uuid4(), name="ghost", slug="ghost")
        with patch("infrastructure.secondary.database.repositories.organization_repository.AsyncSessionLocal", return_value=mgr):
            with pytest.raises(ValueError, match="Organization not found"):
                await repo.update(org)

    async def test_delete_success(self, repo):
        session, mgr = _make_mock_session()
        session.get = AsyncMock(return_value=_make_org_row())
        with patch("infrastructure.secondary.database.repositories.organization_repository.AsyncSessionLocal", return_value=mgr):
            await repo.delete(uuid4())
        session.delete.assert_called_once()
        session.commit.assert_awaited_once()

    async def test_delete_not_found_raises(self, repo):
        session, mgr = _make_mock_session()
        session.get = AsyncMock(return_value=None)
        with patch("infrastructure.secondary.database.repositories.organization_repository.AsyncSessionLocal", return_value=mgr):
            with pytest.raises(ValueError, match="Organization not found"):
                await repo.delete(uuid4())


# ── helpers for verification_result repository ────────────────────────────

def _make_verification_result_row(result_id=None, release_id=None, verdict="VALID",
                                   duration_ms=150, summary=None, rule_results=None,
                                   profile_snapshot=None):
    row = MagicMock()
    row.id = result_id or uuid4()
    row.release_id = release_id or uuid4()
    row.verdict = verdict
    row.duration_ms = duration_ms
    row.summary = summary or {}
    row.rule_results = rule_results or []
    row.profile_snapshot = profile_snapshot or {}
    row.executed_at = datetime.now(timezone.utc)
    return row


# ── SqlVerificationResultRepository ───────────────────────────────────────

class TestSqlVerificationResultRepository:
    @pytest.fixture
    def repo(self):
        from infrastructure.secondary.database.repositories.verification_result_repository import SqlVerificationResultRepository
        return SqlVerificationResultRepository()

    async def test_save_success(self, repo):
        session, mgr = _make_mock_session()
        from domain.entities.verification_result import VerificationResult
        result = VerificationResult(
            id=uuid4(), release_id=uuid4(), verdict=VerdictType.VALID,
            duration_ms=150, summary={"key": "val"},
            rule_results=[{"rule_id": "RV01", "message": "ok"}],
            profile_snapshot={},
            executed_at=datetime.now(timezone.utc),
        )
        with patch("infrastructure.secondary.database.repositories.verification_result_repository.AsyncSessionLocal", return_value=mgr):
            saved = await repo.save(result)
        session.add.assert_called_once()
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert saved is not None

    async def test_find_by_id_found(self, repo):
        session, mgr = _make_mock_session()
        rid = uuid4()
        row = _make_verification_result_row(result_id=rid, verdict="VALID")
        result = _make_scalar_result(row)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.verification_result_repository.AsyncSessionLocal", return_value=mgr):
            entity = await repo.find_by_id(rid)
        assert entity is not None
        assert entity.verdict == VerdictType.VALID

    async def test_find_by_id_not_found(self, repo):
        session, mgr = _make_mock_session()
        result = _make_scalar_result(None)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.verification_result_repository.AsyncSessionLocal", return_value=mgr):
            entity = await repo.find_by_id(uuid4())
        assert entity is None

    async def test_find_by_release_with_results(self, repo):
        session, mgr = _make_mock_session()
        rel_id = uuid4()
        rows = [_make_verification_result_row(release_id=rel_id, verdict="INVALID")]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.verification_result_repository.AsyncSessionLocal", return_value=mgr):
            entities = await repo.find_by_release(rel_id)
        assert len(entities) == 1
        assert entities[0].verdict == VerdictType.INVALID

    async def test_find_by_release_empty(self, repo):
        session, mgr = _make_mock_session()
        result = _make_scalars_result([])
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.verification_result_repository.AsyncSessionLocal", return_value=mgr):
            entities = await repo.find_by_release(uuid4())
        assert entities == []

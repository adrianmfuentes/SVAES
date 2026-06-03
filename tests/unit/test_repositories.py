"""
Branch-coverage tests for SQL repository implementations with most missed lines.
Uses AsyncMock to simulate SQLAlchemy async sessions.
"""

import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from uuid import uuid4, UUID
from datetime import datetime, timezone
from domain.entities.access_request import AccessRequest
from domain.enums import AccessRequestStatus

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api", "src"))

pytestmark = pytest.mark.unit


# ── helpers: create a fake async session with context manager interface ──────

def _make_mock_session():
    """Return an (AsyncMock, context manager factory) that simulates SQLAlchemy session."""
    session = AsyncMock()
    session_mgr = MagicMock()
    session_mgr.__aenter__ = AsyncMock(return_value=session)
    session_mgr.__aexit__ = AsyncMock(return_value=None)
    return session, session_mgr


def _make_scalar_result(row):
    """Simulate result.scalar_one_or_none() returning a row."""
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=row)
    return result


_SENTINEL = object()


def _make_scalars_result(rows):
    """Simulate result.scalars().all() returning rows."""
    scalars = MagicMock()
    scalars.all = MagicMock(return_value=rows)
    result = MagicMock()
    result.scalars = MagicMock(return_value=scalars)
    return result


def _make_release_row(release_id=None, name="v1.0", version="1.0.0",
                      project_id=None, status="BORRADOR", profile_id=_SENTINEL):
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


# ── SqlReleaseRepository ─────────────────────────────────────────────────────

class TestSqlReleaseRepository:
    @pytest.fixture
    def repo(self):
        from infrastructure.secondary.database.repositories.release_repository import SqlReleaseRepository
        return SqlReleaseRepository()

    # -- _release_from_row ---------------------------------------------------

    def test_release_from_row_with_profile_id(self, repo):
        """Branch: _release_from_row with profile_id not None → maps correctly"""
        row = _make_release_row(profile_id=uuid4())
        r = repo._release_from_row(row)
        assert r.name == "v1.0"
        assert r.version == "1.0.0"
        assert r.profile_id is not None
        assert r.status.value == "BORRADOR"

    def test_release_from_row_without_profile_id(self, repo):
        """Branch: _release_from_row with profile_id None → maps to None"""
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
        """Branch: get_by_id finds release + has artifacts → returns Release with artifacts"""
        session, mgr = _make_mock_session()
        rel_row = _make_release_row()
        art_row = _make_artifact_row()
        rel_result = _make_scalar_result(rel_row)
        art_scalars = MagicMock()
        art_scalars.all = MagicMock(return_value=[art_row])
        art_result = MagicMock()
        art_result.scalars = MagicMock(return_value=art_scalars)

        session.execute = AsyncMock(side_effect=[rel_result, art_result])
        with patch("infrastructure.secondary.database.repositories.release_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.get_by_id(uuid4())
        assert result is not None
        assert result.name == "v1.0"
        assert len(result.artifacts) == 1

    async def test_get_by_id_not_found(self, repo):
        """Branch: get_by_id returns None → returns None"""
        session, mgr = _make_mock_session()
        rel_result = _make_scalar_result(None)
        session.execute = AsyncMock(return_value=rel_result)
        with patch("infrastructure.secondary.database.repositories.release_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.get_by_id(uuid4())
        assert result is None

    # -- list_by_project -----------------------------------------------------

    async def test_list_by_project_returns_list(self, repo):
        """Branch: list_by_project with results → returns list of Releases"""
        session, mgr = _make_mock_session()
        rows = [_make_release_row()]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.release_repository.AsyncSessionLocal", return_value=mgr):
            releases = await repo.list_by_project(uuid4())
        assert len(releases) == 1
        assert releases[0].name == "v1.0"

    async def test_list_by_project_empty(self, repo):
        """Branch: list_by_project no results → returns empty list"""
        session, mgr = _make_mock_session()
        result = _make_scalars_result([])
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.release_repository.AsyncSessionLocal", return_value=mgr):
            releases = await repo.list_by_project(uuid4())
        assert releases == []

    # -- list_by_organization ------------------------------------------------

    async def test_list_by_organization_with_org_id(self, repo):
        """Branch: list_by_organization with organization_id → filters by org"""
        session, mgr = _make_mock_session()
        rows = [_make_release_row()]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.release_repository.AsyncSessionLocal", return_value=mgr):
            releases = await repo.list_by_organization(uuid4())
        assert len(releases) == 1

    async def test_list_by_organization_without_org_id(self, repo):
        """Branch: list_by_organization with organization_id=None → no org filter"""
        session, mgr = _make_mock_session()
        rows = [_make_release_row()]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.release_repository.AsyncSessionLocal", return_value=mgr):
            releases = await repo.list_by_organization(None)
        assert len(releases) == 1

    # -- update --------------------------------------------------------------

    async def test_update_found(self, repo):
        """Branch: update finds release → updates fields, returns Release"""
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
        """Branch: update does not find release → raises EntityNotFoundError"""
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
            with pytest.raises(EntityNotFoundError, match="Release no encontrado"):
                await repo.update(release)

    # -- update_status -------------------------------------------------------

    async def test_update_status_found(self, repo):
        """Branch: update_status finds release → updates status, returns Release"""
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
        """Branch: update_status does not find release → returns None"""
        session, mgr = _make_mock_session()
        result = _make_scalar_result(None)
        session.execute = AsyncMock(return_value=result)
        from domain.enums import ReleaseStatus
        with patch("infrastructure.secondary.database.repositories.release_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.update_status(uuid4(), ReleaseStatus.VALIDA)
        assert result is None

    # -- delete --------------------------------------------------------------

    async def test_delete_found(self, repo):
        """Branch: delete finds release → deletes and commits"""
        session, mgr = _make_mock_session()
        rel_row = _make_release_row()
        result = _make_scalar_result(rel_row)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.release_repository.AsyncSessionLocal", return_value=mgr):
            await repo.delete(uuid4())
        session.delete.assert_awaited_once_with(rel_row)
        session.commit.assert_awaited_once()

    async def test_delete_not_found_raises(self, repo):
        """Branch: delete does not find release → raises EntityNotFoundError"""
        session, mgr = _make_mock_session()
        result = _make_scalar_result(None)
        session.execute = AsyncMock(return_value=result)
        from domain.exceptions import EntityNotFoundError
        with patch("infrastructure.secondary.database.repositories.release_repository.AsyncSessionLocal", return_value=mgr):
            with pytest.raises(EntityNotFoundError, match="Release no encontrado"):
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
        """Branch: _channel_model_to_entity with config_data None → empty dict"""
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
        """Branch: list_channels with results → returns list"""
        session, mgr = _make_mock_session()
        rows = [_make_channel_row()]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.notification_repository._session_scope", return_value=mgr):
            channels = await repo.list_channels(uuid4())
        assert len(channels) == 1

    async def test_list_channels_empty(self, repo):
        """Branch: list_channels no results → empty list"""
        session, mgr = _make_mock_session()
        result = _make_scalars_result([])
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.notification_repository._session_scope", return_value=mgr):
            channels = await repo.list_channels(uuid4())
        assert channels == []

    # -- get_channel_by_id ---------------------------------------------------

    async def test_get_channel_by_id_found(self, repo):
        """Branch: get_channel_by_id finds → returns entity"""
        session, mgr = _make_mock_session()
        result = _make_scalar_result(_make_channel_row())
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.notification_repository._session_scope", return_value=mgr):
            channel = await repo.get_channel_by_id(uuid4())
        assert channel is not None

    async def test_get_channel_by_id_not_found(self, repo):
        """Branch: get_channel_by_id None → returns None"""
        session, mgr = _make_mock_session()
        result = _make_scalar_result(None)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.notification_repository._session_scope", return_value=mgr):
            channel = await repo.get_channel_by_id(uuid4())
        assert channel is None

    # -- update_channel ------------------------------------------------------

    async def test_update_channel_found(self, repo):
        """Branch: update_channel finds model → updates and returns"""
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
        """Branch: update_channel model not found → ValueError"""
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
        """Branch: delete_channel finds → deletes"""
        session, mgr = _make_mock_session()
        model = _make_channel_row()
        session.get = AsyncMock(return_value=model)
        with patch("infrastructure.secondary.database.repositories.notification_repository._session_scope", return_value=mgr):
            await repo.delete_channel(uuid4())
        session.delete.assert_awaited_once()
        session.commit.assert_awaited_once()

    async def test_delete_channel_not_found_raises(self, repo):
        """Branch: delete_channel not found → ValueError"""
        session, mgr = _make_mock_session()
        session.get = AsyncMock(return_value=None)
        with patch("infrastructure.secondary.database.repositories.notification_repository._session_scope", return_value=mgr):
            with pytest.raises(ValueError, match="not found"):
                await repo.delete_channel(uuid4())

    # -- list_subscriptions --------------------------------------------------

    async def test_list_subscriptions_returns_list(self, repo):
        """Branch: list_subscriptions with results → returns list"""
        session, mgr = _make_mock_session()
        rows = [_make_subscription_row()]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.notification_repository._session_scope", return_value=mgr):
            subs = await repo.list_subscriptions(uuid4())
        assert len(subs) == 1

    # -- get_subscription ----------------------------------------------------

    async def test_get_subscription_found(self, repo):
        """Branch: get_subscription finds → returns entity"""
        session, mgr = _make_mock_session()
        result = _make_scalar_result(_make_subscription_row())
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.notification_repository._session_scope", return_value=mgr):
            sub = await repo.get_subscription(uuid4(), "release_validated")
        assert sub is not None

    async def test_get_subscription_not_found(self, repo):
        """Branch: get_subscription None → returns None"""
        session, mgr = _make_mock_session()
        result = _make_scalar_result(None)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.notification_repository._session_scope", return_value=mgr):
            sub = await repo.get_subscription(uuid4(), "release_validated")
        assert sub is None

    # -- upsert_subscription -------------------------------------------------

    async def test_upsert_subscription_existing_update(self, repo):
        """Branch: upsert finds existing → updates enabled and returns"""
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
        """Branch: upsert does not find existing → inserts new"""
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
        """Branch: delete_subscription finds → deletes"""
        session, mgr = _make_mock_session()
        model = _make_subscription_row()
        result = _make_scalar_result(model)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.notification_repository._session_scope", return_value=mgr):
            await repo.delete_subscription(uuid4(), "release_validated")
        session.delete.assert_awaited_once()
        session.commit.assert_awaited_once()

    async def test_delete_subscription_not_found(self, repo):
        """Branch: delete_subscription not found → no-op (returns early)"""
        session, mgr = _make_mock_session()
        result = _make_scalar_result(None)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.notification_repository._session_scope", return_value=mgr):
            await repo.delete_subscription(uuid4(), "release_validated")
        # No delete or commit called
        session.delete.assert_not_awaited()


# ── SqlUserRepository ────────────────────────────────────────────────────────

class TestSqlUserRepository:
    @pytest.fixture
    def repo(self):
        from infrastructure.secondary.database.repositories.user_repository import SqlUserRepository
        return SqlUserRepository()

    # -- _model_to_entity ----------------------------------------------------

    def test_model_to_entity_with_org_id(self, repo):
        """Branch: _model_to_entity with organization_id → maps to organization_ids"""
        row = _make_user_row(organization_id=uuid4())
        user = repo._model_to_entity(row)
        assert user.email == "test@test.com"
        assert len(user.organization_ids) == 1

    def test_model_to_entity_without_org_id(self, repo):
        """Branch: _model_to_entity with organization_id=None → empty list"""
        row = _make_user_row(organization_id=None)
        user = repo._model_to_entity(row)
        assert user.organization_ids == []

    def test_model_to_entity_totp_disabled(self, repo):
        """Branch: _model_to_entity with totp_enabled=None → defaults to False"""
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
        """Branch: get_by_id finds user → returns User"""
        session, mgr = _make_mock_session()
        row = _make_user_row()
        result = _make_scalar_result(row)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.user_repository.AsyncSessionLocal", return_value=mgr):
            user = await repo.get_by_id(uuid4())
        assert user is not None
        assert user.email == "test@test.com"

    async def test_get_by_id_not_found(self, repo):
        """Branch: get_by_id returns None → returns None"""
        session, mgr = _make_mock_session()
        result = _make_scalar_result(None)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.user_repository.AsyncSessionLocal", return_value=mgr):
            user = await repo.get_by_id(uuid4())
        assert user is None

    # -- get_by_email --------------------------------------------------------

    async def test_get_by_email_found(self, repo):
        """Branch: get_by_email finds user → returns User"""
        session, mgr = _make_mock_session()
        row = _make_user_row(email="found@test.com")
        result = _make_scalar_result(row)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.user_repository.AsyncSessionLocal", return_value=mgr):
            user = await repo.get_by_email("found@test.com")
        assert user is not None
        assert user.email == "found@test.com"

    async def test_get_by_email_not_found(self, repo):
        """Branch: get_by_email returns None → returns None"""
        session, mgr = _make_mock_session()
        result = _make_scalar_result(None)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.user_repository.AsyncSessionLocal", return_value=mgr):
            user = await repo.get_by_email("no@test.com")
        assert user is None

    # -- list_all ------------------------------------------------------------

    async def test_list_all_with_filters(self, repo):
        """Branch: list_all with organization_id + active_only → filtered"""
        session, mgr = _make_mock_session()
        rows = [_make_user_row()]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.user_repository.AsyncSessionLocal", return_value=mgr):
            users = await repo.list_all(organization_id=uuid4(), active_only=True)
        assert len(users) == 1

    async def test_list_all_no_org_id(self, repo):
        """Branch: list_all with organization_id=None → no org filter"""
        session, mgr = _make_mock_session()
        rows = [_make_user_row()]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.user_repository.AsyncSessionLocal", return_value=mgr):
            users = await repo.list_all(organization_id=None, active_only=False)
        assert len(users) == 1

    async def test_list_all_not_active_only(self, repo):
        """Branch: list_all with active_only=False → no active filter"""
        session, mgr = _make_mock_session()
        rows = [_make_user_row(is_active=False), _make_user_row(is_active=True)]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.user_repository.AsyncSessionLocal", return_value=mgr):
            users = await repo.list_all(active_only=False)
        assert len(users) == 2

    # -- update --------------------------------------------------------------

    async def test_update_found(self, repo):
        """Branch: update finds user → updates fields, returns User"""
        session, mgr = _make_mock_session()
        model = _make_user_row()
        session.get = AsyncMock(return_value=model)
        from domain.entities.user import User
        from domain.enums import UserRole
        user = User(
            id=uuid4(), email="updated@test.com", hashed_password="newhash", # NOSONAR
            display_name="Updated", role=UserRole.U1, is_active=False,
        )
        with patch("infrastructure.secondary.database.repositories.user_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.update(user)
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert result is not None

    async def test_update_not_found_raises(self, repo):
        """Branch: update not found → ValueError"""
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
        """Branch: get_by_activation_token finds → returns User"""
        session, mgr = _make_mock_session()
        row = _make_user_row(activation_token="token123")
        result = _make_scalar_result(row)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.user_repository.AsyncSessionLocal", return_value=mgr):
            user = await repo.get_by_activation_token("token123")
        assert user is not None

    async def test_get_by_activation_token_not_found(self, repo):
        """Branch: get_by_activation_token None → returns None"""
        session, mgr = _make_mock_session()
        result = _make_scalar_result(None)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.user_repository.AsyncSessionLocal", return_value=mgr):
            user = await repo.get_by_activation_token("no-token")
        assert user is None

    # -- delete --------------------------------------------------------------

    async def test_delete_found(self, repo):
        """Branch: delete finds user → deletes"""
        session, mgr = _make_mock_session()
        model = _make_user_row()
        session.get = AsyncMock(return_value=model)
        with patch("infrastructure.secondary.database.repositories.user_repository.AsyncSessionLocal", return_value=mgr):
            await repo.delete(uuid4())
        session.delete.assert_awaited_once()
        session.commit.assert_awaited_once()

    async def test_delete_not_found_raises(self, repo):
        """Branch: delete not found → ValueError"""
        session, mgr = _make_mock_session()
        session.get = AsyncMock(return_value=None)
        with patch("infrastructure.secondary.database.repositories.user_repository.AsyncSessionLocal", return_value=mgr):
            with pytest.raises(ValueError, match="User not found"):
                await repo.delete(uuid4())


# ── helpers: access request mock row ──────────────────────────────────────────


from typing import Optional


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
        """Branch: get_by_id finds row → returns AccessRequest"""
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
        """Branch: get_by_id returns None → returns None"""
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
        """Branch: get_by_email finds row → returns AccessRequest"""
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
        """Branch: get_by_email returns None → returns None"""
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
        """Branch: list_by_status with results → returns list of AccessRequests"""
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
        """Branch: list_by_status no results → empty list"""
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
        """Branch: update finds row → updates fields, returns entity"""
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
        """Branch: update does not find row → raises ValueError"""
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

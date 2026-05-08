"""
Tests for SQLAlchemy repository adapters.

Uses mocked AsyncSession / Session to verify entity mapping and ORM delegation
without requiring a real database connection.
"""

import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from domain.entities.enums import (
    ReleaseStatus, ConnectorStatus, VerdictType, UserRole
)
from domain.entities.organization import Organization
from domain.entities.user import User
from domain.entities.project import Project
from domain.entities.release import Release
from domain.entities.connector_instance import ConnectorInstance
from domain.entities.verification_profile import VerificationProfile
from domain.entities.artifact import Artifact
from domain.entities.verification_result import VerificationResult

from infrastructure.database.repositories.organization_repository import SqlOrganizationRepository
from infrastructure.database.repositories.user_repository import SqlUserRepository
from infrastructure.database.repositories.project_repository import SqlProjectRepository
from infrastructure.database.repositories.release_repository import SqlReleaseRepository
from infrastructure.database.repositories.connector_repository import SqlConnectorRepository
from infrastructure.database.repositories.profile_repository import SqlProfileRepository
from infrastructure.database.repositories.artifact_repository import SqlArtifactRepository
from infrastructure.database.repositories.verification_result_repository import SqlVerificationResultRepository


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime.now(timezone.utc)


def _async_session():
    """Returns a mocked AsyncSession with common methods pre-configured."""
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.get = AsyncMock(return_value=None)
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=mock_result)
    return session


def _sync_session():
    """Returns a mocked sync Session with common methods pre-configured."""
    session = MagicMock()
    session.add = MagicMock()
    session.flush = MagicMock()
    session.get = MagicMock(return_value=None)
    mock_result = MagicMock()
    mock_result.all.return_value = []
    session.query.return_value.filter_by.return_value.all.return_value = []
    session.query.return_value.filter_by.return_value.order_by.return_value.all.return_value = []
    return session


def _org_model(name="Acme", slug="acme", **kwargs):
    m = MagicMock()
    m.id = kwargs.get("id", uuid.uuid4())
    m.name = name
    m.slug = slug
    m.is_active = kwargs.get("is_active", True)
    m.created_at = _NOW
    m.updated_at = _NOW
    return m


def _user_model(email="user@test.com", **kwargs):
    m = MagicMock()
    m.id = kwargs.get("id", uuid.uuid4())
    m.email = email
    m.password_hash = "$2b$12$hashed" # NOSONAR
    m.created_at = _NOW
    m.updated_at = _NOW
    return m


def _project_model(name="MyProject", **kwargs):
    m = MagicMock()
    m.id = kwargs.get("id", uuid.uuid4())
    m.organization_id = kwargs.get("organization_id", uuid.uuid4())
    m.name = name
    m.description = kwargs.get("description", "")
    m.created_at = _NOW
    m.updated_at = _NOW
    return m


def _release_model(version="1.0.0", status="BORRADOR", **kwargs):
    m = MagicMock()
    m.id = kwargs.get("id", uuid.uuid4())
    m.project_id = kwargs.get("project_id", uuid.uuid4())
    m.profile_id = kwargs.get("profile_id", uuid.uuid4())
    m.version = version
    m.created_by = kwargs.get("created_by", uuid.uuid4())
    m.status = status
    m.description = kwargs.get("description", "")
    m.created_at = _NOW
    m.updated_at = _NOW
    return m


def _connector_model(connector_type="github", status="ACTIVO", **kwargs):
    m = MagicMock()
    m.id = kwargs.get("id", uuid.uuid4())
    m.organization_id = kwargs.get("organization_id", uuid.uuid4())
    m.connector_type = connector_type
    m.config_encrypted = b"encrypted_creds"
    m.status = status
    m.created_at = _NOW
    return m


def _profile_model(name="Default", **kwargs):
    m = MagicMock()
    m.id = kwargs.get("id", uuid.uuid4())
    m.organization_id = kwargs.get("organization_id", uuid.uuid4())
    m.name = name
    m.rules = []
    m.created_at = _NOW
    m.updated_at = _NOW
    return m


def _artifact_model(**kwargs):
    m = MagicMock()
    m.id = kwargs.get("id", uuid.uuid4())
    m.release_id = kwargs.get("release_id", uuid.uuid4())
    m.connector_instance_id = kwargs.get("connector_instance_id", uuid.uuid4())
    m.artifact_type = kwargs.get("artifact_type", "commit")
    m.external_ref = kwargs.get("external_ref", "abc123")
    m.metadata_ = kwargs.get("metadata_", {})
    m.created_at = _NOW
    return m


def _vr_model(**kwargs):
    m = MagicMock()
    m.id = kwargs.get("id", uuid.uuid4())
    m.release_id = kwargs.get("release_id", uuid.uuid4())
    m.verdict = kwargs.get("verdict", "VALID")
    m.rule_results = kwargs.get("rule_results", {})
    m.profile_snapshot = kwargs.get("profile_snapshot", {})
    m.executed_at = _NOW
    m.duration_ms = kwargs.get("duration_ms", 500)
    return m


# ---------------------------------------------------------------------------
# Organization repository
# ---------------------------------------------------------------------------

class TestSqlOrganizationRepository:
    async def test_create_calls_add_and_flush(self):
        session = _async_session()
        org = Organization(name="Test Org", slug="test-org")

        result = await SqlOrganizationRepository(session).create(org)

        assert result is org
        session.add.assert_called_once()
        session.flush.assert_called_once()

    async def test_get_by_id_found(self):
        model = _org_model("Found Org", "found-org")
        session = _async_session()
        session.get = AsyncMock(return_value=model)

        result = await SqlOrganizationRepository(session).get_by_id(model.id)

        assert result is not None
        assert result.name == "Found Org"
        assert result.slug == "found-org"
        assert result.is_active is True

    async def test_get_by_id_not_found_returns_none(self):
        session = _async_session()
        session.get = AsyncMock(return_value=None)

        result = await SqlOrganizationRepository(session).get_by_id(uuid.uuid4())

        assert result is None

    async def test_get_by_slug_found(self):
        model = _org_model("Slug Org", "slug-org")
        session = _async_session()
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = model
        session.execute = AsyncMock(return_value=result_mock)

        result = await SqlOrganizationRepository(session).get_by_slug("slug-org")

        assert result is not None
        assert result.slug == "slug-org"

    async def test_get_by_slug_not_found(self):
        session = _async_session()

        result = await SqlOrganizationRepository(session).get_by_slug("nonexistent")

        assert result is None

    async def test_list_all_active_only(self):
        models = [_org_model("A", "a"), _org_model("B", "b")]
        session = _async_session()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = models
        session.execute = AsyncMock(return_value=result_mock)

        results = await SqlOrganizationRepository(session).list_all(active_only=True)

        assert len(results) == 2
        assert results[0].name == "A"

    async def test_list_all_empty(self):
        session = _async_session()

        results = await SqlOrganizationRepository(session).list_all()

        assert results == []

    async def test_update_existing(self):
        model = _org_model("Old Name", "old-slug")
        session = _async_session()
        session.get = AsyncMock(return_value=model)

        org = Organization(id=model.id, name="New Name", slug="new-slug")
        result = await SqlOrganizationRepository(session).update(org)

        assert result is org
        assert model.name == "New Name"
        session.flush.assert_called_once()

    async def test_update_not_found_returns_entity(self):
        session = _async_session()
        session.get = AsyncMock(return_value=None)

        org = Organization(name="X", slug="x")
        result = await SqlOrganizationRepository(session).update(org)

        assert result is org


# ---------------------------------------------------------------------------
# User repository
# ---------------------------------------------------------------------------

class TestSqlUserRepository:
    async def test_create_calls_add_and_flush(self):
        session = _async_session()
        user = User(
            id=uuid.uuid4(),
            email="new@test.com",
            hashed_password="$2b$hash", # NOSONAR
            role=UserRole.OPERATOR,
            organization_id=uuid.uuid4(),
        )

        result = await SqlUserRepository(session).create(user)

        assert result is user
        session.add.assert_called_once()
        session.flush.assert_called_once()

    async def test_get_by_id_found(self):
        model = _user_model("found@test.com")
        session = _async_session()
        session.get = AsyncMock(return_value=model)

        result = await SqlUserRepository(session).get_by_id(model.id)

        assert result is not None
        assert result.email == "found@test.com"

    async def test_get_by_id_not_found(self):
        session = _async_session()

        result = await SqlUserRepository(session).get_by_id(uuid.uuid4())

        assert result is None

    async def test_get_by_email_found(self):
        model = _user_model("match@test.com")
        session = _async_session()
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = model
        session.execute = AsyncMock(return_value=result_mock)

        result = await SqlUserRepository(session).get_by_email("match@test.com")

        assert result is not None
        assert result.email == "match@test.com"

    async def test_get_by_email_not_found(self):
        session = _async_session()

        result = await SqlUserRepository(session).get_by_email("nobody@test.com")

        assert result is None

    async def test_list_all(self):
        models = [_user_model("a@test.com"), _user_model("b@test.com")]
        session = _async_session()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = models
        session.execute = AsyncMock(return_value=result_mock)

        results = await SqlUserRepository(session).list_all()

        assert len(results) == 2

    async def test_update_found(self):
        model = _user_model("old@test.com")
        session = _async_session()
        session.get = AsyncMock(return_value=model)

        user = User(
            id=model.id,
            email="new@test.com",
            hashed_password="$new$hash", # NOSONAR
            role=UserRole.ADMIN,
            organization_id=None,
        )
        result = await SqlUserRepository(session).update(user)

        assert result is user
        assert model.email == "new@test.com"


# ---------------------------------------------------------------------------
# Project repository
# ---------------------------------------------------------------------------

class TestSqlProjectRepository:
    async def test_create(self):
        session = _async_session()
        project = Project(
            organization_id=uuid.uuid4(), name="My Project", description="Desc"
        )

        result = await SqlProjectRepository(session).create(project)

        assert result is project
        session.add.assert_called_once()

    async def test_get_by_id_found(self):
        model = _project_model("Found Project")
        session = _async_session()
        session.get = AsyncMock(return_value=model)

        result = await SqlProjectRepository(session).get_by_id(model.id)

        assert result is not None
        assert result.name == "Found Project"

    async def test_get_by_id_not_found(self):
        session = _async_session()

        result = await SqlProjectRepository(session).get_by_id(uuid.uuid4())

        assert result is None

    async def test_list_by_organization(self):
        org_id = uuid.uuid4()
        models = [_project_model("P1", organization_id=org_id)]
        session = _async_session()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = models
        session.execute = AsyncMock(return_value=result_mock)

        results = await SqlProjectRepository(session).list_by_organization(org_id)

        assert len(results) == 1

    async def test_to_entity_uses_empty_description_fallback(self):
        model = _project_model("P", description=None)
        session = _async_session()
        session.get = AsyncMock(return_value=model)

        result = await SqlProjectRepository(session).get_by_id(model.id)

        assert result is not None
        assert result.description == ""


# ---------------------------------------------------------------------------
# Release repository
# ---------------------------------------------------------------------------

class TestSqlReleaseRepository:
    async def test_create(self):
        session = _async_session()
        release = Release(
            project_id=uuid.uuid4(),
            profile_id=uuid.uuid4(),
            version="1.0.0",
            created_by=uuid.uuid4(),
        )

        result = await SqlReleaseRepository(session).create(release)

        assert result is release
        session.add.assert_called_once()

    async def test_get_by_id_found(self):
        model = _release_model("2.0.0", "PENDIENTE")
        session = _async_session()
        session.get = AsyncMock(return_value=model)

        result = await SqlReleaseRepository(session).get_by_id(model.id)

        assert result is not None
        assert result.version == "2.0.0"
        assert result.status == ReleaseStatus.PENDIENTE

    async def test_get_by_id_not_found(self):
        session = _async_session()

        result = await SqlReleaseRepository(session).get_by_id(uuid.uuid4())

        assert result is None

    async def test_list_by_project(self):
        project_id = uuid.uuid4()
        models = [_release_model("1.0.0", "BORRADOR", project_id=project_id)]
        session = _async_session()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = models
        session.execute = AsyncMock(return_value=result_mock)

        results = await SqlReleaseRepository(session).list_by_project(project_id)

        assert len(results) == 1

    async def test_update_found(self):
        model = _release_model("1.0.0", "PENDIENTE")
        session = _async_session()
        session.get = AsyncMock(return_value=model)

        release = Release(
            id=model.id,
            project_id=model.project_id,
            profile_id=model.profile_id,
            version="1.0.0",
            created_by=model.created_by,
            status=ReleaseStatus.EN_VERIFICACION,
        )
        result = await SqlReleaseRepository(session).update(release)

        assert result is release
        assert model.status == "EN_VERIFICACION"

    async def test_update_not_found_returns_entity(self):
        session = _async_session()
        release = Release(
            project_id=uuid.uuid4(),
            profile_id=uuid.uuid4(),
            version="1.0.0",
            created_by=uuid.uuid4(),
        )

        result = await SqlReleaseRepository(session).update(release)

        assert result is release


# ---------------------------------------------------------------------------
# Connector repository
# ---------------------------------------------------------------------------

class TestSqlConnectorRepository:
    async def test_save_new_connector(self):
        session = _async_session()
        session.get = AsyncMock(return_value=None)

        connector = ConnectorInstance(
            id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            connector_type="github",
            encrypted_credentials=b"enc",
            status=ConnectorStatus.ACTIVO,
        )

        result = await SqlConnectorRepository(session).save(connector)

        assert result is connector
        session.add.assert_called_once()
        session.flush.assert_called_once()

    async def test_save_existing_connector_updates_fields(self):
        model = _connector_model("github", "INACTIVO")
        session = _async_session()
        session.get = AsyncMock(return_value=model)

        connector = ConnectorInstance(
            id=model.id,
            organization_id=model.organization_id,
            connector_type="github",
            encrypted_credentials=b"new_enc",
            status=ConnectorStatus.ACTIVO,
        )

        result = await SqlConnectorRepository(session).save(connector)

        assert result is connector
        assert model.config_encrypted == b"new_enc"
        assert model.status == "ACTIVO"

    async def test_get_by_id_found(self):
        model = _connector_model("jira", "ACTIVO")
        session = _async_session()
        session.get = AsyncMock(return_value=model)

        result = await SqlConnectorRepository(session).get_by_id(model.id)

        assert result is not None
        assert result.connector_type == "jira"
        assert result.status == ConnectorStatus.ACTIVO

    async def test_get_by_id_not_found(self):
        session = _async_session()

        result = await SqlConnectorRepository(session).get_by_id(uuid.uuid4())

        assert result is None

    async def test_list_by_organization_active(self):
        org_id = uuid.uuid4()
        models = [_connector_model("github", "ACTIVO", organization_id=org_id)]
        session = _async_session()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = models
        session.execute = AsyncMock(return_value=result_mock)

        results = await SqlConnectorRepository(session).list_by_organization(
            org_id, active_only=True
        )

        assert len(results) == 1

    async def test_list_by_organization_all(self):
        org_id = uuid.uuid4()
        models = [
            _connector_model("github", "ACTIVO", organization_id=org_id),
            _connector_model("jira", "INACTIVO", organization_id=org_id),
        ]
        session = _async_session()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = models
        session.execute = AsyncMock(return_value=result_mock)

        results = await SqlConnectorRepository(session).list_by_organization(
            org_id, active_only=False
        )

        assert len(results) == 2


# ---------------------------------------------------------------------------
# Profile repository
# ---------------------------------------------------------------------------

class TestSqlProfileRepository:
    async def test_create(self):
        session = _async_session()
        profile = VerificationProfile(
            id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            name="Default Profile",
        )

        result = await SqlProfileRepository(session).create(profile)

        assert result is profile
        session.add.assert_called_once()

    async def test_get_by_id_found(self):
        model = _profile_model("Found Profile")
        session = _async_session()
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = model
        session.execute = AsyncMock(return_value=result_mock)

        result = await SqlProfileRepository(session).get_by_id(model.id)

        assert result is not None
        assert result.name == "Found Profile"
        assert result.rules == []

    async def test_get_by_id_not_found(self):
        session = _async_session()

        result = await SqlProfileRepository(session).get_by_id(uuid.uuid4())

        assert result is None

    async def test_get_default_for_organization_found(self):
        model = _profile_model("Default")
        session = _async_session()
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = model
        session.execute = AsyncMock(return_value=result_mock)

        result = await SqlProfileRepository(session).get_default_for_organization(
            uuid.uuid4()
        )

        assert result is not None

    async def test_get_default_for_organization_not_found(self):
        session = _async_session()

        result = await SqlProfileRepository(session).get_default_for_organization(
            uuid.uuid4()
        )

        assert result is None


# ---------------------------------------------------------------------------
# Artifact repository (sync)
# ---------------------------------------------------------------------------

class TestSqlArtifactRepository:
    def test_save_new_artifact(self):
        session = _sync_session()
        session.get = MagicMock(return_value=None)

        artifact = Artifact(
            release_id=uuid.uuid4(),
            connector_instance_id=uuid.uuid4(),
            artifact_type="commit",
            external_ref="sha:abc123",
        )

        result = SqlArtifactRepository(session).save(artifact)

        assert result is artifact
        session.add.assert_called_once()
        session.flush.assert_called_once()

    def test_save_existing_artifact_updates_fields(self):
        model = _artifact_model()
        session = _sync_session()
        session.get = MagicMock(return_value=model)

        artifact = Artifact(
            id=model.id,
            release_id=model.release_id,
            connector_instance_id=model.connector_instance_id,
            artifact_type="task",
            external_ref="JIRA-99",
            metadata={"updated": True},
        )

        result = SqlArtifactRepository(session).save(artifact)

        assert result is artifact
        assert model.artifact_type == "task"
        assert model.external_ref == "JIRA-99"

    def test_find_by_id_found(self):
        model = _artifact_model(artifact_type="doc", external_ref="DOC-1")
        session = _sync_session()
        session.get = MagicMock(return_value=model)

        result = SqlArtifactRepository(session).find_by_id(model.id)

        assert result is not None
        assert result.artifact_type == "doc"

    def test_find_by_id_not_found(self):
        session = _sync_session()

        result = SqlArtifactRepository(session).find_by_id(uuid.uuid4())

        assert result is None

    def test_find_by_release(self):
        models = [_artifact_model(), _artifact_model()]
        session = _sync_session()
        session.query.return_value.filter_by.return_value.all.return_value = models

        results = SqlArtifactRepository(session).find_by_release(uuid.uuid4())

        assert len(results) == 2

    def test_find_by_release_empty(self):
        session = _sync_session()

        results = SqlArtifactRepository(session).find_by_release(uuid.uuid4())

        assert results == []


# ---------------------------------------------------------------------------
# VerificationResult repository (sync)
# ---------------------------------------------------------------------------

class TestSqlVerificationResultRepository:
    def test_save_new_result(self):
        session = _sync_session()
        session.get = MagicMock(return_value=None)

        result_entity = VerificationResult(
            release_id=uuid.uuid4(),
            verdict=VerdictType.VALID,
            duration_ms=800,
        )

        result = SqlVerificationResultRepository(session).save(result_entity)

        assert result is result_entity
        session.add.assert_called_once()
        session.flush.assert_called_once()

    def test_save_existing_result_skips_add(self):
        model = _vr_model()
        session = _sync_session()
        session.get = MagicMock(return_value=model)

        result_entity = VerificationResult(
            id=model.id,
            release_id=model.release_id,
            verdict=VerdictType.VALID,
            duration_ms=900,
        )

        SqlVerificationResultRepository(session).save(result_entity)

        session.add.assert_not_called()
        session.flush.assert_called_once()

    def test_find_by_id_found(self):
        model = _vr_model(verdict="INVALID", duration_ms=300)
        session = _sync_session()
        session.get = MagicMock(return_value=model)

        result = SqlVerificationResultRepository(session).find_by_id(model.id)

        assert result is not None
        assert result.verdict == VerdictType.INVALID
        assert result.duration_ms == 300

    def test_find_by_id_not_found(self):
        session = _sync_session()

        result = SqlVerificationResultRepository(session).find_by_id(uuid.uuid4())

        assert result is None

    def test_find_by_release(self):
        models = [_vr_model(), _vr_model()]
        session = _sync_session()
        (
            session.query.return_value
            .filter_by.return_value
            .order_by.return_value
            .all.return_value
        ) = models

        results = SqlVerificationResultRepository(session).find_by_release(uuid.uuid4())

        assert len(results) == 2

    def test_find_by_release_empty(self):
        session = _sync_session()

        results = SqlVerificationResultRepository(session).find_by_release(uuid.uuid4())

        assert results == []

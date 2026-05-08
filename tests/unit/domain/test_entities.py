"""
Tests for domain entities and exceptions.

Verifies field defaults, identity generation, and exception message contracts.
"""

import uuid
import pytest
from datetime import datetime

from domain.entities.enums import (
    ReleaseStatus,
    VerdictType,
    ConnectorStatus,
    SeverityType,
    UserRole,
)
from domain.entities.user import User
from domain.entities.organization import Organization
from domain.entities.project import Project
from domain.entities.release import Release
from domain.entities.artifact import Artifact
from domain.entities.connector_instance import ConnectorInstance
from domain.entities.verification_profile import VerificationProfile
from domain.entities.verification_result import VerificationResult
from domain.entities.verification_rule import VerificationRule
from domain.exceptions import (
    DomainException,
    EntityNotFoundError,
    ReleaseInvalidStateError,
    ConnectorConnectionFailedError,
    InvalidConnectorConfigurationError,
    UserNotBelongsToOrganizationError,
    VerificationProfileNotActiveError,
)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TestEnums:
    def test_release_status_string_values(self):
        assert ReleaseStatus.BORRADOR == "BORRADOR"
        assert ReleaseStatus.PENDIENTE == "PENDIENTE"
        assert ReleaseStatus.EN_VERIFICACION == "EN_VERIFICACION"
        assert ReleaseStatus.COMPLETADA == "COMPLETADA"

    def test_verdict_type_values(self):
        assert VerdictType.VALID == "VALID"
        assert VerdictType.VALID_WITH_WARNINGS == "VALID_WITH_WARNINGS"
        assert VerdictType.INVALID == "INVALID"

    def test_connector_status_values(self):
        assert ConnectorStatus.ACTIVO == "ACTIVO"
        assert ConnectorStatus.INACTIVO == "INACTIVO"
        assert ConnectorStatus.ERROR == "ERROR"

    def test_severity_type_values(self):
        assert SeverityType.INFO == "INFO"
        assert SeverityType.LOW == "LOW"
        assert SeverityType.MEDIUM == "MEDIUM"
        assert SeverityType.HIGH == "HIGH"
        assert SeverityType.CRITICAL == "CRITICAL"

    def test_user_role_values(self):
        assert UserRole.VIEWER == "VIEWER"
        assert UserRole.OPERATOR == "OPERATOR"
        assert UserRole.MANAGER == "MANAGER"
        assert UserRole.ADMIN == "ADMIN"

    def test_release_status_enum_from_string(self):
        assert ReleaseStatus("BORRADOR") is ReleaseStatus.BORRADOR

    def test_verdict_type_is_string_subclass(self):
        assert isinstance(VerdictType.VALID, str)


# ---------------------------------------------------------------------------
# Domain entities
# ---------------------------------------------------------------------------

class TestUserEntity:
    def test_fields_stored_correctly(self):
        org_id = uuid.uuid4()
        user = User(
            id=uuid.uuid4(),
            email="admin@acme.com",
            hashed_password="$2b$hash", # NOSONAR
            role=UserRole.ADMIN,
            organization_id=org_id,
        )

        assert user.email == "admin@acme.com"
        assert user.role == UserRole.ADMIN
        assert user.organization_id == org_id

    def test_timestamps_auto_set(self):
        user = User(
            id=uuid.uuid4(),
            email="u@x.com",
            hashed_password="h", # NOSONAR
            role=UserRole.VIEWER,
            organization_id=None,
        )

        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)


class TestOrganizationEntity:
    def test_defaults(self):
        org = Organization(name="Acme Corp", slug="acme-corp")

        assert org.is_active is True
        assert isinstance(org.id, uuid.UUID)
        assert isinstance(org.created_at, datetime)

    def test_unique_ids(self):
        o1 = Organization(name="X", slug="x")
        o2 = Organization(name="X", slug="x")

        assert o1.id != o2.id

    def test_explicit_id(self):
        fixed_id = uuid.uuid4()
        org = Organization(id=fixed_id, name="Y", slug="y")

        assert org.id == fixed_id


class TestProjectEntity:
    def test_fields(self):
        org_id = uuid.uuid4()
        project = Project(organization_id=org_id, name="API Service", description="Core API")

        assert project.organization_id == org_id
        assert project.name == "API Service"
        assert project.description == "Core API"

    def test_auto_id(self):
        project = Project(organization_id=uuid.uuid4(), name="X", description="")
        assert isinstance(project.id, uuid.UUID)


class TestReleaseEntity:
    def test_default_status_is_borrador(self):
        release = Release(
            project_id=uuid.uuid4(),
            profile_id=uuid.uuid4(),
            version="1.0.0",
            created_by=uuid.uuid4(),
        )

        assert release.status == ReleaseStatus.BORRADOR

    def test_default_description_is_empty(self):
        release = Release(
            project_id=uuid.uuid4(),
            profile_id=uuid.uuid4(),
            version="1.0.0",
            created_by=uuid.uuid4(),
        )

        assert release.description == ""

    def test_auto_id_and_timestamps(self):
        release = Release(
            project_id=uuid.uuid4(),
            profile_id=uuid.uuid4(),
            version="2.0.0",
            created_by=uuid.uuid4(),
        )

        assert isinstance(release.id, uuid.UUID)
        assert isinstance(release.created_at, datetime)

    def test_unique_ids_per_instance(self):
        kwargs = {
            "project_id": uuid.uuid4(),
            "profile_id": uuid.uuid4(),
            "version": "1.0.0",
            "created_by": uuid.uuid4(),
        }
        r1 = Release(**kwargs)
        r2 = Release(**kwargs)

        assert r1.id != r2.id

    def test_explicit_status(self):
        release = Release(
            project_id=uuid.uuid4(),
            profile_id=uuid.uuid4(),
            version="1.0.0",
            created_by=uuid.uuid4(),
            status=ReleaseStatus.PENDIENTE,
        )

        assert release.status == ReleaseStatus.PENDIENTE


class TestArtifactEntity:
    def test_fields_and_defaults(self):
        release_id = uuid.uuid4()
        conn_id = uuid.uuid4()
        artifact = Artifact(
            release_id=release_id,
            connector_instance_id=conn_id,
            artifact_type="commit",
            external_ref="abc123def456",
        )

        assert artifact.release_id == release_id
        assert artifact.connector_instance_id == conn_id
        assert artifact.artifact_type == "commit"
        assert artifact.external_ref == "abc123def456"
        assert artifact.metadata == {}
        assert isinstance(artifact.id, uuid.UUID)
        assert isinstance(artifact.created_at, datetime)

    def test_custom_metadata(self):
        artifact = Artifact(
            release_id=uuid.uuid4(),
            connector_instance_id=uuid.uuid4(),
            artifact_type="task",
            external_ref="JIRA-42",
            metadata={"priority": "high"},
        )

        assert artifact.metadata == {"priority": "high"}


class TestConnectorInstanceEntity:
    def test_fields(self):
        conn_id = uuid.uuid4()
        org_id = uuid.uuid4()
        instance = ConnectorInstance(
            id=conn_id,
            organization_id=org_id,
            connector_type="sonarqube",
            encrypted_credentials=b"\x00encrypted",
            status=ConnectorStatus.ACTIVO,
        )

        assert instance.id == conn_id
        assert instance.organization_id == org_id
        assert instance.connector_type == "sonarqube"
        assert instance.encrypted_credentials == b"\x00encrypted"
        assert instance.status == ConnectorStatus.ACTIVO

    def test_timestamps_auto_set(self):
        instance = ConnectorInstance(
            id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            connector_type="github",
            encrypted_credentials=b"enc",
            status=ConnectorStatus.INACTIVO,
        )

        assert isinstance(instance.created_at, datetime)


class TestVerificationProfileEntity:
    def test_empty_rules_by_default(self):
        profile = VerificationProfile(
            id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            name="QA Gate",
        )

        assert profile.name == "QA Gate"
        assert profile.rules == []

    def test_custom_rules(self):
        rule = VerificationRule(rule_id="RV-01", enabled=True)
        profile = VerificationProfile(
            id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            name="Strict",
            rules=[rule],
        )

        assert len(profile.rules) == 1
        assert profile.rules[0].rule_id == "RV-01"


class TestVerificationResultEntity:
    def test_fields_and_defaults(self):
        release_id = uuid.uuid4()
        result = VerificationResult(
            release_id=release_id,
            verdict=VerdictType.VALID,
            duration_ms=1234,
        )

        assert result.release_id == release_id
        assert result.verdict == VerdictType.VALID
        assert result.duration_ms == 1234
        assert result.rule_results == {}
        assert result.profile_snapshot == {}
        assert isinstance(result.id, uuid.UUID)
        assert isinstance(result.executed_at, datetime)

    def test_invalid_verdict(self):
        result = VerificationResult(
            release_id=uuid.uuid4(),
            verdict=VerdictType.INVALID,
            duration_ms=500,
        )

        assert result.verdict == VerdictType.INVALID


class TestVerificationRuleEntity:
    def test_defaults(self):
        rule = VerificationRule(rule_id="RV-05")

        assert rule.rule_id == "RV-05"
        assert rule.enabled is True
        assert rule.config == {}

    def test_explicit_config(self):
        rule = VerificationRule(
            rule_id="RV-02", enabled=False, config={"threshold": 90}
        )

        assert rule.enabled is False
        assert rule.config == {"threshold": 90}


# ---------------------------------------------------------------------------
# Domain exceptions
# ---------------------------------------------------------------------------

class TestDomainExceptions:
    def test_domain_exception_message_and_str(self):
        exc = DomainException("something went wrong")

        assert exc.message == "something went wrong"
        assert str(exc) == "something went wrong"
        assert isinstance(exc, Exception)

    def test_entity_not_found_error_inherits(self):
        exc = EntityNotFoundError("Release 123 not found")

        assert exc.message == "Release 123 not found"
        assert isinstance(exc, DomainException)

    def test_release_invalid_state_error_message_contains_state(self):
        release_id = uuid.uuid4()
        exc = ReleaseInvalidStateError(release_id, "BORRADOR", "PENDIENTE")

        assert "BORRADOR" in exc.message
        assert "PENDIENTE" in exc.message
        assert str(release_id) in exc.message
        assert isinstance(exc, DomainException)

    def test_connector_connection_failed_error(self):
        exc = ConnectorConnectionFailedError("authentication timeout")

        assert exc.message == "authentication timeout"
        assert isinstance(exc, DomainException)

    def test_invalid_connector_configuration_error(self):
        exc = InvalidConnectorConfigurationError("missing required field 'host'")

        assert isinstance(exc, DomainException)
        assert "missing required field" in exc.message

    def test_user_not_belongs_to_organization_error(self):
        exc = UserNotBelongsToOrganizationError("user does not belong to org")

        assert isinstance(exc, DomainException)

    def test_verification_profile_not_active_error(self):
        exc = VerificationProfileNotActiveError("profile is disabled")

        assert isinstance(exc, DomainException)

    def test_all_exceptions_are_catchable_as_domain_exception(self):
        errors = [
            EntityNotFoundError("e"),
            ConnectorConnectionFailedError("c"),
            InvalidConnectorConfigurationError("i"),
            UserNotBelongsToOrganizationError("u"),
            VerificationProfileNotActiveError("v"),
        ]

        for err in errors:
            assert isinstance(err, DomainException)

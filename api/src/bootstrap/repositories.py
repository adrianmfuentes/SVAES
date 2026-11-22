from __future__ import annotations

from features.connectors.infrastructure.gateways import create_registered_connector_registry
from features.connectors.infrastructure.gateways.connector_registry import ConnectorRegistry
from features.connectors.infrastructure.persistence.connector_repository import SqlConnectorRepository
from features.identity.infrastructure.persistence.api_key_repository import SqlAPIKeyRepository
from features.identity.infrastructure.persistence.custom_role_repository import SqlCustomRoleRepository
from features.identity.infrastructure.persistence.user_membership_repository import SqlUserMembershipRepository
from features.identity.infrastructure.persistence.user_repository import SqlUserRepository
from features.notifications.infrastructure.persistence.notification_repository import SqlNotificationRepository
from features.organizations.infrastructure.persistence.organization_repository import SqlOrganizationRepository
from features.projects_releases.infrastructure.persistence.artifact_repository import SqlArtifactRepository
from features.projects_releases.infrastructure.persistence.project_repository import SqlProjectRepository
from features.projects_releases.infrastructure.persistence.release_repository import SqlReleaseRepository
from features.verification.infrastructure.persistence.profile_repository import SqlProfileRepository
from features.verification.infrastructure.persistence.rule_repository import SqlVerificationRuleRepository
from features.verification.infrastructure.persistence.template_repository import SqlTemplateRepository
from features.verification.infrastructure.persistence.verification_result_repository import SqlVerificationResultRepository
from shared.infrastructure.queue.celery_task_queue import CeleryTaskQueue


def get_user_repository() -> SqlUserRepository:
    return SqlUserRepository()


def get_organization_repository() -> SqlOrganizationRepository:
    return SqlOrganizationRepository()


def get_user_membership_repository() -> SqlUserMembershipRepository:
    return SqlUserMembershipRepository()


def get_connector_repository() -> SqlConnectorRepository:
    return SqlConnectorRepository()


def get_profile_repository() -> SqlProfileRepository:
    return SqlProfileRepository()


def get_rule_repository() -> SqlVerificationRuleRepository:
    return SqlVerificationRuleRepository()


def get_verification_result_repository() -> SqlVerificationResultRepository:
    return SqlVerificationResultRepository()


def get_custom_role_repository() -> SqlCustomRoleRepository:
    return SqlCustomRoleRepository()


def get_api_key_repository() -> SqlAPIKeyRepository:
    return SqlAPIKeyRepository()


def get_project_repository() -> SqlProjectRepository:
    return SqlProjectRepository()


def get_release_repository() -> SqlReleaseRepository:
    return SqlReleaseRepository()


def get_artifact_repository() -> SqlArtifactRepository:
    return SqlArtifactRepository()


def get_task_queue() -> CeleryTaskQueue:
    return CeleryTaskQueue()


def get_connector_registry() -> ConnectorRegistry:
    return create_registered_connector_registry()


def get_template_repository() -> SqlTemplateRepository:
    return SqlTemplateRepository()


def get_notification_repository() -> SqlNotificationRepository:
    return SqlNotificationRepository()

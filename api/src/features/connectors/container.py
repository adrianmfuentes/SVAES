from __future__ import annotations

from bootstrap.repositories import get_connector_registry, get_connector_repository, get_organization_repository, get_project_repository
from fastapi import Depends
from features.connectors.application.ports.i_connector_service import IConnectorService
from features.connectors.application.use_cases.connector_service import ConnectorService
from features.connectors.application.use_cases.handle_incoming_webhook import HandleIncomingWebhookUseCase
from features.connectors.infrastructure.gateways.artifact_probe import HttpConnectorArtifactProbe
from features.connectors.infrastructure.gateways.connector_registry import ConnectorRegistry
from features.connectors.infrastructure.persistence.connector_repository import SqlConnectorRepository
from features.organizations.infrastructure.persistence.organization_repository import SqlOrganizationRepository
from features.projects_releases.application.ports.i_release_service import IReleaseService
from features.projects_releases.container import get_release_service
from features.projects_releases.infrastructure.persistence.project_repository import SqlProjectRepository
from features.verification.application.ports.i_verification_service import IVerificationService
from features.verification.container import get_verification_service
from shared.infrastructure.audit_db import get_audit_logger
from shared.infrastructure.fernet_encryptor import create_credential_encryptor


def get_webhook_use_case(
    connector_repo: SqlConnectorRepository = Depends(get_connector_repository),
    project_repo: SqlProjectRepository = Depends(get_project_repository),
    organization_repo: SqlOrganizationRepository = Depends(get_organization_repository),
    release_service: IReleaseService = Depends(get_release_service),
    verification_service: IVerificationService = Depends(get_verification_service),
) -> HandleIncomingWebhookUseCase:
    return HandleIncomingWebhookUseCase(
        connector_repository=connector_repo,
        project_repository=project_repo,
        organization_repository=organization_repo,
        release_service=release_service,
        verification_service=verification_service,
        credential_encryptor=create_credential_encryptor(),
    )


def get_connector_service(
    connector_repo: SqlConnectorRepository = Depends(get_connector_repository),
    connector_registry: ConnectorRegistry = Depends(get_connector_registry),
) -> IConnectorService:
    return ConnectorService(
        connector_repository=connector_repo,
        connector_registry=connector_registry,
        credential_encryptor=create_credential_encryptor(),
        audit_logger=get_audit_logger(),
        artifact_probe=HttpConnectorArtifactProbe(),
    )

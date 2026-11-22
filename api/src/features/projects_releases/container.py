from __future__ import annotations

from bootstrap.repositories import get_artifact_repository, get_connector_registry, get_connector_repository, get_profile_repository, get_project_repository, get_release_repository
from fastapi import Depends
from features.connectors.infrastructure.persistence.connector_repository import SqlConnectorRepository
from features.projects_releases.application.ports.i_artifact_service import IArtifactService
from features.projects_releases.application.ports.i_release_service import IReleaseService
from features.projects_releases.application.use_cases.artifact_service import ArtifactService
from features.projects_releases.application.use_cases.release_service import CreateReleaseUseCase
from features.projects_releases.infrastructure.persistence.artifact_repository import SqlArtifactRepository
from features.projects_releases.infrastructure.persistence.project_repository import SqlProjectRepository
from features.projects_releases.infrastructure.persistence.release_repository import SqlReleaseRepository
from features.verification.infrastructure.persistence.profile_repository import SqlProfileRepository
from shared.infrastructure.audit_db import get_audit_logger


def get_release_service(
    release_repo: SqlReleaseRepository = Depends(get_release_repository),
    project_repo: SqlProjectRepository = Depends(get_project_repository),
    profile_repo: SqlProfileRepository = Depends(get_profile_repository),
) -> IReleaseService:
    return CreateReleaseUseCase(
        release_repository=release_repo,
        project_repository=project_repo,
        profile_repository=profile_repo,
        audit_logger=get_audit_logger(),
    )


def get_artifact_service(
    artifact_repo: SqlArtifactRepository = Depends(get_artifact_repository),
    release_repo: SqlReleaseRepository = Depends(get_release_repository),
    connector_repo: SqlConnectorRepository = Depends(get_connector_repository),
) -> IArtifactService:
    return ArtifactService(
        artifact_repository=artifact_repo,
        release_repository=release_repo,
        connector_repository=connector_repo,
        connector_registry=get_connector_registry(),
    )

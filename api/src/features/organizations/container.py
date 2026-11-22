from __future__ import annotations

from bootstrap.repositories import get_organization_repository, get_profile_repository, get_project_repository, get_user_membership_repository, get_user_repository
from fastapi import Depends
from features.identity.infrastructure.persistence.user_membership_repository import SqlUserMembershipRepository
from features.identity.infrastructure.persistence.user_repository import SqlUserRepository
from features.organizations.application.ports.i_organization_service import IOrganizationService
from features.organizations.application.use_cases.create_organization import CreateOrganization
from features.organizations.application.use_cases.organization_service import OrganizationService
from features.organizations.infrastructure.persistence.organization_repository import SqlOrganizationRepository
from features.projects_releases.infrastructure.persistence.project_repository import SqlProjectRepository
from features.verification.infrastructure.persistence.profile_repository import SqlProfileRepository
from shared.infrastructure.audit_db import get_audit_logger
from shared.infrastructure.database.get_async_session import AsyncSessionLocal
from shared.infrastructure.sql_unit_of_work import SqlUnitOfWork


def get_organization_service(
    org_repo: SqlOrganizationRepository = Depends(get_organization_repository),
    project_repo: SqlProjectRepository = Depends(get_project_repository),
    user_repo: SqlUserRepository = Depends(get_user_repository),
    profile_repo: SqlProfileRepository = Depends(get_profile_repository),
    membership_repo: SqlUserMembershipRepository = Depends(get_user_membership_repository),
) -> IOrganizationService:
    return OrganizationService(
        organization_repository=org_repo,
        project_repository=project_repo,
        user_repository=user_repo,
        profile_repository=profile_repo,
        user_membership_repository=membership_repo,
        audit_logger=get_audit_logger(),
    )


def _transactional_organization_service(unit_of_work: SqlUnitOfWork) -> IOrganizationService:
    return OrganizationService(
        organization_repository=SqlOrganizationRepository(unit_of_work.session),
        project_repository=SqlProjectRepository(),
        user_repository=SqlUserRepository(unit_of_work.session),
        user_membership_repository=SqlUserMembershipRepository(unit_of_work.session),
        audit_logger=get_audit_logger(),
    )


def get_create_organization() -> CreateOrganization:
    unit_of_work = SqlUnitOfWork(AsyncSessionLocal())
    return CreateOrganization(_transactional_organization_service(unit_of_work), unit_of_work)

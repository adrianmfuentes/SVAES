from __future__ import annotations

from bootstrap.authentication import CurrentUser, get_current_user
from bootstrap.repositories import get_api_key_repository, get_connector_repository, get_custom_role_repository, get_notification_repository, get_organization_repository, get_profile_repository, get_project_repository, get_release_repository, get_rule_repository, get_user_membership_repository
from dataclasses import dataclass
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from features.connectors.infrastructure.persistence.connector_repository import SqlConnectorRepository
from features.identity.infrastructure.persistence.api_key_repository import SqlAPIKeyRepository
from features.identity.infrastructure.persistence.custom_role_repository import SqlCustomRoleRepository
from features.identity.infrastructure.persistence.user_membership_repository import SqlUserMembershipRepository
from features.notifications.infrastructure.persistence.notification_repository import SqlNotificationRepository
from features.organizations.infrastructure.persistence.organization_repository import SqlOrganizationRepository
from features.projects_releases.domain.project import Project
from features.projects_releases.infrastructure.persistence.project_repository import SqlProjectRepository
from features.projects_releases.infrastructure.persistence.release_repository import SqlReleaseRepository
from features.verification.infrastructure.persistence.profile_repository import SqlProfileRepository
from features.verification.infrastructure.persistence.rule_repository import SqlVerificationRuleRepository
from shared.domain.enums import Permission
from shared.domain.enums import UserRole
from typing import Optional
from uuid import UUID


@dataclass
class ProjectAccess:
    user: CurrentUser
    project: Optional[Project] = None


def require_permission(permission: Permission):
    def dependency(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if not current_user.role.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No tienes permiso: {permission.value}",
            )
        return current_user
    return dependency  # NOSONAR


def require_org_access():
    async def dependency(
        org_id: UUID,
        current_user: CurrentUser = Depends(get_current_user),
        org_repo: SqlOrganizationRepository = Depends(get_organization_repository),
        membership_repo: SqlUserMembershipRepository = Depends(get_user_membership_repository),
    ) -> CurrentUser:
        if current_user.role != UserRole.U3 and current_user.organization_id != org_id:
            org = await org_repo.get_by_id(org_id)
            is_owner = bool(org and org.owner_id == current_user.user_id)
            # El usuario puede tener membership en org_id aunque su organización
            # "activa" (la del JWT) sea otra distinta (soporte multi-organización).
            is_member = bool(await membership_repo.get(current_user.user_id, org_id))
            if not org or (not is_owner and not is_member):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes acceso a esta organización",
                )
        return current_user
    return dependency  # NOSONAR


def require_project_access():
    async def dependency(
        project_id: UUID,
        current_user: CurrentUser = Depends(get_current_user),
        project_repo: SqlProjectRepository = Depends(get_project_repository),
        org_repo: SqlOrganizationRepository = Depends(get_organization_repository),
    ) -> ProjectAccess:
        project = None
        if current_user.role != UserRole.U3:
            project = await project_repo.get_by_id(project_id)
            if not project:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado")

            if project.organization_id != current_user.organization_id:
                org = await org_repo.get_by_id(project.organization_id)
                if not (org and org.owner_id == current_user.user_id):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="No tienes acceso a este proyecto",
                    )
        return ProjectAccess(user=current_user, project=project)
    return dependency  # NOSONAR


def require_role(min_role: UserRole):
    def dependency(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        role_hierarchy = [UserRole.U2, UserRole.U4, UserRole.U3]
        if min_role == UserRole.U3:
            required_idx = 2
        elif min_role == UserRole.U4:
            required_idx = 1
        elif min_role == UserRole.U2:
            required_idx = 0
        else:
            required_idx = -1

        user_idx = role_hierarchy.index(current_user.role) if current_user.role in role_hierarchy else -1
        if user_idx < required_idx:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere rol {min_role.value} o superior",
            )
        return current_user
    return dependency  # NOSONAR


def require_release_access():
    async def dependency(
        id: UUID,
        current_user: CurrentUser = Depends(get_current_user),
        release_repo: SqlReleaseRepository = Depends(get_release_repository),
        project_repo: SqlProjectRepository = Depends(get_project_repository),
        org_repo: SqlOrganizationRepository = Depends(get_organization_repository),
    ) -> CurrentUser:
        if current_user.role != UserRole.U3:
            release = await release_repo.get_by_id(id)
            if not release:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Release no encontrada")

            project = await project_repo.get_by_id(release.project_id)
            if not project:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado")

            if project.organization_id != current_user.organization_id:
                org = await org_repo.get_by_id(project.organization_id)
                if not (org and org.owner_id == current_user.user_id):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="No tienes acceso a esta release",
                    )
        return current_user
    return dependency  # NOSONAR


def require_connector_access():
    async def dependency(
        connector_id: UUID,
        current_user: CurrentUser = Depends(get_current_user),
        connector_repo: SqlConnectorRepository = Depends(get_connector_repository),
        org_repo: SqlOrganizationRepository = Depends(get_organization_repository),
    ) -> CurrentUser:
        if current_user.role != UserRole.U3:
            connector = await connector_repo.get_by_id(connector_id)
            if not connector:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conector no encontrado")

            if connector.organization_id != current_user.organization_id:
                org = await org_repo.get_by_id(connector.organization_id)
                if not (org and org.owner_id == current_user.user_id):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="No tienes acceso a este conector",
                    )
        return current_user
    return dependency  # NOSONAR


def require_profile_access():
    async def dependency(
        profile_id: UUID,
        current_user: CurrentUser = Depends(get_current_user),
        profile_repo: SqlProfileRepository = Depends(get_profile_repository),
        org_repo: SqlOrganizationRepository = Depends(get_organization_repository),
    ) -> None:
        if current_user.role != UserRole.U3:
            profile = await profile_repo.get_by_id(profile_id)
            if not profile:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil no encontrado")

            if profile.is_system:
                return

            if profile.organization_id != current_user.organization_id:
                if profile.organization_id is None:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="No tienes acceso a este perfil",
                    )
                org = await org_repo.get_by_id(profile.organization_id)
                if not (org and org.owner_id == current_user.user_id):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="No tienes acceso a este perfil",
                    )
    return dependency  # NOSONAR


def require_rule_access():
    async def dependency(
        rule_id: UUID,
        current_user: CurrentUser = Depends(get_current_user),
        rule_repo: SqlVerificationRuleRepository = Depends(get_rule_repository),
        profile_repo: SqlProfileRepository = Depends(get_profile_repository),
        org_repo: SqlOrganizationRepository = Depends(get_organization_repository),
    ) -> CurrentUser:
        if current_user.role != UserRole.U3:
            rule = await rule_repo.get_by_id(rule_id)
            if not rule:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Regla no encontrada")

            profile = await profile_repo.get_by_id(rule.profile_id)
            if profile and profile.organization_id != current_user.organization_id:
                if profile.organization_id is None:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="No tienes acceso a esta regla",
                    )
                org = await org_repo.get_by_id(profile.organization_id)
                if not (org and org.owner_id == current_user.user_id):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="No tienes acceso a esta regla",
                    )
        return current_user
    return dependency  # NOSONAR


def require_custom_role_access():
    async def dependency(
        role_id: UUID,
        current_user: CurrentUser = Depends(get_current_user),
        role_repo: SqlCustomRoleRepository = Depends(get_custom_role_repository),
    ) -> CurrentUser:
        if current_user.role != UserRole.U3:
            role = await role_repo.get_by_id(role_id)
            if not role:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado")

            if role.organization_id != current_user.organization_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes acceso a este rol",
                )
        return current_user
    return dependency  # NOSONAR


def require_api_key_access():
    async def dependency(
        key_id: UUID,
        current_user: CurrentUser = Depends(get_current_user),
        api_key_repo: SqlAPIKeyRepository = Depends(get_api_key_repository),
    ) -> CurrentUser:
        if current_user.role != UserRole.U3:
            api_key = await api_key_repo.get_by_id(key_id)
            if not api_key:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key no encontrada")

            if api_key.organization_id != current_user.organization_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes acceso a esta API key",
                )
        return current_user
    return dependency  # NOSONAR


def require_notification_channel_access():
    async def dependency(
        channel_id: UUID,
        current_user: CurrentUser = Depends(get_current_user),
        notification_repo: SqlNotificationRepository = Depends(get_notification_repository),
        org_repo: SqlOrganizationRepository = Depends(get_organization_repository),
    ) -> CurrentUser:
        if current_user.role != UserRole.U3:
            channel = await notification_repo.get_channel_by_id(channel_id)
            if not channel:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Canal de notificación no encontrado")

            if channel.organization_id != current_user.organization_id:
                org = await org_repo.get_by_id(channel.organization_id)
                if not (org and org.owner_id == current_user.user_id):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="No tienes acceso a este canal de notificación",
                    )
        return current_user
    return dependency  # NOSONAR

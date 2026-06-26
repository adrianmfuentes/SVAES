"""
Este archivo define las dependencias que se pueden inyectar en los endpoints de FastAPI.
Estas dependencias pueden ser utilizadas para manejar la autenticación, autorización, validación de datos, entre otras funcionalidades comunes en los endpoints.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from functools import wraps
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Callable, Optional
from uuid import UUID
from infrastructure.secondary.database.repositories.project_repository import SqlProjectRepository
from infrastructure.secondary.database.repositories.release_repository import SqlReleaseRepository
from infrastructure.secondary.database.repositories.user_repository import SqlUserRepository
from infrastructure.secondary.database.repositories.organization_repository import SqlOrganizationRepository
from infrastructure.secondary.database.repositories.connector_repository import SqlConnectorRepository
from infrastructure.secondary.database.repositories.artifact_repository import SqlArtifactRepository
from infrastructure.secondary.database.repositories.verification_result_repository import SqlVerificationResultRepository
from infrastructure.secondary.database.repositories.profile_repository import SqlProfileRepository
from infrastructure.secondary.database.repositories.rule_repository import SqlVerificationRuleRepository
from infrastructure.primary.middleware.jwt_handler import JwtHandler
from infrastructure.primary.middleware.password_hasher import BcryptPasswordHasher
from core.config import Settings, get_settings
from application.use_cases.main.release_service import CreateReleaseUseCase
from application.use_cases.main.artifact_service import ArtifactService
from application.use_cases.main.verification_service import VerificationService
from application.use_cases.main.auth_service import AuthService
from application.use_cases.main.organization_service import OrganizationService
from application.use_cases.main.connector_service import ConnectorService
from application.use_cases.main.profile_service import ProfileService
from application.use_cases.main.task_service import TaskService
from application.use_cases.main.user_service import UserService
from application.use_cases.main.custom_role_service import CustomRoleService
from application.use_cases.main.template_service import TemplateService
from application.use_cases.main.notification_service import NotificationService
from application.use_cases.main.rules_service import RulesService
from application.use_cases.main.export_service import ExportService
from application.ports.input.i_release_service import IReleaseService
from application.ports.input.i_artifact_service import IArtifactService
from application.ports.input.i_verification_service import IVerificationService
from application.ports.input.i_auth_service import IAuthService
from application.ports.input.i_user_service import IUserService
from application.ports.input.i_organization_service import IOrganizationService
from application.ports.input.i_connector_service import IConnectorService
from application.ports.input.i_profile_service import IProfileService
from application.ports.input.i_task_service import ITaskService
from application.ports.input.i_custom_role_service import ICustomRoleService
from application.ports.input.i_template_service import ITemplateService
from application.ports.input.i_notification_service import INotificationService
from application.ports.input.i_rules_service import IRulesService
from application.ports.input.i_export_service import IExportService
from application.ports.output.i_token_service import ITokenService
from application.ports.output.i_password_hasher import IPasswordHasher
from infrastructure.secondary.queue.celery_task_queue import CeleryTaskQueue
from infrastructure.secondary.database.repositories.custom_role_repository import SqlCustomRoleRepository
from infrastructure.secondary.database.repositories.template_repository import SqlTemplateRepository
from infrastructure.secondary.database.repositories.notification_repository import SqlNotificationRepository
from infrastructure.secondary.database.repositories.api_key_repository import SqlAPIKeyRepository
from infrastructure.secondary.connectors.connector_registry import ConnectorRegistry
from infrastructure.secondary.connectors import create_registered_connector_registry
from domain.enums import UserRole, Permission
from domain.entities.project import Project

_bearer = HTTPBearer(auto_error=False)
_INVALID_TOKEN = "Token inválido"
_API_KEY_HDR = "X-API-Key"


def get_settings_dependency() -> Settings:
    return get_settings()


async def get_current_user_or_api_key(
    request: Request,
    settings: Settings = Depends(get_settings_dependency),
) -> CurrentUser:
    raw_key = request.headers.get(_API_KEY_HDR)
    if raw_key:
        api_key_user = await _validate_api_key(raw_key)
        if api_key_user:
            return api_key_user
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_TOKEN)

    credentials = None
    try:
        credentials = await _bearer(request)
    except Exception:
        pass

    if credentials:
        handler = JwtHandler(
            secret=settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
            access_token_expire_minutes=settings.jwt_expire_minutes,
            refresh_token_expire_days=30,
            redis_url=settings.redis_url,
        )
        try:
            payload = handler.decode_token(credentials.credentials)
            api_key_repo = SqlAPIKeyRepository()
            user_keys = await api_key_repo.list_by_user(payload.user_id)
            active_keys = [
                k for k in user_keys
                if k.is_active and (k.expires_at is None or k.expires_at > datetime.now(timezone.utc))
            ]
            if active_keys:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_TOKEN)
            return CurrentUser(
                user_id=payload.user_id,
                role=UserRole(payload.role),
                email=payload.email,
                organization_id=payload.organization_id,
            )
        except ValueError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_TOKEN)

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_TOKEN)


async def get_current_user_api_key_only(
    request: Request,
) -> "CurrentUser":
    raw_key = request.headers.get(_API_KEY_HDR)
    if not raw_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_TOKEN)
    api_key_user = await _validate_api_key(raw_key)
    if not api_key_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_TOKEN)
    return api_key_user


async def _validate_api_key(raw_key: str) -> Optional[CurrentUser]:
    from application.use_cases.others.manage_api_keys import ManageApiKeysUseCase

    try:
        repo = SqlAPIKeyRepository()
        user_repo = SqlUserRepository()
        use_case = ManageApiKeysUseCase(api_key_repository=repo)
        api_key = await use_case.validate_api_key(raw_key)
        if not api_key:
            return None
        db_user = await user_repo.get_by_id(api_key.user_id)
        role = db_user.role if db_user else UserRole.U2
        return CurrentUser(
            user_id=api_key.user_id,
            role=role,
            email=db_user.email if db_user else "api_key_user",
            organization_id=api_key.organization_id,
            auth_via_api_key=True,
        )
    except Exception:
        return None


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    settings: Settings = Depends(get_settings_dependency),
) -> UUID:
    handler = JwtHandler(
        secret=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        access_token_expire_minutes=settings.jwt_expire_minutes,
        refresh_token_expire_days=30,
        redis_url=settings.redis_url,
    )
    try:
        payload = handler.decode_token(credentials.credentials)
        return payload.user_id
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_TOKEN)


def get_current_user_role(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    settings: Settings = Depends(get_settings_dependency),
):
    handler = JwtHandler(
        secret=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        access_token_expire_minutes=settings.jwt_expire_minutes,
        refresh_token_expire_days=30,
        redis_url=settings.redis_url,
    )
    try:
        payload = handler.decode_token(credentials.credentials)
        return UserRole(payload.role)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_TOKEN)


@dataclass
class CurrentUser:
    user_id: UUID
    role: UserRole
    email: str
    organization_id: Optional[UUID] = None
    auth_via_api_key: bool = False


@dataclass
class ProjectAccess:
    user: CurrentUser
    project: Optional[Project] = None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    settings: Settings = Depends(get_settings_dependency),
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_TOKEN)
    handler = JwtHandler(
        secret=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        access_token_expire_minutes=settings.jwt_expire_minutes,
        refresh_token_expire_days=30,
        redis_url=settings.redis_url,
    )
    try:
        payload = handler.decode_token(credentials.credentials)
        user_repo = SqlUserRepository()
        user = await user_repo.get_by_id(payload.user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_TOKEN)
        return CurrentUser(
            user_id=payload.user_id,
            role=UserRole(payload.role),
            email=payload.email,
            organization_id=payload.organization_id,
        )
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_TOKEN)


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
    ) -> CurrentUser:
        if current_user.role != UserRole.U3 and current_user.organization_id != org_id:
            org = await org_repo.get_by_id(org_id)
            if not org or org.owner_id != current_user.user_id:
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


def get_jwt_handler(
    settings: Settings = Depends(get_settings_dependency),
) -> JwtHandler:
    return JwtHandler(
        secret=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        access_token_expire_minutes=settings.jwt_expire_minutes,
        refresh_token_expire_days=30,
        redis_url=settings.redis_url,
    )


def get_password_hasher() -> IPasswordHasher:
    return BcryptPasswordHasher()


def get_user_repository() -> SqlUserRepository:
    return SqlUserRepository()


def get_organization_repository() -> SqlOrganizationRepository:
    return SqlOrganizationRepository()


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


def get_release_repository() -> SqlReleaseRepository:
    return SqlReleaseRepository()


def get_artifact_repository() -> SqlArtifactRepository:
    return SqlArtifactRepository()


def get_task_queue() -> CeleryTaskQueue:
    return CeleryTaskQueue()


def get_release_service(
    release_repo: SqlReleaseRepository = Depends(get_release_repository),
    project_repo: SqlProjectRepository = Depends(get_project_repository),
    profile_repo: SqlProfileRepository = Depends(get_profile_repository),
) -> IReleaseService:
    return CreateReleaseUseCase(
        release_repository=release_repo,
        project_repository=project_repo,
        profile_repository=profile_repo,
    )


def get_artifact_service(
    artifact_repo: SqlArtifactRepository = Depends(get_artifact_repository),
    release_repo: SqlReleaseRepository = Depends(get_release_repository),
) -> IArtifactService:
    return ArtifactService(
        artifact_repository=artifact_repo,
        release_repository=release_repo,
    )


def get_verification_service(
    release_repo: SqlReleaseRepository = Depends(get_release_repository),
) -> IVerificationService:
    verification_repo = SqlVerificationResultRepository()
    task_queue = CeleryTaskQueue()
    connector_registry = create_registered_connector_registry()
    connector_repo = SqlConnectorRepository()
    return VerificationService(
        release_repository=release_repo,
        verification_repository=verification_repo,
        task_queue=task_queue,
        connector_registry=connector_registry,
        connector_repository=connector_repo,
    )


def get_auth_service(
    user_repo: SqlUserRepository = Depends(get_user_repository),
    settings: Settings = Depends(get_settings_dependency),
) -> IAuthService:
    jwt_handler = get_jwt_handler(settings)
    password_hasher = get_password_hasher()
    return AuthService(
        user_repository=user_repo,
        token_service=jwt_handler,
        password_hasher=password_hasher,
    )


def get_organization_service(
    org_repo: SqlOrganizationRepository = Depends(get_organization_repository),
    project_repo: SqlProjectRepository = Depends(get_project_repository),
    user_repo: SqlUserRepository = Depends(get_user_repository),
    profile_repo: SqlProfileRepository = Depends(get_profile_repository),
) -> IOrganizationService:
    return OrganizationService(
        organization_repository=org_repo,
        project_repository=project_repo,
        user_repository=user_repo,
        profile_repository=profile_repo,
    )


def get_connector_registry() -> ConnectorRegistry:
    return create_registered_connector_registry()


def get_connector_service(
    connector_repo: SqlConnectorRepository = Depends(get_connector_repository),
    connector_registry: ConnectorRegistry = Depends(get_connector_registry),
) -> IConnectorService:
    return ConnectorService(
        connector_repository=connector_repo,
        connector_registry=connector_registry,
    )


def get_profile_service(
    profile_repo: SqlProfileRepository = Depends(get_profile_repository),
    rule_repo: SqlVerificationRuleRepository = Depends(get_rule_repository),
) -> IProfileService:
    return ProfileService(
        profile_repository=profile_repo,
        rule_repository=rule_repo,
    )


def get_task_service(
    task_queue: CeleryTaskQueue = Depends(get_task_queue),
) -> ITaskService:
    return TaskService(
        task_queue=task_queue,
    )


def get_user_service(
    user_repo: SqlUserRepository = Depends(get_user_repository),
    org_repo: SqlOrganizationRepository = Depends(get_organization_repository),
) -> IUserService:
    password_hasher = get_password_hasher()
    return UserService(
        user_repository=user_repo,
        organization_repository=org_repo,
        password_hasher=password_hasher,
    )


def get_template_repository() -> SqlTemplateRepository:
    return SqlTemplateRepository()


def get_custom_role_service(
    role_repo: SqlCustomRoleRepository = Depends(get_custom_role_repository),
) -> ICustomRoleService:
    return CustomRoleService(custom_role_repository=role_repo)


def get_template_service() -> ITemplateService:
    template_repo = get_template_repository()
    profile_repo = get_profile_repository()
    return TemplateService(
        template_repository=template_repo,
        profile_repository=profile_repo,
    )


def get_notification_repository() -> SqlNotificationRepository:
    return SqlNotificationRepository()


def get_notification_service() -> INotificationService:
    notification_repo = get_notification_repository()
    return NotificationService(
        notification_repository=notification_repo,
    )


def get_rules_service() -> IRulesService:
    rule_repo = get_rule_repository()
    return RulesService(
        rule_repository=rule_repo,
    )


def get_export_service() -> IExportService:
    release_repo = get_release_repository()
    verification_repo = get_verification_result_repository()
    project_repo = get_project_repository()
    return ExportService(
        release_repository=release_repo,
        verification_repository=verification_repo,
        project_repository=project_repo,
    )
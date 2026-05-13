"""
Este archivo define las dependencias que se pueden inyectar en los endpoints de FastAPI.
Estas dependencias pueden ser utilizadas para manejar la autenticación, autorización, validación de datos, entre otras funcionalidades comunes en los endpoints.
"""

from dataclasses import dataclass
from functools import wraps
from fastapi import Depends, HTTPException, status
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
from application.ports.output.i_token_service import ITokenService
from application.ports.output.i_password_hasher import IPasswordHasher
from infrastructure.secondary.queue.celery_task_queue import CeleryTaskQueue
from infrastructure.secondary.database.repositories.custom_role_repository import SqlCustomRoleRepository
from infrastructure.secondary.connectors.connector_registry import ConnectorRegistry
from infrastructure.secondary.connectors import create_registered_connector_registry
from domain.enums import UserRole, Permission

_bearer = HTTPBearer()


def get_settings_dependency() -> Settings:
    return get_settings()


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    settings: Settings = Depends(get_settings_dependency),
) -> UUID:
    handler = JwtHandler(
        secret=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expire_minutes=settings.jwt_expire_minutes,
    )
    try:
        payload = handler.decode_token(credentials.credentials)
        return payload.user_id
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")


def get_current_user_role(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    settings: Settings = Depends(get_settings_dependency),
):
    handler = JwtHandler(
        secret=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expire_minutes=settings.jwt_expire_minutes,
    )
    try:
        payload = handler.decode_token(credentials.credentials)
        return UserRole(payload.role)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")


@dataclass
class CurrentUser:
    user_id: UUID
    role: UserRole
    email: str
    organization_id: Optional[UUID] = None


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    settings: Settings = Depends(get_settings_dependency),
) -> CurrentUser:
    handler = JwtHandler(
        secret=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expire_minutes=settings.jwt_expire_minutes,
    )
    try:
        payload = handler.decode_token(credentials.credentials)
        return CurrentUser(
            user_id=payload.user_id,
            role=payload.role,
            email=payload.email,
            organization_id=payload.organization_id,
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")


def require_permission(permission: Permission, require_org_owner: bool = False):
    def dependency(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if not current_user.role.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No tienes permiso: {permission.value}",
            )
        return current_user
    return dependency


def require_org_access(org_id_param: str = "org_id"):
    def dependency(
        org_id: UUID,
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if current_user.organization_id != org_id and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes acceso a esta organización",
            )
        return current_user
    return dependency


def require_project_access(project_id_param: str = "project_id"):
    async def dependency(
        project_id: UUID,
        current_user: CurrentUser = Depends(get_current_user),
        project_repo: SqlProjectRepository = Depends(get_project_repository),
    ) -> CurrentUser:
        if current_user.role == UserRole.ADMIN:
            return current_user

        project = await project_repo.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado")

        if project.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes acceso a este proyecto",
            )
        return current_user
    return dependency


def require_role(min_role: UserRole):
    def dependency(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        role_hierarchy = [UserRole.VIEWER, UserRole.OPERATOR, UserRole.MANAGER, UserRole.ADMIN]
        if min_role == UserRole.ADMIN:
            required_idx = 3
        elif min_role == UserRole.MANAGER:
            required_idx = 2
        elif min_role == UserRole.OPERATOR:
            required_idx = 1
        else:
            required_idx = 0

        user_idx = role_hierarchy.index(current_user.role) if current_user.role in role_hierarchy else -1
        if user_idx < required_idx:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere rol {min_role.value} o superior",
            )
        return current_user
    return dependency


def get_jwt_handler(
    settings: Settings = Depends(get_settings_dependency),
) -> JwtHandler:
    return JwtHandler(
        secret=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expire_minutes=settings.jwt_expire_minutes,
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


def get_custom_role_repository() -> SqlCustomRoleRepository:
    return SqlCustomRoleRepository()


def get_project_repository() -> SqlProjectRepository:
    return SqlProjectRepository()


def get_release_repository() -> SqlReleaseRepository:
    return SqlReleaseRepository()


def get_artifact_repository() -> SqlArtifactRepository:
    return SqlArtifactRepository()


def get_task_queue() -> CeleryTaskQueue:
    return CeleryTaskQueue()


def get_release_service(
    release_repo: SqlReleaseRepository = Depends(get_release_repository),
    project_repo: SqlProjectRepository = Depends(get_project_repository),
) -> IReleaseService:
    return CreateReleaseUseCase(
        release_repository=release_repo,
        project_repository=project_repo,
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
    return VerificationService(
        release_repository=release_repo,
        verification_repository=verification_repo,
        task_queue=task_queue,
    )


def get_auth_service(
    user_repo: SqlUserRepository = Depends(get_user_repository),
) -> IAuthService:
    jwt_handler = get_jwt_handler()
    password_hasher = get_password_hasher()
    return AuthService(
        user_repository=user_repo,
        token_service=jwt_handler,
        password_hasher=password_hasher,
    )


def get_organization_service(
    org_repo: SqlOrganizationRepository = Depends(get_organization_repository),
    project_repo: SqlProjectRepository = Depends(get_project_repository),
) -> IOrganizationService:
    return OrganizationService(
        organization_repository=org_repo,
        project_repository=project_repo,
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


def get_custom_role_service(
    role_repo: SqlCustomRoleRepository = Depends(get_custom_role_repository),
) -> ICustomRoleService:
    from application.use_cases.main.custom_role_service import CustomRoleService
    return CustomRoleService(custom_role_repository=role_repo)
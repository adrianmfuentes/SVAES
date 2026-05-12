from functools import lru_cache
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.user import User
from domain.entities.enums import UserRole
from domain.ports.i_password_hasher import IPasswordHasher
from domain.ports.i_token_service import ITokenService
from domain.ports.i_credential_encryptor import ICredentialEncryptor

from infrastructure.config import settings
from infrastructure.database.session import get_db_session
from infrastructure.security.password_hasher import BcryptPasswordHasher
from infrastructure.security.jwt_handler import JwtHandler
from infrastructure.security.credential_encryptor import FernetCredentialEncryptor
from domain.ports.i_task_queue import ITaskQueue
from domain.ports.i_credential_encryptor import ICredentialEncryptor
from infrastructure.adapters.connector_registry import ConnectorRegistry
from infrastructure.security.mock_task_queue import MockTaskQueue

from infrastructure.database.repositories.release_repository import SqlReleaseRepository
from infrastructure.database.repositories.connector_repository import SqlConnectorRepository
from infrastructure.database.repositories.user_repository import SqlUserRepository
from infrastructure.database.repositories.organization_repository import SqlOrganizationRepository
from infrastructure.database.repositories.profile_repository import SqlProfileRepository
from infrastructure.database.repositories.project_repository import SqlProjectRepository
from infrastructure.database.repositories.artifact_repository import SqlArtifactRepository
from infrastructure.database.repositories.verification_result_repository import SqlVerificationResultRepository
from infrastructure.database.repositories.verification_rule_repository import SqlVerificationRuleRepository

from application.use_cases.launch_verification import LaunchVerificationUseCase
from application.use_cases.configure_connector import ConfigureConnectorUseCase
from application.use_cases.auth_use_cases import LoginUseCase
from application.use_cases.organization_use_cases import (
    CreateOrganizationUseCase,
    GetOrganizationUseCase,
    ListOrganizationsUseCase,
    UpdateOrganizationUseCase,
    DeleteOrganizationUseCase,
)
from application.use_cases.manage_profile import ManageProfileUseCase
from application.use_cases.project_use_cases import (
    CreateProjectUseCase,
    GetProjectUseCase,
    ListProjectsUseCase,
    UpdateProjectUseCase,
    DeleteProjectUseCase,
)
from application.use_cases.create_release import (
    CreateReleaseUseCase,
    GetReleaseUseCase,
    ListReleasesUseCase,
    UpdateReleaseUseCase,
    DeleteReleaseUseCase,
)
from application.use_cases.get_verification_history import GetVerificationHistoryUseCase
from application.use_cases.user_use_cases import (
    RegisterUserUseCase,
    CreateUserUseCase,
    ChangePasswordUseCase,
    GetUserUseCase,
    ListUsersUseCase,
    UpdateUserUseCase,
    DeleteUserUseCase,
)
from application.use_cases.verification_rule_use_cases import (
    CreateRuleUseCase,
    ListRulesUseCase,
    GetRuleUseCase,
    UpdateRuleUseCase,
    DeleteRuleUseCase,
)

_bearer_scheme = HTTPBearer()

# ---------------------------------------------------------------------------
# Security service factories — stateless, safe to recreate per request
# ---------------------------------------------------------------------------
def get_password_hasher() -> IPasswordHasher:
    return BcryptPasswordHasher()

def get_jwt_handler() -> JwtHandler:
    return JwtHandler(
        secret=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expire_minutes=settings.jwt_expire_minutes,
    )

def get_credential_encryptor() -> ICredentialEncryptor:
    return FernetCredentialEncryptor(key=settings.encryption_key)

@lru_cache(maxsize=1)
def get_connector_registry() -> ConnectorRegistry:
    return ConnectorRegistry()

# ---------------------------------------------------------------------------
# Repository factories — must be defined before get_current_user
# ---------------------------------------------------------------------------
def get_release_repository(session: AsyncSession = Depends(get_db_session)) -> SqlReleaseRepository:
    return SqlReleaseRepository(session)

def get_connector_repository(session: AsyncSession = Depends(get_db_session)) -> SqlConnectorRepository:
    return SqlConnectorRepository(session)

def get_user_repository(session: AsyncSession = Depends(get_db_session)) -> SqlUserRepository:
    return SqlUserRepository(session)

def get_organization_repository(session: AsyncSession = Depends(get_db_session)) -> SqlOrganizationRepository:
    return SqlOrganizationRepository(session)

def get_profile_repository(session: AsyncSession = Depends(get_db_session)) -> SqlProfileRepository:
    return SqlProfileRepository(session)

def get_project_repository(session: AsyncSession = Depends(get_db_session)) -> SqlProjectRepository:
    return SqlProjectRepository(session)

def get_artifact_repository(session: AsyncSession = Depends(get_db_session)) -> SqlArtifactRepository:
    return SqlArtifactRepository(session)

def get_verification_result_repository(session: AsyncSession = Depends(get_db_session)) -> SqlVerificationResultRepository:
    return SqlVerificationResultRepository(session)

def get_verification_rule_repository(session: AsyncSession = Depends(get_db_session)) -> SqlVerificationRuleRepository:
    return SqlVerificationRuleRepository(session)

# ---------------------------------------------------------------------------
# Auth guard — inject into any protected endpoint
# ---------------------------------------------------------------------------
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    user_repo: SqlUserRepository = Depends(get_user_repository),
    jwt_handler: JwtHandler = Depends(get_jwt_handler),
) -> User:
    """Validates the Bearer token and returns the authenticated User entity.

    Raises HTTP 401 on missing, expired, or invalid tokens.
    """
    try:
        payload = jwt_handler.decode_token(credentials.credentials)
        user_id = UUID(payload["sub"])
    except (InvalidTokenError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.organization_id is not None:
        from infrastructure.database.session import set_current_organization_id
        set_current_organization_id(user.organization_id)
    return user

# ---------------------------------------------------------------------------
# Use case factories
# ---------------------------------------------------------------------------
def get_login_use_case(
    user_repo: SqlUserRepository = Depends(get_user_repository),
    password_hasher: IPasswordHasher = Depends(get_password_hasher),
    token_service: ITokenService = Depends(get_jwt_handler),
) -> LoginUseCase:
    return LoginUseCase(
        user_repo=user_repo,
        password_hasher=password_hasher,
        token_service=token_service,
    )

def get_create_organization_use_case(
    org_repo: SqlOrganizationRepository = Depends(get_organization_repository),
) -> CreateOrganizationUseCase:
    return CreateOrganizationUseCase(org_repo=org_repo)

def get_list_organizations_use_case(
    org_repo: SqlOrganizationRepository = Depends(get_organization_repository),
) -> ListOrganizationsUseCase:
    return ListOrganizationsUseCase(org_repo=org_repo)

def get_manage_profile_use_case(
    profile_repo: SqlProfileRepository = Depends(get_profile_repository),
) -> ManageProfileUseCase:
    return ManageProfileUseCase(profile_repo=profile_repo)

def get_create_project_use_case(
    project_repo: SqlProjectRepository = Depends(get_project_repository),
) -> CreateProjectUseCase:
    return CreateProjectUseCase(project_repo=project_repo)

def get_create_release_use_case(
    release_repo: SqlReleaseRepository = Depends(get_release_repository),
    org_repo: SqlOrganizationRepository = Depends(get_organization_repository),
) -> CreateReleaseUseCase:
    return CreateReleaseUseCase(release_repo=release_repo, organization_repo=org_repo)

def get_verification_history_use_case(
    release_repo: SqlReleaseRepository = Depends(get_release_repository),
    verification_result_repo: SqlVerificationResultRepository = Depends(get_verification_result_repository),
) -> GetVerificationHistoryUseCase:
    return GetVerificationHistoryUseCase(
        release_repo=release_repo,
        verification_result_repo=verification_result_repo,
    )

def get_task_queue() -> ITaskQueue:
    try:
        from infrastructure.queue import CeleryTaskQueue
        return CeleryTaskQueue()
    except Exception:
        return MockTaskQueue()

def get_launch_verification_use_case(
    release_repo: SqlReleaseRepository = Depends(get_release_repository),
) -> LaunchVerificationUseCase:
    return LaunchVerificationUseCase(release_repo=release_repo, task_queue=get_task_queue())

def get_configure_connector_use_case(
    repo: SqlConnectorRepository = Depends(get_connector_repository),
    registry: ConnectorRegistry = Depends(get_connector_registry),
    encryptor: ICredentialEncryptor = Depends(get_credential_encryptor),
) -> ConfigureConnectorUseCase:
    return ConfigureConnectorUseCase(
        connector_repo=repo,
        connector_registry=registry,
        credential_encryptor=encryptor,
    )

# ---------------------------------------------------------------------------
# RBAC — place after get_current_user so the closure can reference it
# ---------------------------------------------------------------------------
_ROLE_LEVELS: dict[UserRole, int] = {
    UserRole.VIEWER: 0,
    UserRole.OPERATOR: 1,
    UserRole.MANAGER: 2,
    UserRole.ADMIN: 3,
}


def require_min_role(min_role: UserRole) -> Depends:
    def _guard(current_user: User = Depends(get_current_user)) -> User:
        if _ROLE_LEVELS[current_user.role] < _ROLE_LEVELS[min_role]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    return Depends(_guard)

# ---------------------------------------------------------------------------
# New use case factories
# ---------------------------------------------------------------------------
def get_get_organization_use_case(
    org_repo: SqlOrganizationRepository = Depends(get_organization_repository),
) -> GetOrganizationUseCase:
    return GetOrganizationUseCase(org_repo=org_repo)

def get_update_organization_use_case(
    org_repo: SqlOrganizationRepository = Depends(get_organization_repository),
) -> UpdateOrganizationUseCase:
    return UpdateOrganizationUseCase(org_repo=org_repo)

def get_delete_organization_use_case(
    org_repo: SqlOrganizationRepository = Depends(get_organization_repository),
) -> DeleteOrganizationUseCase:
    return DeleteOrganizationUseCase(org_repo=org_repo)

def get_get_project_use_case(
    project_repo: SqlProjectRepository = Depends(get_project_repository),
) -> GetProjectUseCase:
    return GetProjectUseCase(project_repo=project_repo)

def get_list_projects_use_case(
    project_repo: SqlProjectRepository = Depends(get_project_repository),
) -> ListProjectsUseCase:
    return ListProjectsUseCase(project_repo=project_repo)

def get_update_project_use_case(
    project_repo: SqlProjectRepository = Depends(get_project_repository),
) -> UpdateProjectUseCase:
    return UpdateProjectUseCase(project_repo=project_repo)

def get_delete_project_use_case(
    project_repo: SqlProjectRepository = Depends(get_project_repository),
) -> DeleteProjectUseCase:
    return DeleteProjectUseCase(project_repo=project_repo)

def get_get_release_use_case(
    release_repo: SqlReleaseRepository = Depends(get_release_repository),
) -> GetReleaseUseCase:
    return GetReleaseUseCase(release_repo=release_repo)

def get_list_releases_use_case(
    release_repo: SqlReleaseRepository = Depends(get_release_repository),
) -> ListReleasesUseCase:
    return ListReleasesUseCase(release_repo=release_repo)

def get_update_release_use_case(
    release_repo: SqlReleaseRepository = Depends(get_release_repository),
) -> UpdateReleaseUseCase:
    return UpdateReleaseUseCase(release_repo=release_repo)

def get_delete_release_use_case(
    release_repo: SqlReleaseRepository = Depends(get_release_repository),
) -> DeleteReleaseUseCase:
    return DeleteReleaseUseCase(release_repo=release_repo)

def get_register_use_case(
    user_repo: SqlUserRepository = Depends(get_user_repository),
    password_hasher: IPasswordHasher = Depends(get_password_hasher),
    token_service: ITokenService = Depends(get_jwt_handler),
) -> RegisterUserUseCase:
    return RegisterUserUseCase(
        user_repo=user_repo,
        password_hasher=password_hasher,
        token_service=token_service,
    )

def get_create_user_use_case(
    user_repo: SqlUserRepository = Depends(get_user_repository),
    password_hasher: IPasswordHasher = Depends(get_password_hasher),
) -> CreateUserUseCase:
    return CreateUserUseCase(user_repo=user_repo, password_hasher=password_hasher)

def get_get_user_use_case(
    user_repo: SqlUserRepository = Depends(get_user_repository),
) -> GetUserUseCase:
    return GetUserUseCase(user_repo=user_repo)

def get_list_users_use_case(
    user_repo: SqlUserRepository = Depends(get_user_repository),
) -> ListUsersUseCase:
    return ListUsersUseCase(user_repo=user_repo)

def get_update_user_use_case(
    user_repo: SqlUserRepository = Depends(get_user_repository),
) -> UpdateUserUseCase:
    return UpdateUserUseCase(user_repo=user_repo)

def get_delete_user_use_case(
    user_repo: SqlUserRepository = Depends(get_user_repository),
) -> DeleteUserUseCase:
    return DeleteUserUseCase(user_repo=user_repo)

def get_change_password_use_case(
    user_repo: SqlUserRepository = Depends(get_user_repository),
    password_hasher: IPasswordHasher = Depends(get_password_hasher),
) -> ChangePasswordUseCase:
    return ChangePasswordUseCase(user_repo=user_repo, password_hasher=password_hasher)

def get_create_rule_use_case(
    rule_repo: SqlVerificationRuleRepository = Depends(get_verification_rule_repository),
    profile_repo: SqlProfileRepository = Depends(get_profile_repository),
) -> CreateRuleUseCase:
    return CreateRuleUseCase(rule_repo=rule_repo, profile_repo=profile_repo)

def get_list_rules_use_case(
    rule_repo: SqlVerificationRuleRepository = Depends(get_verification_rule_repository),
    profile_repo: SqlProfileRepository = Depends(get_profile_repository),
) -> ListRulesUseCase:
    return ListRulesUseCase(rule_repo=rule_repo, profile_repo=profile_repo)

def get_get_rule_use_case(
    rule_repo: SqlVerificationRuleRepository = Depends(get_verification_rule_repository),
) -> GetRuleUseCase:
    return GetRuleUseCase(rule_repo=rule_repo)

def get_update_rule_use_case(
    rule_repo: SqlVerificationRuleRepository = Depends(get_verification_rule_repository),
) -> UpdateRuleUseCase:
    return UpdateRuleUseCase(rule_repo=rule_repo)

def get_delete_rule_use_case(
    rule_repo: SqlVerificationRuleRepository = Depends(get_verification_rule_repository),
) -> DeleteRuleUseCase:
    return DeleteRuleUseCase(rule_repo=rule_repo)

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.user import User
from domain.ports.i_password_hasher import IPasswordHasher
from domain.ports.i_token_service import ITokenService
from domain.ports.i_credential_encryptor import ICredentialEncryptor

from infrastructure.config import settings
from infrastructure.database.session import get_db_session
from infrastructure.security.password_hasher import BcryptPasswordHasher
from infrastructure.security.jwt_handler import JwtHandler
from infrastructure.security.credential_encryptor import FernetCredentialEncryptor
from infrastructure.security.mock_task_queue import MockTaskQueue
from infrastructure.adapters.connector_registry import ConnectorRegistry

from infrastructure.database.repositories.release_repository import SqlReleaseRepository
from infrastructure.database.repositories.connector_repository import SqlConnectorRepository
from infrastructure.database.repositories.user_repository import SqlUserRepository
from infrastructure.database.repositories.organization_repository import SqlOrganizationRepository
from infrastructure.database.repositories.profile_repository import SqlProfileRepository
from infrastructure.database.repositories.project_repository import SqlProjectRepository

from application.use_cases.launch_verification import LaunchVerificationUseCase
from application.use_cases.configure_connector import ConfigureConnectorUseCase
from application.use_cases.auth_use_cases import LoginUseCase
from application.use_cases.organization_use_cases import CreateOrganizationUseCase, ListOrganizationsUseCase
from application.use_cases.manage_profile import ManageProfileUseCase
from application.use_cases.project_use_cases import CreateProjectUseCase
from application.use_cases.create_release import CreateReleaseUseCase
from application.use_cases.get_verification_history import GetVerificationHistoryUseCase

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
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )
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
) -> GetVerificationHistoryUseCase:
    return GetVerificationHistoryUseCase(release_repo=release_repo)


def get_launch_verification_use_case(
    release_repo: SqlReleaseRepository = Depends(get_release_repository),
) -> LaunchVerificationUseCase:
    return LaunchVerificationUseCase(release_repo=release_repo, task_queue=MockTaskQueue())


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

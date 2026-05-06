import uuid
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from infrastructure.database.session import get_db_session

from infrastructure.database.repositories.release_repository import SqlReleaseRepository
from infrastructure.database.repositories.connector_repository import SqlConnectorRepository
from infrastructure.database.repositories.user_repository import SqlUserRepository
from infrastructure.database.repositories.organization_repository import SqlOrganizationRepository
from infrastructure.database.repositories.profile_repository import SqlProfileRepository
from infrastructure.database.repositories.project_repository import SqlProjectRepository

from infrastructure.adapters.connector_registry import ConnectorRegistry

from domain.ports.i_task_queue import ITaskQueue

from application.use_cases.launch_verification import LaunchVerificationUseCase
from application.use_cases.configure_connector import ConfigureConnectorUseCase
from application.use_cases.auth_use_cases import LoginUseCase
from application.use_cases.organization_use_cases import CreateOrganizationUseCase, ListOrganizationsUseCase
from application.use_cases.manage_profile import ManageProfileUseCase
from application.use_cases.project_use_cases import CreateProjectUseCase
from application.use_cases.create_release import CreateReleaseUseCase
from application.use_cases.get_verification_history import GetVerificationHistoryUseCase


class MockTaskQueue(ITaskQueue):
    """Development stub for ITaskQueue.

    Returns random UUIDs as task IDs without real queueing. Replace with a
    Celery/ARQ/Redis Streams implementation before connecting the verification engine.
    """

    async def enqueue_verification_task(self, release_id: uuid.UUID) -> str:
        return str(uuid.uuid4())

    async def get_task_status(self, task_id: str) -> str:
        return "PENDING"


# --- Repository factories ---

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


# --- Singleton-like factories ---
def get_task_queue() -> MockTaskQueue:
    return MockTaskQueue()

def get_connector_registry() -> ConnectorRegistry:
    return ConnectorRegistry()


# --- Use case factories ---
def get_login_use_case(
    user_repo: SqlUserRepository = Depends(get_user_repository),
) -> LoginUseCase:
    return LoginUseCase(user_repo=user_repo)

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
    task_queue: MockTaskQueue = Depends(get_task_queue),
) -> LaunchVerificationUseCase:
    return LaunchVerificationUseCase(release_repo=release_repo, task_queue=task_queue)

def get_configure_connector_use_case(
    repo: SqlConnectorRepository = Depends(get_connector_repository),
    registry: ConnectorRegistry = Depends(get_connector_registry),
) -> ConfigureConnectorUseCase:
    return ConfigureConnectorUseCase(connector_repo=repo, connector_registry=registry)
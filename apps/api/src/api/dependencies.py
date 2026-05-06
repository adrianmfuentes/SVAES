import uuid
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from infrastructure.database.session import get_db_session
from infrastructure.database.repositories.release_repository import SqlReleaseRepository
from domain.ports.i_task_queue import ITaskQueue
from application.use_cases.launch_verification import LaunchVerificationUseCase
from infrastructure.database.repositories.connector_repository import SqlConnectorRepository
from infrastructure.adapters.connector_registry import ConnectorRegistry
from application.use_cases.configure_connector import ConfigureConnectorUseCase

class MockTaskQueue(ITaskQueue):
    async def enqueue_verification_task(self, release_id: uuid.UUID) -> str:
        return str(uuid.uuid4())

    async def get_task_status(self, task_id: str) -> str:
        return "PENDING"


def get_release_repository(session: AsyncSession = Depends(get_db_session)) -> SqlReleaseRepository:
    return SqlReleaseRepository(session)


def get_task_queue() -> MockTaskQueue:
    return MockTaskQueue()


def get_launch_verification_use_case(
    release_repo: SqlReleaseRepository = Depends(get_release_repository),
    task_queue: MockTaskQueue = Depends(get_task_queue),
) -> LaunchVerificationUseCase:
    return LaunchVerificationUseCase(release_repo=release_repo, task_queue=task_queue)

def get_connector_repository(session: AsyncSession = Depends(get_db_session)) -> SqlConnectorRepository:
    return SqlConnectorRepository(session)

def get_connector_registry() -> ConnectorRegistry:
    return ConnectorRegistry()

def get_configure_connector_use_case(
    repo: SqlConnectorRepository = Depends(get_connector_repository),
    registry: ConnectorRegistry = Depends(get_connector_registry)
) -> ConfigureConnectorUseCase:
    return ConfigureConnectorUseCase(connector_repo=repo, connector_registry=registry)
import uuid
from dataclasses import dataclass
from typing import List

from domain.entities.release import Release
from domain.entities.enums import ReleaseStatus
from domain.exceptions import EntityNotFoundError, ReleaseInvalidStateError
from domain.ports.i_release_repository import IReleaseRepository
from domain.ports.i_organization_repository import IOrganizationRepository
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CreateReleaseCommand:
    project_id: uuid.UUID
    profile_id: uuid.UUID
    version: str
    created_by: uuid.UUID
    description: str = ""


@dataclass
class UpdateReleaseCommand:
    release_id: uuid.UUID
    description: str | None = None


class CreateReleaseUseCase:
    def __init__(
        self,
        release_repo: IReleaseRepository,
        organization_repo: IOrganizationRepository,
    ):
        self.release_repo = release_repo
        self.organization_repo = organization_repo

    async def execute(self, command: CreateReleaseCommand) -> Release:
        new_release = Release(
            project_id=command.project_id,
            profile_id=command.profile_id,
            version=command.version,
            created_by=command.created_by,
            description=command.description,
            status=ReleaseStatus.BORRADOR,
        )
        logger.info(
            "Creating release: project=%s version=%s by=%s",
            command.project_id, command.version, command.created_by,
        )
        return await self.release_repo.create(new_release)


class GetReleaseUseCase:
    def __init__(self, release_repo: IReleaseRepository):
        self.release_repo = release_repo

    async def execute(self, release_id: uuid.UUID) -> Release:
        release = await self.release_repo.get_by_id(release_id)
        if not release:
            raise EntityNotFoundError(f"Release {release_id} not found")
        return release


class ListReleasesUseCase:
    def __init__(self, release_repo: IReleaseRepository):
        self.release_repo = release_repo

    async def execute(self, project_id: uuid.UUID, skip: int = 0, limit: int = 50) -> List[Release]:
        return await self.release_repo.list_by_project(project_id, skip=skip, limit=limit)


class UpdateReleaseUseCase:
    def __init__(self, release_repo: IReleaseRepository):
        self.release_repo = release_repo

    async def execute(self, command: UpdateReleaseCommand) -> Release:
        release = await self.release_repo.get_by_id(command.release_id)
        if not release:
            raise EntityNotFoundError(f"Release {command.release_id} not found")
        if release.status != ReleaseStatus.BORRADOR:
            raise ReleaseInvalidStateError(command.release_id, release.status.value, ReleaseStatus.BORRADOR.value)

        if command.description is not None:
            release.description = command.description

        return await self.release_repo.update(release)


class DeleteReleaseUseCase:
    def __init__(self, release_repo: IReleaseRepository):
        self.release_repo = release_repo

    async def execute(self, release_id: uuid.UUID) -> None:
        release = await self.release_repo.get_by_id(release_id)
        if not release:
            raise EntityNotFoundError(f"Release {release_id} not found")
        if release.status != ReleaseStatus.BORRADOR:
            raise ReleaseInvalidStateError(release_id, release.status.value, ReleaseStatus.BORRADOR.value)
        await self.release_repo.delete(release_id)

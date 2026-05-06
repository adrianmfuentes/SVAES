import uuid
from dataclasses import dataclass
from domain.entities.release import Release
from domain.entities.enums import ReleaseStatus
from domain.ports.i_release_repository import IReleaseRepository
from domain.ports.i_organization_repository import IOrganizationRepository

@dataclass
class CreateReleaseCommand:
    project_id: uuid.UUID
    profile_id: uuid.UUID
    version: str
    created_by: uuid.UUID
    description: str = ""

class CreateReleaseUseCase:
    def __init__(
        self,
        release_repo: IReleaseRepository,
        organization_repo: IOrganizationRepository,
    ):
        self.release_repo = release_repo
        self.organization_repo = organization_repo

    async def execute(self, command: CreateReleaseCommand) -> Release:
        nueva_release = Release(
            project_id=command.project_id,
            profile_id=command.profile_id,
            version=command.version,
            created_by=command.created_by,
            description=command.description,
            status=ReleaseStatus.BORRADOR,
        )
        return await self.release_repo.create(nueva_release)

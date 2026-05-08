import uuid
from dataclasses import dataclass
from domain.entities.release import Release
from domain.entities.enums import ReleaseStatus
from domain.ports.i_release_repository import IReleaseRepository
from domain.ports.i_organization_repository import IOrganizationRepository
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

@dataclass
class CreateReleaseCommand:
    """Command object for creating a new release."""
    project_id: uuid.UUID
    profile_id: uuid.UUID
    version: str
    created_by: uuid.UUID
    description: str = ""

class CreateReleaseUseCase:
    """Use case for creating a new release for a project profile.

    Attributes:
        release_repo (IReleaseRepository): Repository for managing release entities.
        organization_repo (IOrganizationRepository): Repository for managing organization entities.

    Logs:
        - Info: Creation of a new release with project, profile, version, and creator details
    """

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

        logger.info("Creating new release: project_id=%s, profile_id=%s, version=%s, created_by=%s",
                    command.project_id, command.profile_id, command.version, command.created_by)
        return await self.release_repo.create(new_release)

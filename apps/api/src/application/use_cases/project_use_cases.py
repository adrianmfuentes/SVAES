from dataclasses import dataclass
import uuid
from domain.ports.i_project_repository import IProjectRepository
from domain.entities.project import Project

@dataclass
class CreateProjectCommand:
    """Command object for creating a new project within an organization."""
    organization_id: uuid.UUID
    name: str
    description: str = ""

class CreateProjectUseCase:
    """Use case for creating a new project within an organization.

    Attributes:
        project_repo (IProjectRepository): Repository for managing project entities.
    """

    def __init__(self, project_repo: IProjectRepository):
        self.project_repo = project_repo

    async def execute(self, command: CreateProjectCommand) -> Project:
        project = Project(
            organization_id=command.organization_id,
            name=command.name,
            description=command.description,
        )
        return await self.project_repo.create(project)

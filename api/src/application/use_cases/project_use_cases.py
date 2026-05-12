import uuid
from dataclasses import dataclass
from typing import List

from domain.entities.project import Project
from domain.exceptions import EntityNotFoundError
from domain.ports.i_project_repository import IProjectRepository


@dataclass
class CreateProjectCommand:
    organization_id: uuid.UUID
    name: str
    description: str = ""


@dataclass
class UpdateProjectCommand:
    project_id: uuid.UUID
    name: str | None = None
    description: str | None = None


class CreateProjectUseCase:
    def __init__(self, project_repo: IProjectRepository):
        self.project_repo = project_repo

    async def execute(self, command: CreateProjectCommand) -> Project:
        project = Project(
            organization_id=command.organization_id,
            name=command.name,
            description=command.description,
        )
        return await self.project_repo.create(project)


class GetProjectUseCase:
    def __init__(self, project_repo: IProjectRepository):
        self.project_repo = project_repo

    async def execute(self, project_id: uuid.UUID) -> Project:
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise EntityNotFoundError(f"Project {project_id} not found")
        return project


class ListProjectsUseCase:
    def __init__(self, project_repo: IProjectRepository):
        self.project_repo = project_repo

    async def execute(self, organization_id: uuid.UUID, skip: int = 0, limit: int = 50) -> List[Project]:
        return await self.project_repo.list_by_organization(organization_id, skip=skip, limit=limit)


class UpdateProjectUseCase:
    def __init__(self, project_repo: IProjectRepository):
        self.project_repo = project_repo

    async def execute(self, command: UpdateProjectCommand) -> Project:
        project = await self.project_repo.get_by_id(command.project_id)
        if not project:
            raise EntityNotFoundError(f"Project {command.project_id} not found")

        if command.name is not None:
            project.name = command.name
        if command.description is not None:
            project.description = command.description

        return await self.project_repo.update(project)


class DeleteProjectUseCase:
    def __init__(self, project_repo: IProjectRepository):
        self.project_repo = project_repo

    async def execute(self, project_id: uuid.UUID) -> None:
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise EntityNotFoundError(f"Project {project_id} not found")
        await self.project_repo.delete(project_id)

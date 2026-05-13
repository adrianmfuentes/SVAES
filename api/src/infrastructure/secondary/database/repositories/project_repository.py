from uuid import UUID
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from domain.entities.project import Project
from domain.ports.i_project_repository import IProjectRepository
from api.src.infrastructure.secondary.database.models.project import ProjectModel


class SqlProjectRepository(IProjectRepository):
    """Async SQLAlchemy adapter for IProjectRepository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, project: Project) -> Project:
        model = ProjectModel(
            id=project.id,
            organization_id=project.organization_id,
            name=project.name,
            description=project.description,
        )
        self.session.add(model)
        await self.session.flush()
        return project

    async def get_by_id(self, project_id: UUID) -> Optional[Project]:
        model = await self.session.get(ProjectModel, project_id)
        return self._to_entity(model) if model else None

    async def list_by_organization(self, organization_id: UUID, skip: int = 0, limit: int = 50) -> List[Project]:
        result = await self.session.execute(
            select(ProjectModel).where(ProjectModel.organization_id == organization_id)
            .offset(skip).limit(limit)
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def update(self, project: Project) -> Project:
        model = await self.session.get(ProjectModel, project.id)
        if model:
            model.name = project.name
            model.description = project.description
            await self.session.flush()
        return project

    async def delete(self, project_id: UUID) -> None:
        model = await self.session.get(ProjectModel, project_id)
        if model:
            await self.session.delete(model)
            await self.session.flush()

    def _to_entity(self, model: ProjectModel) -> Project:
        return Project(
            id=model.id,
            organization_id=model.organization_id,
            name=model.name,
            description=model.description or "",
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

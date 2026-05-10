from typing import Optional, List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from domain.entities.release import Release, ReleaseStatus
from domain.ports.i_release_repository import IReleaseRepository
from infrastructure.database.models.release import ReleaseModel


class SqlReleaseRepository(IReleaseRepository):
    """Async SQLAlchemy adapter for IReleaseRepository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, release: Release) -> Release:
        model = ReleaseModel(
            id=release.id,
            project_id=release.project_id,
            profile_id=release.profile_id,
            version=release.version,
            created_by=release.created_by,
            status=release.status.value,
            description=release.description,
        )
        self.session.add(model)
        await self.session.flush()
        return release

    async def get_by_id(self, release_id: UUID) -> Optional[Release]:
        model = await self.session.get(ReleaseModel, release_id)
        return self._to_entity(model) if model else None

    async def list_by_project(self, project_id: UUID) -> List[Release]:
        result = await self.session.execute(
            select(ReleaseModel).where(ReleaseModel.project_id == project_id)
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def update(self, release: Release) -> Release:
        model = await self.session.get(ReleaseModel, release.id)
        if model:
            model.status = release.status.value
            model.description = release.description
            await self.session.flush()
        return release

    async def delete(self, release_id: UUID) -> None:
        model = await self.session.get(ReleaseModel, release_id)
        if model:
            await self.session.delete(model)
            await self.session.flush()

    def _to_entity(self, model: ReleaseModel) -> Release:
        return Release(
            id=model.id,
            project_id=model.project_id,
            profile_id=model.profile_id,
            version=model.version,
            created_by=model.created_by,
            status=ReleaseStatus(model.status),
            description=model.description,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

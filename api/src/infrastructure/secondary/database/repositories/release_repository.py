from application.ports.output.i_release_repository import IReleaseRepository
from domain.entities.release import Release
from domain.enums import ReleaseStatus
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from infrastructure.secondary.database.models import ReleaseModel
from infrastructure.secondary.database import get_async_session
import uuid
from infrastructure.secondary.database.get_async_session import get_async_session
from typing import Optional
from infrastructure.secondary.database.models.project_model import ProjectModel
from contextlib import asynccontextmanager

"""
Repositorio para las operaciones relacionadas con la entidad Release en base de datos.
Este repositorio implementa la interfaz IReleaseRepository, el cual es un puerto de salida para operaciones de persistencia de releases.
"""
class SqlReleaseRepository(IReleaseRepository):

    @asynccontextmanager
    async def _get_session(self):
        session = await get_async_session().__anext__()
        try:
            yield session
        finally:
            await session.close()

    def _release_from_row(self, row) -> Release:
        return Release(
            id=uuid.UUID(str(row.id)),
            name=str(row.name),
            version=str(row.version),
            project_id=uuid.UUID(str(row.project_id)),
            status=ReleaseStatus(row.status),
            profile_id=uuid.UUID(str(row.profile_id)),
            created_by=uuid.UUID(str(row.created_by))
        )

    async def create(self, release: Release) -> None:
        async with self._get_session() as session:
            try:
                release_model = ReleaseModel(
                    id=release.id,
                    name=release.name,
                    version=release.version,
                    project_id=release.project_id,
                    status=release.status,
                    profile_id=uuid.UUID(str(getattr(release, 'profile_id'))) if getattr(release, 'profile_id', None) is not None else None,
                    created_by=getattr(release, 'created_by', None)
                )
                session.add(release_model)
                await session.commit()
                await session.refresh(release_model)
            except IntegrityError:
                await session.rollback()
                raise


    async def get_by_id(self, release_id: uuid.UUID) -> Optional[Release]:
        async with self._get_session() as session:
            try:
                result = await session.execute(select(ReleaseModel).where(ReleaseModel.id == release_id))
                release_row = result.scalar_one_or_none()
                if not release_row:
                    return None
                return self._release_from_row(release_row)
            except IntegrityError:
                await session.rollback()
                raise


    async def list_by_project(
        self, project_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> list[Release]:
        async with self._get_session() as session:
            result = await session.execute(
                select(ReleaseModel)
                .where(ReleaseModel.project_id == project_id)
                .offset(skip)
                .limit(limit)
            )
            release_rows = result.scalars().all()
            return [self._release_from_row(row) for row in release_rows]


    async def list_by_organization(
        self, organization_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> list[Release]:
        async with self._get_session() as session:
            result = await session.execute(
                select(ReleaseModel)
                .join(ProjectModel, ReleaseModel.project_id == ProjectModel.id)
                .where(ProjectModel.organization_id == organization_id)
                .offset(skip)
                .limit(limit)
            )
            release_rows = result.scalars().all()
            return [self._release_from_row(row) for row in release_rows]


    async def update(self, release: Release) -> Release:
        async with self._get_session() as session:
            result = await session.execute(select(ReleaseModel).where(ReleaseModel.id == release.id))
            release_row = result.scalar_one_or_none()
            if not release_row:
                raise EntityNotFoundError("Release no encontrado")

            setattr(release_row, "name", str(release.name))
            setattr(release_row, "version", str(release.version))
            setattr(release_row, "status", str(release.status))
            setattr(release_row, "profile_id", uuid.UUID(str(getattr(release, "profile_id"))))
            setattr(release_row, "created_by", uuid.UUID(str(getattr(release, "created_by"))))

            await session.commit()
            await session.refresh(release_row)
            return self._release_from_row(release_row)


    async def update_status(
        self, release_id: uuid.UUID, status: ReleaseStatus
    ) -> Optional[Release]:
        async with self._get_session() as session:
            result = await session.execute(select(ReleaseModel).where(ReleaseModel.id == release_id))
            release_row = result.scalar_one_or_none()
            if not release_row:
                return None

            setattr(release_row, "status", str(status))

            await session.commit()
            await session.refresh(release_row)
            return self._release_from_row(release_row)


    async def delete(self, release_id: uuid.UUID) -> None:
        async with self._get_session() as session:
            result = await session.execute(select(ReleaseModel).where(ReleaseModel.id == release_id))
            release_row = result.scalar_one_or_none()
            if not release_row:
                raise EntityNotFoundError("Release no encontrado")

            await session.delete(release_row)
            await session.commit()


    async def get_artifact_by_id(self, artifact_id: uuid.UUID):
        async with self._get_session() as session:
            result = await session.execute(
                select(ReleaseModel).where(ReleaseModel.artifacts.any(id=artifact_id))
            )
            release_row = result.scalar_one_or_none()
            if not release_row:
                return None

            artifact = next((a for a in release_row.artifacts if a.id == artifact_id), None)
            return artifact


    async def delete_artifact(self, artifact_id: uuid.UUID) -> None:
        async with self._get_session() as session:
            result = await session.execute(
                select(ReleaseModel).where(ReleaseModel.artifacts.any(id=artifact_id))
            )
            release_row = result.scalar_one_or_none()
            if not release_row:
                raise EntityNotFoundError("Artifact no encontrado")

            artifact = next((a for a in release_row.artifacts if a.id == artifact_id), None)
            if artifact:
                release_row.artifacts.remove(artifact)
                await session.commit()
from sqlalchemy.future import select
from typing import Optional, cast
import uuid, sys
from datetime import datetime
from pathlib import Path
from application.ports.output.i_project_repository import IProjectRepository
from domain.entities.project import Project
from infrastructure.secondary.database.models.project_model import ProjectModel
from infrastructure.secondary.database.get_async_session import get_async_session

# Agregar el directorio raíz del proyecto al sys.path para permitir importaciones relativas
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

"""
Repositorio para las operaciones relacionadas con la entidad Project en base de datos.
Este repositorio implementa la interfaz IProjectRepository, el cual es un puerto de salida para operaciones de persistencia de proyectos.
"""
class SqlProjectRepository(IProjectRepository):
    async def create(self, project: Project) -> Project:
        session = await get_async_session().__anext__() # Obtener una sesión de base de datos
        
        try:
            project_model = ProjectModel(
                id=project.id,
                name=project.name,
                description=project.description,
                organization_id=project.organization_id,
                profile_id=project.profile_id,
                is_archived=project.is_archived,
                created_at=project.created_at,
                updated_at=project.updated_at
            )
            session.add(project_model)
            await session.commit()
            await session.refresh(project_model)

            return Project(
                id=cast(uuid.UUID, project_model.id),
                name=cast(str, project_model.name),
                description=cast(str, project_model.description),
                organization_id=cast(uuid.UUID, project_model.organization_id),
                profile_id=cast(uuid.UUID, project_model.profile_id),
                created_at=cast(datetime, project_model.created_at),
                updated_at=cast(datetime, project_model.updated_at)
            )
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()


    async def get_by_id(self, project_id: uuid.UUID) -> Optional[Project]:
        session = await get_async_session().__anext__()
        
        try:
            result = await session.execute(select(ProjectModel).where(ProjectModel.id == project_id))
            project_row = result.scalar_one_or_none()
            if not project_row:
                return None
            
            return Project(
                id=cast(uuid.UUID, project_row.id),
                name=cast(str, project_row.name),
                description=cast(str, project_row.description),
                organization_id=cast(uuid.UUID, project_row.organization_id),
                profile_id=cast(uuid.UUID, project_row.profile_id),
                is_archived=cast(bool, project_row.is_archived),
                created_at=cast(datetime, project_row.created_at),
                updated_at=cast(datetime, project_row.updated_at)
            )
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()


    async def list_by_organization(self, organization_id: uuid.UUID, skip: int = 0, limit: int = 50) -> list[Project]:
        session = await get_async_session().__anext__()
        
        try:
            result = await session.execute(
                select(ProjectModel)
                .where(ProjectModel.organization_id == organization_id)
                .offset(skip)
                .limit(limit)
            )
            project_rows = result.scalars().all()
            
            return [
                Project(
                    id=cast(uuid.UUID, row.id),
                    name=cast(str, row.name),
                    description=cast(str, row.description),
                    organization_id=cast(uuid.UUID, row.organization_id),
                    profile_id=cast(uuid.UUID, row.profile_id),
                    is_archived=cast(bool, row.is_archived),
                    created_at=cast(datetime, row.created_at),
                    updated_at=cast(datetime, row.updated_at)
                )
                for row in project_rows
            ]
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()


    async def update(self, project: Project) -> Project:
        session = await get_async_session().__anext__()
        
        try:
            project_model = await session.get(ProjectModel, project.id)
            if not project_model:
                raise ValueError("Project not found")

            setattr(project_model, "name", project.name)
            setattr(project_model, "description", project.description)
            setattr(project_model, "organization_id", project.organization_id)
            setattr(project_model, "profile_id", project.profile_id)
            setattr(project_model, "is_archived", project.is_archived)
            setattr(project_model, "updated_at", datetime.now(datetime.timezone.utc))

            await session.commit()
            await session.refresh(project_model)

            return Project(
                id=cast(uuid.UUID, project_model.id),
                name=cast(str, project_model.name),
                description=cast(str, project_model.description),
                organization_id=cast(uuid.UUID, project_model.organization_id),
                profile_id=cast(uuid.UUID, project_model.profile_id),
                is_archived=cast(bool, project_model.is_archived),
                created_at=cast(datetime, project_model.created_at),
                updated_at=cast(datetime, project_model.updated_at)
            )
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()


    async def delete(self, project_id: uuid.UUID) -> None:
        session = await get_async_session().__anext__()
        
        try:
            project_model = await session.get(ProjectModel, project_id)
            if not project_model:
                raise ValueError("Project not found")

            await session.delete(project_model)
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

from sqlalchemy.future import select
from typing import Optional, List, cast
import uuid
from datetime import datetime
from application.ports.output.i_template_repository import ITemplateRepository
from domain.entities.template import Template
from infrastructure.secondary.database.models.template_model import TemplateModel
from infrastructure.secondary.database.get_async_session import AsyncSessionLocal


class SqlTemplateRepository(ITemplateRepository):
    def _model_to_entity(self, row: TemplateModel) -> Template:
        return Template(
            id=cast(uuid.UUID, row.id),
            organization_id=cast(uuid.UUID, row.organization_id),
            name=cast(str, row.name),
            description=cast(str, row.description) or "",
            profile_id=cast(uuid.UUID, row.profile_id),
            created_by=cast(uuid.UUID, row.created_by),
            project_name_template=cast(str | None, row.project_name_template),
            is_archived=cast(bool, row.is_archived),
            created_at=cast(datetime, row.created_at),
            updated_at=cast(datetime, row.updated_at),
        )

    async def create(self, template: Template) -> Template:
        async with AsyncSessionLocal() as session:
            model = TemplateModel(
                id=template.id,
                organization_id=template.organization_id,
                name=template.name,
                description=template.description,
                profile_id=template.profile_id,
                created_by=template.created_by,
                project_name_template=template.project_name_template,
                is_archived=template.is_archived,
                created_at=template.created_at,
                updated_at=template.updated_at,
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)

            return self._model_to_entity(model)

    async def get_by_id(self, template_id: uuid.UUID) -> Optional[Template]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(TemplateModel).where(TemplateModel.id == template_id))
            row = result.scalar_one_or_none()
            if not row:
                return None

            return self._model_to_entity(row)

    async def list_by_organization(self, organization_id: uuid.UUID, skip: int = 0, limit: int = 50, include_archived: bool = False) -> List[Template]:
        async with AsyncSessionLocal() as session:
            stmt = select(TemplateModel).where(TemplateModel.organization_id == organization_id)
            if not include_archived:
                stmt = stmt.where(TemplateModel.is_archived == False)
            stmt = stmt.offset(skip).limit(limit)
            result = await session.execute(stmt)
            rows = result.scalars().all()

            return [self._model_to_entity(row) for row in rows]

    async def update(self, template: Template) -> Template:
        async with AsyncSessionLocal() as session:
            model = await session.get(TemplateModel, template.id)
            if not model:
                raise ValueError("Template not found")

            model.name = template.name  # pyright: ignore[reportAttributeAccessIssue]
            model.description = template.description  # pyright: ignore[reportAttributeAccessIssue]
            model.profile_id = template.profile_id  # pyright: ignore[reportAttributeAccessIssue]
            model.project_name_template = template.project_name_template  # pyright: ignore[reportAttributeAccessIssue]
            model.is_archived = template.is_archived  # pyright: ignore[reportAttributeAccessIssue]
            model.updated_at = datetime.now(datetime.timezone.utc)

            await session.commit()
            await session.refresh(model)

            return self._model_to_entity(model)

    async def delete(self, template_id: uuid.UUID) -> None:
        async with AsyncSessionLocal() as session:
            model = await session.get(TemplateModel, template_id)
            if not model:
                raise ValueError("Template not found")

            await session.delete(model)
            await session.commit()

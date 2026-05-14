from typing import Optional, List
from uuid import UUID, uuid4
from application.ports.input.i_template_service import ITemplateService
from application.ports.output.i_template_repository import ITemplateRepository
from application.ports.output.i_profile_repository import IProfileRepository
from domain.entities.template import Template
from domain.exceptions import EntityNotFoundError, DuplicateEntityError, ValidationError
from core.audit import AuditEntry, AuditEvent, get_audit_logger
from core.logger import get_logger

_log = get_logger(__name__)


class TemplateService(ITemplateService):
    def __init__(self, template_repository: ITemplateRepository, profile_repository: IProfileRepository) -> None:
        self._template_repo = template_repository
        self._profile_repo = profile_repository

    async def create_template(
        self,
        name: str,
        description: str,
        profile_id: UUID,
        created_by: UUID,
        organization_id: UUID,
        project_name_template: Optional[str] = None,
    ):
        existing = await self._template_repo.list_by_organization(organization_id, limit=1000)
        if any(t.name == name and not t.is_archived for t in existing):
            raise DuplicateEntityError(f"Ya existe una plantilla con el nombre: {name}")

        profile = await self._profile_repo.get_by_id(profile_id)
        if not profile:
            raise EntityNotFoundError(f"Perfil no encontrado: {profile_id}")

        template = Template(
            organization_id=organization_id,
            name=name,
            description=description,
            profile_id=profile_id,
            created_by=created_by,
            project_name_template=project_name_template,
        )
        created = await self._template_repo.create(template)

        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.TEMPLATE_CREATED,
            user_id=created_by,
            organization_id=organization_id,
            resource_type="template",
            resource_id=created.id,
            details={"name": name, "profile_id": str(profile_id)},
        ))
        _log.info("Template created: by=%s org=%s name=%s", created_by, organization_id, name)

        return created

    async def list_templates(
        self,
        organization_id: UUID,
        skip: int = 0,
        limit: int = 50,
        include_archived: bool = False,
    ):
        return await self._template_repo.list_by_organization(
            organization_id=organization_id,
            skip=skip,
            limit=limit,
            include_archived=include_archived,
        )

    async def get_template(self, template_id: UUID):
        return await self._template_repo.get_by_id(template_id)

    async def update_template(
        self,
        template_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_archived: Optional[bool] = None,
    ):
        template = await self._template_repo.get_by_id(template_id)
        if not template:
            raise EntityNotFoundError(f"Plantilla no encontrada: {template_id}")

        if name is not None:
            template.name = name
        if description is not None:
            template.description = description
        if is_archived is not None:
            template.is_archived = is_archived

        updated = await self._template_repo.update(template)

        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.TEMPLATE_UPDATED,
            user_id=template.created_by,
            organization_id=template.organization_id,
            resource_type="template",
            resource_id=template_id,
            details={"name": template.name},
        ))
        _log.info("Template updated: id=%s org=%s", template_id, template.organization_id)

        return updated

    async def archive_template(self, template_id: UUID):
        template = await self._template_repo.get_by_id(template_id)
        if not template:
            raise EntityNotFoundError(f"Plantilla no encontrada: {template_id}")

        template.is_archived = True
        await self._template_repo.update(template)

        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.TEMPLATE_ARCHIVED,
            user_id=template.created_by,
            organization_id=template.organization_id,
            resource_type="template",
            resource_id=template_id,
            details={"name": template.name},
        ))
        _log.info("Template archived: id=%s org=%s", template_id, template.organization_id)

    async def clone_template(
        self,
        template_id: UUID,
        new_name: str,
        target_organization_id: UUID,
        requested_by: UUID,
    ):
        original = await self._template_repo.get_by_id(template_id)
        if not original:
            raise EntityNotFoundError(f"Plantilla no encontrada: {template_id}")

        existing = await self._template_repo.list_by_organization(target_organization_id, limit=1000)
        if any(t.name == new_name and not t.is_archived for t in existing):
            raise DuplicateEntityError(f"Ya existe una plantilla con el nombre: {new_name}")

        cloned = Template(
            organization_id=target_organization_id,
            name=new_name,
            description=original.description,
            profile_id=original.profile_id,
            created_by=requested_by,
            project_name_template=original.project_name_template,
        )
        created = await self._template_repo.create(cloned)

        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.TEMPLATE_CLONED,
            user_id=requested_by,
            organization_id=target_organization_id,
            resource_type="template",
            resource_id=created.id,
            details={"original_id": str(template_id), "new_name": new_name},
        ))
        _log.info("Template cloned: by=%s from=%s to=%s org=%s", requested_by, template_id, created.id, target_organization_id)

        return created

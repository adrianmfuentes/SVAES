from typing import List, Optional
from uuid import UUID
from application.ports.input.i_organization_service import IOrganizationService
from application.ports.output.i_organization_repository import IOrganizationRepository
from application.ports.output.i_project_repository import IProjectRepository
from application.ports.output.i_user_repository import IUserRepository
from domain.entities.organization import Organization
from domain.entities.project import Project
from domain.enums import UserRole
from domain.exceptions import DuplicateEntityError, EntityNotFoundError, ValidationError
from core.audit import AuditEntry, AuditEvent, get_audit_logger
from core.logger import get_logger

_log = get_logger(__name__)


class OrganizationService(IOrganizationService):
    def __init__(
        self,
        organization_repository: IOrganizationRepository,
        project_repository: IProjectRepository,
        user_repository: Optional[IUserRepository] = None,
    ) -> None:
        self._org_repo = organization_repository
        self._project_repo = project_repository
        self._user_repo = user_repository


    async def create_organization(
        self,
        name: str,
        slug: str,
        owner_id: Optional[UUID] = None,
    ) -> Organization:
        existing = await self._org_repo.get_by_slug(slug)
        if existing:
            raise DuplicateEntityError(f"Ya existe una organización con slug: {slug}")

        if owner_id and self._user_repo:
            owner = await self._user_repo.get_by_id(owner_id)
            if owner and owner.role == UserRole.U3:
                raise ValidationError("El administrador global no puede ser propietario de una organización.")

        org = Organization(name=name, slug=slug, owner_id=owner_id)
        created_org = await self._org_repo.create(org)

        if owner_id and self._user_repo:
            if owner:
                owner.organization_id = created_org.id
                await self._user_repo.update(owner)

        return created_org


    async def get_organization(self, organization_id: UUID) -> Optional[Organization]:
        return await self._org_repo.get_by_id(organization_id)


    async def list_organizations(
        self,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = True,
    ) -> List[Organization]:
        return await self._org_repo.list_all(active_only=active_only, skip=skip, limit=limit)


    async def create_project(
        self,
        organization_id: UUID,
        name: str,
        description: str,
        profile_id: UUID,
    ) -> Project:
        org = await self._org_repo.get_by_id(organization_id)
        if not org:
            raise EntityNotFoundError(f"Organización no encontrada: {organization_id}")

        project = Project(
            organization_id=organization_id,
            name=name,
            description=description,
            profile_id=profile_id,
        )
        return await self._project_repo.create(project)


    async def list_projects(
        self,
        organization_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Project]:
        return await self._project_repo.list_by_organization(organization_id, skip=skip, limit=limit)


    async def get_project(self, project_id: UUID) -> Optional[Project]:
        return await self._project_repo.get_by_id(project_id)


    async def archive_project(self, project_id: UUID) -> Project:
        project = await self._project_repo.get_by_id(project_id)
        if not project:
            raise EntityNotFoundError(f"Proyecto no encontrado: {project_id}")

        project.is_archived = True
        updated = await self._project_repo.update(project)

        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.PROJECT_ARCHIVED,
            user_id=project.organization_id,
            organization_id=project.organization_id,
            resource_type="project",
            resource_id=project_id,
            details={"name": project.name},
        ))
        _log.info("Project archived: id=%s org=%s", project_id, project.organization_id)

        return updated


    async def transfer_ownership(
        self,
        organization_id: UUID,
        new_owner_id: UUID,
        requested_by: UUID,
    ) -> Organization:
        org = await self._org_repo.get_by_id(organization_id)
        if not org:
            raise EntityNotFoundError(f"Organización no encontrada: {organization_id}")

        if self._user_repo:
            new_owner = await self._user_repo.get_by_id(new_owner_id)
            if new_owner and new_owner.role == UserRole.U3:
                raise ValidationError("El administrador global no puede ser propietario de una organización.")

        old_owner = org.owner_id
        org.owner_id = new_owner_id
        updated = await self._org_repo.update(org)

        audit = get_audit_logger()
        audit.log(AuditEntry(
            event=AuditEvent.ORG_OWNERSHIP_TRANSFERRED,
            user_id=requested_by,
            organization_id=organization_id,
            resource_type="organization",
            resource_id=organization_id,
            details={"old_owner": str(old_owner), "new_owner": str(new_owner_id)},
        ))
        _log.info("Org ownership transferred: by=%s org=%s %s->%s", requested_by, organization_id, old_owner, new_owner_id)

        return updated

    async def list_accessible_projects(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Project]:
        orgs = await self._org_repo.list_all(active_only=True, skip=0, limit=1000)
        projects: List[Project] = []
        for org in orgs:
            org_projects = await self._project_repo.list_by_organization(org.id, skip=0, limit=1000)
            projects.extend(org_projects)
        return projects[skip : skip + limit]

    async def restore_organization(self, organization_id: UUID) -> Organization:
        org = await self._org_repo.get_by_id(organization_id)
        if not org:
            raise EntityNotFoundError(f"Organización no encontrada: {organization_id}")

        org.is_active = True
        updated = await self._org_repo.update(org)
        _log.info("Organization restored: id=%s", organization_id)

        return updated
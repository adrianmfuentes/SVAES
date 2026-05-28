import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from application.use_cases.main.organization_service import OrganizationService
from domain.entities.organization import Organization
from domain.entities.project import Project
from domain.exceptions import DuplicateEntityError, EntityNotFoundError, ValidationError


@pytest.fixture
def mock_audit_logger():
    logger = MagicMock()
    logger.log = MagicMock()
    return logger


@pytest.fixture
def org_repo():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.get_by_slug = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    repo.update = AsyncMock()
    repo.list_all = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def project_repo():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    repo.update = AsyncMock()
    repo.list_by_organization = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def user_repo():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.update = AsyncMock()
    return repo


@pytest.fixture
def service(org_repo, project_repo, user_repo, mock_audit_logger):
    with patch(
        "application.use_cases.main.organization_service.get_audit_logger",
        return_value=mock_audit_logger,
    ):
        yield OrganizationService(org_repo, project_repo, user_repo)


@pytest.fixture
def sample_org():
    return Organization(
        name="Test Org",
        slug="test-org",
        owner_id=uuid4(),
        plan="default",
    )


@pytest.fixture
def sample_project():
    project = Project(
        organization_id=uuid4(),
        name="Test Project",
        description="A test project",
        profile_id=uuid4(),
    )
    return project


pytestmark = pytest.mark.unit


class TestCreateOrganization:
    async def test_create_organization_success(self, service, org_repo, sample_org):
        """Verifica la creación exitosa de una organización con slug único y datos válidos."""
        org_repo.get_by_slug.return_value = None
        org_repo.create.return_value = sample_org

        result = await service.create_organization(
            name=sample_org.name,
            slug=sample_org.slug,
            plan=sample_org.plan,
            owner_id=None,
        )

        assert result.name == sample_org.name
        assert result.slug == sample_org.slug
        assert result.plan == sample_org.plan
        org_repo.get_by_slug.assert_called_once_with(sample_org.slug)
        org_repo.create.assert_called_once()

    async def test_create_organization_duplicate_slug(self, service, org_repo, sample_org):
        """Verifica que se lance DuplicateEntityError cuando el slug ya existe."""
        org_repo.get_by_slug.return_value = sample_org

        with pytest.raises(DuplicateEntityError, match="slug"):
            await service.create_organization(
                name=sample_org.name,
                slug=sample_org.slug,
                plan=sample_org.plan,
            )

        org_repo.create.assert_not_called()

    async def test_create_organization_with_owner(self, service, org_repo, user_repo, sample_org):
        """Verifica que al crear una organización con owner_id se asocie al usuario correctamente."""
        owner_id = uuid4()
        sample_org.owner_id = owner_id
        org_repo.get_by_slug.return_value = None
        org_repo.create.return_value = sample_org

        owner = MagicMock()
        owner.organization_id = None
        owner.id = owner_id
        user_repo.get_by_id.return_value = owner

        result = await service.create_organization(
            name=sample_org.name,
            slug=sample_org.slug,
            plan=sample_org.plan,
            owner_id=owner_id,
        )

        assert result.owner_id == owner_id
        user_repo.get_by_id.assert_called_once_with(owner_id)
        assert owner.organization_id == sample_org.id
        user_repo.update.assert_called_once_with(owner)

    async def test_create_organization_owner_not_found(self, service, org_repo, user_repo, sample_org):
        """Verifica que no falle cuando el owner_id se especifica pero el usuario no existe."""
        owner_id = uuid4()
        org_repo.get_by_slug.return_value = None
        org_repo.create.return_value = sample_org
        user_repo.get_by_id.return_value = None

        result = await service.create_organization(
            name=sample_org.name,
            slug=sample_org.slug,
            plan=sample_org.plan,
            owner_id=owner_id,
        )

        assert result is not None
        user_repo.get_by_id.assert_called_once_with(owner_id)
        user_repo.update.assert_not_called()

    async def test_create_organization_without_user_repo(self, org_repo, project_repo, mock_audit_logger, sample_org):
        """Verifica que se pueda crear una organización sin que se proporcione un user_repository."""
        with patch(
            "application.use_cases.main.organization_service.get_audit_logger",
            return_value=mock_audit_logger,
        ):
            service_no_user = OrganizationService(org_repo, project_repo, user_repository=None)

            org_repo.get_by_slug.return_value = None
            org_repo.create.return_value = sample_org

            result = await service_no_user.create_organization(
                name=sample_org.name,
                slug=sample_org.slug,
                plan=sample_org.plan,
                owner_id=uuid4(),
            )

            assert result.name == sample_org.name
            org_repo.create.assert_called_once()


class TestGetOrganization:
    async def test_get_organization_found(self, service, org_repo, sample_org):
        """Verifica que al buscar una organización existente se retorne el objeto correcto."""
        org_repo.get_by_id.return_value = sample_org

        result = await service.get_organization(sample_org.id)

        assert result == sample_org
        org_repo.get_by_id.assert_called_once_with(sample_org.id)

    async def test_get_organization_not_found(self, service, org_repo):
        """Verifica que se retorne None cuando la organización solicitada no existe."""
        org_id = uuid4()

        result = await service.get_organization(org_id)

        assert result is None
        org_repo.get_by_id.assert_called_once_with(org_id)


class TestListOrganizations:
    async def test_list_organizations_returns_items(self, service, org_repo, sample_org):
        """Verifica que se listen correctamente las organizaciones cuando existen."""
        org_repo.list_all.return_value = [sample_org]

        result = await service.list_organizations()

        assert len(result) == 1
        assert result[0] == sample_org
        org_repo.list_all.assert_called_once_with(active_only=True, skip=0, limit=100)

    async def test_list_organizations_empty(self, service, org_repo):
        """Verifica que se retorne una lista vacía cuando no hay organizaciones."""
        org_repo.list_all.return_value = []

        result = await service.list_organizations()

        assert result == []
        org_repo.list_all.assert_called_once_with(active_only=True, skip=0, limit=100)

    async def test_list_organizations_with_pagination(self, service, org_repo):
        """Verifica que se respeten los parámetros skip y limit en la paginación."""
        await service.list_organizations(skip=10, limit=5, active_only=False)

        org_repo.list_all.assert_called_once_with(active_only=False, skip=10, limit=5)

    async def test_list_organizations_active_only(self, service, org_repo, sample_org):
        """Verifica que solo se listen las organizaciones activas por defecto."""
        org_repo.list_all.return_value = [sample_org]

        result = await service.list_organizations(active_only=True)

        assert len(result) == 1
        assert result[0] == sample_org
        org_repo.list_all.assert_called_once_with(active_only=True, skip=0, limit=100)


class TestCreateProject:
    async def test_create_project_success(self, service, org_repo, project_repo, sample_org, sample_project):
        """Verifica la creación exitosa de un proyecto dentro de una organización existente."""
        org_repo.get_by_id.return_value = sample_org
        sample_project.organization_id = sample_org.id
        project_repo.create.return_value = sample_project

        result = await service.create_project(
            organization_id=sample_org.id,
            name=sample_project.name,
            description=sample_project.description,
            profile_id=sample_project.profile_id,
        )

        assert result.name == sample_project.name
        assert result.organization_id == sample_org.id
        assert result.profile_id == sample_project.profile_id
        org_repo.get_by_id.assert_called_once_with(sample_org.id)
        project_repo.create.assert_called_once()

    async def test_create_project_org_not_found(self, service, org_repo, project_repo):
        """Verifica que se lance EntityNotFoundError cuando la organización no existe."""
        org_repo.get_by_id.return_value = None
        org_id = uuid4()

        with pytest.raises(EntityNotFoundError, match="Organización"):
            await service.create_project(
                organization_id=org_id,
                name="Test",
                description="Desc",
                profile_id=uuid4(),
            )

        project_repo.create.assert_not_called()


class TestListProjects:
    async def test_list_projects_returns_items(self, service, project_repo, sample_project):
        """Verifica que se listen correctamente los proyectos de una organización."""
        project_repo.list_by_organization.return_value = [sample_project]
        org_id = sample_project.organization_id

        result = await service.list_projects(org_id)

        assert len(result) == 1
        assert result[0] == sample_project
        project_repo.list_by_organization.assert_called_once_with(org_id, skip=0, limit=50)

    async def test_list_projects_empty(self, service, project_repo):
        """Verifica que se retorne una lista vacía cuando la organización no tiene proyectos."""
        org_id = uuid4()
        project_repo.list_by_organization.return_value = []

        result = await service.list_projects(org_id)

        assert result == []
        project_repo.list_by_organization.assert_called_once_with(org_id, skip=0, limit=50)

    async def test_list_projects_with_pagination(self, service, project_repo):
        """Verifica que se respeten los parámetros skip y limit en la paginación de proyectos."""
        org_id = uuid4()

        await service.list_projects(org_id, skip=10, limit=5)

        project_repo.list_by_organization.assert_called_once_with(org_id, skip=10, limit=5)


class TestGetProject:
    async def test_get_project_found(self, service, project_repo, sample_project):
        """Verifica que al buscar un proyecto existente se retorne el objeto correcto."""
        project_repo.get_by_id.return_value = sample_project

        result = await service.get_project(sample_project.id)

        assert result == sample_project
        project_repo.get_by_id.assert_called_once_with(sample_project.id)

    async def test_get_project_not_found(self, service, project_repo):
        """Verifica que se retorne None cuando el proyecto solicitado no existe."""
        project_id = uuid4()

        result = await service.get_project(project_id)

        assert result is None
        project_repo.get_by_id.assert_called_once_with(project_id)


class TestArchiveProject:
    async def test_archive_project_success(self, service, project_repo, sample_project, mock_audit_logger):
        """Verifica que se archive un proyecto correctamente y se registre la auditoría."""
        project_repo.get_by_id.return_value = sample_project
        project_repo.update.return_value = sample_project

        result = await service.archive_project(sample_project.id)

        assert result.is_archived is True
        project_repo.update.assert_called_once()
        mock_audit_logger.log.assert_called_once()

    async def test_archive_project_not_found(self, service, project_repo):
        """Verifica que se lance EntityNotFoundError al archivar un proyecto inexistente."""
        project_repo.get_by_id.return_value = None
        project_id = uuid4()

        with pytest.raises(EntityNotFoundError, match="Proyecto"):
            await service.archive_project(project_id)

        project_repo.update.assert_not_called()

    async def test_archive_project_already_archived(self, service, project_repo, sample_project, mock_audit_logger):
        """Verifica que archivar un proyecto ya archivado no cause errores."""
        sample_project.is_archived = True
        project_repo.get_by_id.return_value = sample_project
        project_repo.update.return_value = sample_project

        result = await service.archive_project(sample_project.id)

        assert result.is_archived is True
        project_repo.update.assert_called_once()
        mock_audit_logger.log.assert_called_once()


class TestTransferOwnership:
    async def test_transfer_ownership_success(self, service, org_repo, sample_org, mock_audit_logger):
        """Verifica que la transferencia de propiedad cambie correctamente el owner_id y se audite."""
        old_owner_id = sample_org.owner_id
        new_owner_id = uuid4()
        requested_by = uuid4()

        org_repo.get_by_id.return_value = sample_org
        org_repo.update.return_value = sample_org

        result = await service.transfer_ownership(
            organization_id=sample_org.id,
            new_owner_id=new_owner_id,
            requested_by=requested_by,
        )

        assert result.owner_id == new_owner_id
        org_repo.update.assert_called_once()
        mock_audit_logger.log.assert_called_once()

        audit_call = mock_audit_logger.log.call_args[0][0]
        assert str(old_owner_id) in audit_call.details["old_owner"]
        assert str(new_owner_id) in audit_call.details["new_owner"]

    async def test_transfer_ownership_org_not_found(self, service, org_repo):
        """Verifica que se lance EntityNotFoundError al transferir propiedad de una organización inexistente."""
        org_repo.get_by_id.return_value = None
        org_id = uuid4()

        with pytest.raises(EntityNotFoundError, match="Organización"):
            await service.transfer_ownership(
                organization_id=org_id,
                new_owner_id=uuid4(),
                requested_by=uuid4(),
            )

        org_repo.update.assert_not_called()


class TestListAccessibleProjects:
    async def test_list_accessible_projects_returns_items(
        self, service, org_repo, project_repo, sample_org, sample_project
    ):
        """Verifica que se listen todos los proyectos accesibles a través de las organizaciones activas."""
        org_repo.list_all.return_value = [sample_org]
        project_repo.list_by_organization.return_value = [sample_project]

        result = await service.list_accessible_projects(user_id=uuid4())

        assert len(result) == 1
        assert result[0] == sample_project
        org_repo.list_all.assert_called_once_with(active_only=True, skip=0, limit=1000)
        project_repo.list_by_organization.assert_called_once_with(
            sample_org.id, skip=0, limit=1000
        )

    async def test_list_accessible_projects_empty(self, service, org_repo, project_repo):
        """Verifica que se retorne una lista vacía cuando no hay organizaciones activas."""
        org_repo.list_all.return_value = []

        result = await service.list_accessible_projects(user_id=uuid4())

        assert result == []
        org_repo.list_all.assert_called_once()
        project_repo.list_by_organization.assert_not_called()

    async def test_list_accessible_projects_with_pagination(self, service, org_repo, project_repo, sample_org):
        """Verifica que se respeten los parámetros skip y limit en la paginación de proyectos accesibles."""
        projects = [
            Project(
                organization_id=sample_org.id,
                name=f"Project {i}",
                description=f"Desc {i}",
                profile_id=uuid4(),
            )
            for i in range(10)
        ]
        org_repo.list_all.return_value = [sample_org]
        project_repo.list_by_organization.return_value = projects

        result = await service.list_accessible_projects(
            user_id=uuid4(), skip=2, limit=3
        )

        assert len(result) == 3
        assert result[0].name == "Project 2"
        assert result[2].name == "Project 4"

    async def test_list_accessible_projects_multiple_orgs(
        self, service, org_repo, project_repo, sample_org
    ):
        """Verifica que se consoliden proyectos de múltiples organizaciones activas."""
        org2 = Organization(name="Org 2", slug="org-2")
        projects_org1 = [
            Project(
                organization_id=sample_org.id,
                name="P1",
                description="D1",
                profile_id=uuid4(),
            )
        ]
        projects_org2 = [
            Project(
                organization_id=org2.id,
                name="P2",
                description="D2",
                profile_id=uuid4(),
            ),
            Project(
                organization_id=org2.id,
                name="P3",
                description="D3",
                profile_id=uuid4(),
            ),
        ]

        org_repo.list_all.return_value = [sample_org, org2]
        project_repo.list_by_organization.side_effect = [projects_org1, projects_org2]

        result = await service.list_accessible_projects(user_id=uuid4())

        assert len(result) == 3
        assert result[0].name == "P1"
        assert result[1].name == "P2"
        assert result[2].name == "P3"


class TestRestoreOrganization:
    async def test_restore_organization_success(self, service, org_repo, sample_org):
        """Verifica la restauración exitosa de una organización inactiva a activa."""
        sample_org.is_active = False
        org_repo.get_by_id.return_value = sample_org
        org_repo.update.return_value = sample_org

        result = await service.restore_organization(sample_org.id)

        assert result.is_active is True
        org_repo.update.assert_called_once()

    async def test_restore_organization_not_found(self, service, org_repo):
        """Verifica que se lance EntityNotFoundError al restaurar una organización inexistente."""
        org_repo.get_by_id.return_value = None
        org_id = uuid4()

        with pytest.raises(EntityNotFoundError, match="Organización"):
            await service.restore_organization(org_id)

        org_repo.update.assert_not_called()

    async def test_restore_organization_already_active(self, service, org_repo, sample_org):
        """Verifica que restaurar una organización ya activa no cause errores."""
        sample_org.is_active = True
        org_repo.get_by_id.return_value = sample_org
        org_repo.update.return_value = sample_org

        result = await service.restore_organization(sample_org.id)

        assert result.is_active is True
        org_repo.update.assert_called_once()

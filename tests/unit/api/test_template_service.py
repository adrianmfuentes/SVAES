import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from application.use_cases.main.template_service import TemplateService
from domain.entities.template import Template
from domain.entities.verification_profile import VerificationProfile
from domain.exceptions import EntityNotFoundError, DuplicateEntityError

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_audit_logger():
    logger = MagicMock()
    logger.log = MagicMock()
    return logger


@pytest.fixture
def template_repo():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock()
    repo.list_by_organization = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def profile_repo():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def service(template_repo, profile_repo, mock_audit_logger):
    with patch(
        "application.use_cases.main.template_service.get_audit_logger",
        return_value=mock_audit_logger,
    ):
        yield TemplateService(template_repo, profile_repo)


@pytest.fixture
def sample_template():
    return Template(
        id=uuid4(),
        organization_id=uuid4(),
        name="Test Template",
        description="A test template",
        profile_id=uuid4(),
        created_by=uuid4(),
        project_name_template="PROJ-{name}",
        is_archived=False,
    )


@pytest.fixture
def sample_profile():
    return VerificationProfile(
        id=uuid4(),
        organization_id=uuid4(),
        name="Test Profile",
        description="A test profile",
        is_default=False,
        rules=[],
    )


class TestCreateTemplate:
    async def test_create_template_success(self, service, template_repo, profile_repo, sample_profile):
        """Verifica la creación exitosa de una plantilla."""
        org_id = uuid4()
        user_id = uuid4()
        profile_repo.get_by_id.return_value = sample_profile
        template_repo.list_by_organization.return_value = []
        created = Template(
            id=uuid4(),
            organization_id=org_id,
            name="My Template",
            description="Desc",
            profile_id=sample_profile.id,
            created_by=user_id,
            project_name_template="T-{name}",
        )
        template_repo.create.return_value = created

        result = await service.create_template(
            name="My Template",
            description="Desc",
            profile_id=sample_profile.id,
            created_by=user_id,
            organization_id=org_id,
            project_name_template="T-{name}",
        )

        assert result.name == "My Template"
        assert result.organization_id == org_id
        assert result.profile_id == sample_profile.id
        assert result.created_by == user_id
        assert result.project_name_template == "T-{name}"
        template_repo.create.assert_called_once()

    async def test_create_template_duplicate_name(self, service, template_repo, profile_repo, sample_profile):
        """Verifica que se lance DuplicateEntityError cuando el nombre ya existe."""
        org_id = uuid4()
        profile_repo.get_by_id.return_value = sample_profile
        existing = Template(
            id=uuid4(),
            organization_id=org_id,
            name="Duplicate",
            description="",
            profile_id=sample_profile.id,
            created_by=uuid4(),
            is_archived=False,
        )
        template_repo.list_by_organization.return_value = [existing]

        with pytest.raises(DuplicateEntityError, match="Ya existe una plantilla"):
            await service.create_template(
                name="Duplicate",
                description="",
                profile_id=sample_profile.id,
                created_by=uuid4(),
                organization_id=org_id,
            )

    async def test_create_template_duplicate_ignores_archived(self, service, template_repo, profile_repo, sample_profile):
        """Verifica que los nombres duplicados de plantillas archivadas se ignoren."""
        org_id = uuid4()
        profile_repo.get_by_id.return_value = sample_profile
        archived = Template(
            id=uuid4(),
            organization_id=org_id,
            name="My Template",
            description="",
            profile_id=sample_profile.id,
            created_by=uuid4(),
            is_archived=True,
        )
        template_repo.list_by_organization.return_value = [archived]
        created = Template(
            id=uuid4(),
            organization_id=org_id,
            name="My Template",
            description="",
            profile_id=sample_profile.id,
            created_by=uuid4(),
            project_name_template=None,
        )
        template_repo.create.return_value = created

        result = await service.create_template(
            name="My Template",
            description="",
            profile_id=sample_profile.id,
            created_by=uuid4(),
            organization_id=org_id,
        )

        assert result.name == "My Template"

    async def test_create_template_profile_not_found(self, service, template_repo, profile_repo):
        """Verifica que se lance EntityNotFoundError cuando el perfil no existe."""
        profile_repo.get_by_id.return_value = None
        template_repo.list_by_organization.return_value = []

        with pytest.raises(EntityNotFoundError, match="Perfil no encontrado"):
            await service.create_template(
                name="Test",
                description="",
                profile_id=uuid4(),
                created_by=uuid4(),
                organization_id=uuid4(),
            )

    async def test_create_template_without_project_name_template(self, service, template_repo, profile_repo, sample_profile):
        """Verifica la creación sin project_name_template (None por defecto)."""
        org_id = uuid4()
        profile_repo.get_by_id.return_value = sample_profile
        template_repo.list_by_organization.return_value = []
        created = Template(
            id=uuid4(),
            organization_id=org_id,
            name="Simple",
            description="",
            profile_id=sample_profile.id,
            created_by=uuid4(),
            project_name_template=None,
        )
        template_repo.create.return_value = created

        result = await service.create_template(
            name="Simple",
            description="",
            profile_id=sample_profile.id,
            created_by=uuid4(),
            organization_id=org_id,
        )

        assert result.project_name_template is None


class TestListTemplates:
    async def test_list_templates(self, service, sample_template, template_repo):
        """Verifica que se listen las plantillas de la organización."""
        template_repo.list_by_organization.return_value = [sample_template]

        result = await service.list_templates(sample_template.organization_id)

        assert result == [sample_template]
        template_repo.list_by_organization.assert_called_once_with(
            organization_id=sample_template.organization_id,
            skip=0,
            limit=50,
            include_archived=False,
        )

    async def test_list_templates_with_pagination(self, service, template_repo):
        """Verifica que se respeten los parámetros de paginación."""
        org_id = uuid4()

        await service.list_templates(org_id, skip=10, limit=5, include_archived=True)

        template_repo.list_by_organization.assert_called_once_with(
            organization_id=org_id,
            skip=10,
            limit=5,
            include_archived=True,
        )


class TestGetTemplate:
    async def test_get_template_found(self, service, sample_template, template_repo):
        """Verifica que se retorne la plantilla correcta."""
        template_repo.get_by_id.return_value = sample_template

        result = await service.get_template(sample_template.id)

        assert result == sample_template
        template_repo.get_by_id.assert_called_once_with(sample_template.id)

    async def test_get_template_not_found(self, service, template_repo):
        """Verifica que se retorne None cuando la plantilla no existe."""
        result = await service.get_template(uuid4())
        assert result is None


class TestUpdateTemplate:
    async def test_update_template_all_fields(self, service, sample_template, template_repo):
        """Verifica la actualización exitosa de todos los campos."""
        template_repo.get_by_id.return_value = sample_template
        template_repo.update.return_value = sample_template

        result = await service.update_template(
            template_id=sample_template.id,
            name="Updated Name",
            description="Updated Desc",
            is_archived=True,
        )

        assert result.name == "Updated Name"
        assert result.description == "Updated Desc"
        assert result.is_archived is True
        template_repo.update.assert_called_once_with(sample_template)

    async def test_update_template_name_only(self, service, sample_template, template_repo):
        """Verifica que solo se actualice el nombre."""
        template_repo.get_by_id.return_value = sample_template
        template_repo.update.return_value = sample_template

        result = await service.update_template(
            template_id=sample_template.id,
            name="New Name",
        )

        assert result.name == "New Name"

    async def test_update_template_not_found(self, service, template_repo):
        """Verifica que se lance EntityNotFoundError si la plantilla no existe."""
        template_repo.get_by_id.return_value = None

        with pytest.raises(EntityNotFoundError, match="Plantilla no encontrada"):
            await service.update_template(template_id=uuid4(), name="Test")

    async def test_update_template_none_does_not_change(self, service, sample_template, template_repo):
        """Verifica que pasar None no modifique los campos."""
        template_repo.get_by_id.return_value = sample_template
        template_repo.update.return_value = sample_template
        original_name = sample_template.name
        original_description = sample_template.description
        original_is_archived = sample_template.is_archived

        result = await service.update_template(
            template_id=sample_template.id,
            name=None,
            description=None,
            is_archived=None,
        )

        assert result.name == original_name
        assert result.description == original_description
        assert result.is_archived == original_is_archived


class TestArchiveTemplate:
    async def test_archive_template(self, service, sample_template, template_repo):
        """Verifica que se archive correctamente una plantilla."""
        template_repo.get_by_id.return_value = sample_template

        await service.archive_template(sample_template.id)

        assert sample_template.is_archived is True
        template_repo.update.assert_called_once_with(sample_template)

    async def test_archive_template_not_found(self, service, template_repo):
        """Verifica que se lance EntityNotFoundError si la plantilla no existe."""
        template_repo.get_by_id.return_value = None

        with pytest.raises(EntityNotFoundError, match="Plantilla no encontrada"):
            await service.archive_template(uuid4())


class TestCloneTemplate:
    async def test_clone_template_success(self, service, template_repo, sample_template, profile_repo):
        """Verifica el clonado exitoso de una plantilla."""
        template_repo.get_by_id.return_value = sample_template
        template_repo.list_by_organization.return_value = []
        new_org_id = uuid4()
        user_id = uuid4()
        cloned = Template(
            id=uuid4(),
            organization_id=new_org_id,
            name="Cloned Template",
            description=sample_template.description,
            profile_id=sample_template.profile_id,
            created_by=user_id,
            project_name_template=sample_template.project_name_template,
        )
        template_repo.create.return_value = cloned

        result = await service.clone_template(
            template_id=sample_template.id,
            new_name="Cloned Template",
            target_organization_id=new_org_id,
            requested_by=user_id,
        )

        assert result.name == "Cloned Template"
        assert result.organization_id == new_org_id
        assert result.created_by == user_id
        assert result.profile_id == sample_template.profile_id
        assert result.description == sample_template.description
        assert result.project_name_template == sample_template.project_name_template
        template_repo.create.assert_called_once()

    async def test_clone_template_original_not_found(self, service, template_repo):
        """Verifica que se lance EntityNotFoundError si la plantilla original no existe."""
        template_repo.get_by_id.return_value = None

        with pytest.raises(EntityNotFoundError, match="Plantilla no encontrada"):
            await service.clone_template(
                template_id=uuid4(),
                new_name="Clone",
                target_organization_id=uuid4(),
                requested_by=uuid4(),
            )

    async def test_clone_template_duplicate_name(self, service, template_repo, sample_template):
        """Verifica que se lance DuplicateEntityError si el nombre ya existe."""
        template_repo.get_by_id.return_value = sample_template
        new_org_id = uuid4()
        existing = Template(
            id=uuid4(),
            organization_id=new_org_id,
            name="Duplicate",
            description="",
            profile_id=uuid4(),
            created_by=uuid4(),
            is_archived=False,
        )
        template_repo.list_by_organization.return_value = [existing]

        with pytest.raises(DuplicateEntityError, match="Ya existe una plantilla"):
            await service.clone_template(
                template_id=sample_template.id,
                new_name="Duplicate",
                target_organization_id=new_org_id,
                requested_by=uuid4(),
            )

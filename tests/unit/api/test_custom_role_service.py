import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from application.use_cases.main.custom_role_service import CustomRoleService
from domain.entities.custom_role import CustomRole
from domain.enums import Permission
from domain.exceptions import EntityNotFoundError, DuplicateEntityError, ValidationError

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_audit_logger():
    logger = MagicMock()
    logger.log = MagicMock()
    return logger


@pytest.fixture
def role_repo():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock()
    repo.list_by_organization = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def service(role_repo, mock_audit_logger):
    with patch(
        "application.use_cases.main.custom_role_service.get_audit_logger",
        return_value=mock_audit_logger,
    ):
        yield CustomRoleService(role_repo)


@pytest.fixture
def sample_role():
    return CustomRole(
        id=uuid4(),
        organization_id=uuid4(),
        name="Admin Role",
        permissions=[Permission.CREATE_RELEASE, Permission.VIEW_DASHBOARD],
        is_active=True,
    )


class TestCreateRole:
    async def test_create_role_success(self, service, role_repo):
        """Verifica la creación exitosa de un rol personalizado."""
        org_id = uuid4()
        user_id = uuid4()
        created = CustomRole(
            id=uuid4(),
            organization_id=org_id,
            name="Test Role",
            permissions=[Permission.CREATE_RELEASE],
            is_active=True,
        )
        role_repo.create.return_value = created
        role_repo.list_by_organization.return_value = []

        result = await service.create_role(
            organization_id=org_id,
            name="Test Role",
            permissions=[Permission.CREATE_RELEASE],
            requested_by=user_id,
        )

        assert result.name == "Test Role"
        assert result.organization_id == org_id
        assert result.permissions == [Permission.CREATE_RELEASE]
        role_repo.create.assert_called_once()
        role_repo.list_by_organization.assert_called_once_with(org_id)

    async def test_create_role_duplicate_name(self, service, role_repo):
        """Verifica que se lance DuplicateEntityError cuando el nombre ya existe."""
        org_id = uuid4()
        existing_role = CustomRole(
            id=uuid4(),
            organization_id=org_id,
            name="Duplicate",
            permissions=[Permission.VIEW_DASHBOARD],
        )
        role_repo.list_by_organization.return_value = [existing_role]

        with pytest.raises(DuplicateEntityError, match="Ya existe un rol"):
            await service.create_role(
                organization_id=org_id,
                name="Duplicate",
                permissions=[Permission.CREATE_RELEASE],
                requested_by=uuid4(),
            )

    async def test_create_role_empty_permissions(self, service, role_repo):
        """Verifica que se lance ValidationError cuando no hay permisos."""
        org_id = uuid4()
        role_repo.list_by_organization.return_value = []

        with pytest.raises(ValidationError, match="al menos un permiso"):
            await service.create_role(
                organization_id=org_id,
                name="Empty Permissions",
                permissions=[],
                requested_by=uuid4(),
            )


class TestGetRole:
    async def test_get_role_found(self, service, sample_role, role_repo):
        """Verifica que al buscar un rol existente se retorne el objeto correcto."""
        role_repo.get_by_id.return_value = sample_role

        result = await service.get_role(sample_role.id)

        assert result == sample_role
        role_repo.get_by_id.assert_called_once_with(sample_role.id)

    async def test_get_role_not_found(self, service, role_repo):
        """Verifica que se retorne None cuando el rol no existe."""
        role_id = uuid4()

        result = await service.get_role(role_id)

        assert result is None
        role_repo.get_by_id.assert_called_once_with(role_id)


class TestListRoles:
    async def test_list_roles_returns_items(self, service, sample_role, role_repo):
        """Verifica que se listen correctamente los roles de una organización."""
        role_repo.list_by_organization.return_value = [sample_role]

        result = await service.list_roles(sample_role.organization_id)

        assert len(result) == 1
        assert result[0] == sample_role
        role_repo.list_by_organization.assert_called_once_with(sample_role.organization_id)

    async def test_list_roles_empty(self, service, role_repo):
        """Verifica que se retorne una lista vacía cuando no hay roles."""
        org_id = uuid4()

        result = await service.list_roles(org_id)

        assert result == []


class TestUpdateRole:
    async def test_update_role_all_fields(self, service, sample_role, role_repo):
        """Verifica la actualización exitosa de todos los campos de un rol."""
        role_repo.get_by_id.return_value = sample_role
        role_repo.update.return_value = sample_role

        new_permissions = [Permission.MANAGE_CONNECTORS, Permission.CREATE_PROJECT]
        result = await service.update_role(
            role_id=sample_role.id,
            name="Updated Name",
            permissions=new_permissions,
            is_active=False,
            requested_by=uuid4(),
        )

        assert result.name == "Updated Name"
        assert result.permissions == new_permissions
        assert result.is_active is False
        role_repo.update.assert_called_once_with(sample_role)

    async def test_update_role_name_only(self, service, sample_role, role_repo):
        """Verifica que solo se actualice el nombre sin modificar los demás campos."""
        role_repo.get_by_id.return_value = sample_role
        role_repo.update.return_value = sample_role

        result = await service.update_role(
            role_id=sample_role.id,
            name="New Name",
        )

        assert result.name == "New Name"

    async def test_update_role_not_found(self, service, role_repo):
        """Verifica que se lance EntityNotFoundError al actualizar un rol inexistente."""
        role_repo.get_by_id.return_value = None
        with pytest.raises(EntityNotFoundError, match="Rol no encontrado"):
            await service.update_role(
                role_id=uuid4(),
                name="Test",
            )

    async def test_update_role_empty_permissions_fails(self, service, sample_role, role_repo):
        """Verifica que se lance ValidationError al intentar dejar un rol sin permisos."""
        role_repo.get_by_id.return_value = sample_role

        with pytest.raises(ValidationError, match="al menos un permiso"):
            await service.update_role(
                role_id=sample_role.id,
                permissions=[],
            )


class TestDeleteRole:
    async def test_delete_role_success(self, service, sample_role, role_repo):
        """Verifica la eliminación exitosa de un rol existente."""
        role_repo.get_by_id.return_value = sample_role

        await service.delete_role(sample_role.id, uuid4())

        role_repo.delete.assert_called_once_with(sample_role.id)

    async def test_delete_role_not_found(self, service, role_repo):
        """Verifica que se lance EntityNotFoundError al eliminar un rol inexistente."""
        role_repo.get_by_id.return_value = None
        with pytest.raises(EntityNotFoundError, match="Rol no encontrado"):
            await service.delete_role(role_id=uuid4(), requested_by=uuid4())

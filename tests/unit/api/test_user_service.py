import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4
from application.use_cases.main.user_service import UserService
from domain.entities.user import User
from domain.enums import UserRole
from domain.exceptions import (
    EntityNotFoundError,
    DuplicateEntityError,
    ValidationError,
    AuthenticationError,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_audit_logger():
    logger = MagicMock()
    logger.log = MagicMock()
    return logger


@pytest.fixture
def mock_password_hasher():
    hasher = MagicMock()
    hasher.hash_password.return_value = "hashed_password"
    hasher.verify_password.return_value = True
    return hasher


@pytest.fixture
def mock_user_repo():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.get_by_email = AsyncMock(return_value=None)
    repo.create = AsyncMock(side_effect=lambda user: user)
    repo.update = AsyncMock(side_effect=lambda user: user)
    repo.list_all = AsyncMock(return_value=[])
    repo.delete = AsyncMock()
    return repo


@pytest.fixture
def mock_org_repo():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def service(mock_user_repo, mock_org_repo, mock_password_hasher, mock_audit_logger):
    with patch(
        "application.use_cases.main.user_service.get_audit_logger",
        return_value=mock_audit_logger,
    ):
        yield UserService(mock_user_repo, mock_org_repo, mock_password_hasher)


@pytest.fixture
def sample_user():
    return User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="old_hashed", # NOSONAR
        display_name="Test User",
        role=UserRole.U2,
        is_active=True,
        organization_ids=[],
    )


@pytest.fixture
def sample_user_with_org():
    org_id = uuid4()
    return User(
        id=uuid4(),
        email="orguser@example.com",
        hashed_password="old_hashed", # NOSONAR
        display_name="Org User",
        role=UserRole.U2,
        is_active=True,
        organization_ids=[org_id],
    )


class TestGetUserById:
    """Pruebas para obtener un usuario por su ID."""

    async def test_returns_user_when_found(self, service, mock_user_repo, sample_user):
        """Verifica que al solicitar un usuario existente, se retorna el usuario correcto."""
        mock_user_repo.get_by_id.return_value = sample_user

        result = await service.get_user_by_id(sample_user.id)

        assert result is sample_user
        mock_user_repo.get_by_id.assert_called_once_with(sample_user.id)

    async def test_returns_none_when_not_found(self, service, mock_user_repo):
        """Verifica que se retorna None si el usuario no existe."""
        mock_user_repo.get_by_id.return_value = None

        result = await service.get_user_by_id(uuid4())

        assert result is None


class TestUpdateProfile:
    """Pruebas para actualizar el perfil de un usuario."""

    async def test_updates_display_name_successfully(self, service, mock_user_repo, sample_user):
        """Verifica que se actualiza correctamente el nombre visible del usuario."""
        mock_user_repo.get_by_id.return_value = sample_user

        result = await service.update_profile(sample_user.id, display_name="Nuevo Nombre")

        assert result.display_name == "Nuevo Nombre"
        mock_user_repo.update.assert_called_once()

    async def test_no_change_when_display_name_is_none(self, service, mock_user_repo, sample_user):
        """Verifica que no se modifica el nombre visible cuando se pasa None."""
        original_name = sample_user.display_name
        mock_user_repo.get_by_id.return_value = sample_user

        result = await service.update_profile(sample_user.id, display_name=None)

        assert result.display_name == original_name

    async def test_raises_entity_not_found(self, service, mock_user_repo):
        """Verifica que se lanza EntityNotFoundError si el usuario no existe."""
        mock_user_repo.get_by_id.return_value = None

        with pytest.raises(EntityNotFoundError, match="Usuario no encontrado"):
            await service.update_profile(uuid4(), display_name="Nombre")


class TestChangePassword:
    """Pruebas para el cambio de contraseña."""

    async def test_returns_true_when_password_changed(
        self, service, mock_user_repo, mock_password_hasher, sample_user
    ):
        """Verifica que se cambia la contraseña exitosamente y se retorna True."""
        mock_user_repo.get_by_id.return_value = sample_user
        mock_password_hasher.verify_password.return_value = True
        mock_password_hasher.hash_password.return_value = "new_hashed"

        result = await service.change_password(sample_user.id, "old_pass", "new_pass")

        assert result is True
        assert sample_user.hashed_password == "new_hashed"
        mock_password_hasher.verify_password.assert_called_once_with("old_pass", "old_hashed")
        mock_password_hasher.hash_password.assert_called_once_with("new_pass")
        mock_user_repo.update.assert_called_once()

    async def test_returns_false_when_current_password_wrong(
        self, service, mock_user_repo, mock_password_hasher, sample_user
    ):
        """Verifica que se retorna False cuando la contraseña actual es incorrecta."""
        mock_user_repo.get_by_id.return_value = sample_user
        mock_password_hasher.verify_password.return_value = False

        result = await service.change_password(sample_user.id, "wrong_pass", "new_pass")

        assert result is False
        mock_password_hasher.hash_password.assert_not_called()
        mock_user_repo.update.assert_not_called()

    async def test_raises_entity_not_found(self, service, mock_user_repo):
        """Verifica que se lanza EntityNotFoundError si el usuario no existe."""
        mock_user_repo.get_by_id.return_value = None

        with pytest.raises(EntityNotFoundError, match="Usuario no encontrado"):
            await service.change_password(uuid4(), "old", "new")


class TestListOrganizationUsers:
    """Pruebas para listar usuarios de una organización."""

    async def test_delegates_to_repo_with_default_pagination(
        self, service, mock_user_repo, sample_user
    ):
        """Verifica que se delega correctamente al repositorio con paginación por defecto."""
        org_id = uuid4()
        mock_user_repo.list_all.return_value = [sample_user]

        result = await service.list_organization_users(org_id)

        assert result == [sample_user]
        mock_user_repo.list_all.assert_called_once_with(
            organization_id=org_id, skip=0, limit=50
        )

    async def test_delegates_to_repo_with_custom_pagination(
        self, service, mock_user_repo, sample_user
    ):
        """Verifica que se delega al repositorio con parámetros de paginación personalizados."""
        org_id = uuid4()
        mock_user_repo.list_all.return_value = [sample_user]

        result = await service.list_organization_users(org_id, skip=10, limit=20)

        assert result == [sample_user]
        mock_user_repo.list_all.assert_called_once_with(
            organization_id=org_id, skip=10, limit=20
        )


class TestInviteUser:
    """Pruebas para invitar un usuario a una organización."""

    async def test_invites_new_user_successfully(
        self, service, mock_user_repo, mock_org_repo, mock_audit_logger
    ):
        """Verifica que un nuevo usuario sin cuenta previa es creado e invitado a la organización."""
        org_id = uuid4()
        org = MagicMock()
        org.id = org_id
        mock_org_repo.get_by_id.return_value = org
        mock_user_repo.get_by_email.return_value = None

        result = await service.invite_user(
            organization_id=org_id,
            email="nuevo@example.com",
            role=UserRole.U2,
            requested_by=uuid4(),
        )

        assert result.email == "nuevo@example.com"
        assert result.display_name == "nuevo"
        assert result.role == UserRole.U2
        assert result.is_active is False
        assert org_id in result.organization_ids
        mock_user_repo.create.assert_called_once()
        mock_audit_logger.log.assert_called_once()

    async def test_invites_existing_user_without_organization(
        self, service, mock_user_repo, mock_org_repo, mock_audit_logger, sample_user
    ):
        """Verifica que un usuario existente sin organización se une a la organización invitada."""
        org_id = uuid4()
        org = MagicMock()
        org.id = org_id
        mock_org_repo.get_by_id.return_value = org
        sample_user.organization_ids = []
        mock_user_repo.get_by_email.return_value = sample_user

        result = await service.invite_user(
            organization_id=org_id,
            email=sample_user.email,
            role=UserRole.U4,
            requested_by=uuid4(),
        )

        assert result.role == UserRole.U4
        assert result.organization_id == org_id
        mock_user_repo.update.assert_called_once()
        mock_audit_logger.log.assert_called_once()

    async def test_raises_duplicate_for_user_already_in_org(
        self, service, mock_user_repo, mock_org_repo, sample_user_with_org
    ):
        """Verifica que se lanza DuplicateEntityError si el usuario ya pertenece a una organización."""
        org_id = uuid4()
        org = MagicMock()
        mock_org_repo.get_by_id.return_value = org
        mock_user_repo.get_by_email.return_value = sample_user_with_org

        with pytest.raises(DuplicateEntityError, match="ya pertenece a una organización"):
            await service.invite_user(
                organization_id=org_id,
                email=sample_user_with_org.email,
                role=UserRole.U2,
                requested_by=uuid4(),
            )

    async def test_raises_entity_not_found_when_org_not_found(
        self, service, mock_org_repo
    ):
        """Verifica que se lanza EntityNotFoundError si la organización no existe."""
        mock_org_repo.get_by_id.return_value = None

        with pytest.raises(EntityNotFoundError, match="Organización no encontrada"):
            await service.invite_user(
                organization_id=uuid4(),
                email="test@example.com",
                role=UserRole.U2,
                requested_by=uuid4(),
            )


class TestUpdateUserRole:
    """Pruebas para actualizar el rol de un usuario dentro de una organización."""

    async def test_updates_role_successfully(
        self, service, mock_user_repo, mock_org_repo, mock_audit_logger, sample_user_with_org
    ):
        """Verifica que el rol se actualiza exitosamente dentro de la organización."""
        org_id = sample_user_with_org.organization_ids[0]
        org = MagicMock()
        org.id = org_id
        org.owner_id = uuid4()
        mock_org_repo.get_by_id.return_value = org
        mock_user_repo.get_by_id.return_value = sample_user_with_org
        requested_by = uuid4()

        result = await service.update_user_role(
            user_id=sample_user_with_org.id,
            organization_id=org_id,
            new_role=UserRole.U4,
            requested_by=requested_by,
        )

        assert result.role == UserRole.U4
        mock_user_repo.update.assert_called_once()
        mock_audit_logger.log.assert_called_once()

    async def test_raises_entity_not_found_when_user_not_in_org(
        self, service, mock_user_repo, sample_user
    ):
        """Verifica que se lanza EntityNotFoundError si el usuario no pertenece a la organización."""
        mock_user_repo.get_by_id.return_value = sample_user

        with pytest.raises(EntityNotFoundError, match="Usuario no encontrado en esta organización"):
            await service.update_user_role(
                user_id=sample_user.id,
                organization_id=uuid4(),
                new_role=UserRole.U4,
                requested_by=uuid4(),
            )

    async def test_raises_entity_not_found_when_org_not_found(
        self, service, mock_user_repo, mock_org_repo, sample_user_with_org
    ):
        """Verifica que se lanza EntityNotFoundError si la organización no existe."""
        org_id = sample_user_with_org.organization_ids[0]
        mock_user_repo.get_by_id.return_value = sample_user_with_org
        mock_org_repo.get_by_id.return_value = None

        with pytest.raises(EntityNotFoundError, match="Organización no encontrada"):
            await service.update_user_role(
                user_id=sample_user_with_org.id,
                organization_id=org_id,
                new_role=UserRole.U4,
                requested_by=uuid4(),
            )

    async def test_raises_validation_error_for_owner(
        self, service, mock_user_repo, mock_org_repo, sample_user_with_org
    ):
        """Verifica que se lanza ValidationError al intentar cambiar el rol del Owner."""
        org_id = sample_user_with_org.organization_ids[0]
        org = MagicMock()
        org.id = org_id
        org.owner_id = sample_user_with_org.id
        mock_org_repo.get_by_id.return_value = org
        mock_user_repo.get_by_id.return_value = sample_user_with_org

        with pytest.raises(ValidationError, match="No se puede cambiar el rol del Owner"):
            await service.update_user_role(
                user_id=sample_user_with_org.id,
                organization_id=org_id,
                new_role=UserRole.U2,
                requested_by=uuid4(),
            )


class TestRemoveUserFromOrganization:
    """Pruebas para eliminar un usuario de una organización."""

    async def test_removes_user_successfully(
        self, service, mock_user_repo, mock_org_repo, mock_audit_logger, sample_user_with_org
    ):
        """Verifica que un usuario es removido exitosamente de la organización."""
        org_id = sample_user_with_org.organization_ids[0]
        org = MagicMock()
        org.id = org_id
        org.owner_id = uuid4()
        mock_org_repo.get_by_id.return_value = org
        mock_user_repo.get_by_id.return_value = sample_user_with_org
        requested_by = uuid4()

        await service.remove_user_from_organization(
            user_id=sample_user_with_org.id,
            organization_id=org_id,
            requested_by=requested_by,
        )

        assert sample_user_with_org.organization_id is None
        assert sample_user_with_org.role == UserRole.U1
        mock_user_repo.update.assert_called_once()
        mock_audit_logger.log.assert_called_once()

    async def test_raises_entity_not_found_when_user_not_in_org(
        self, service, mock_user_repo, sample_user
    ):
        """Verifica que se lanza EntityNotFoundError si el usuario no está en la organización."""
        mock_user_repo.get_by_id.return_value = sample_user

        with pytest.raises(EntityNotFoundError, match="Usuario no encontrado en esta organización"):
            await service.remove_user_from_organization(
                user_id=sample_user.id,
                organization_id=uuid4(),
                requested_by=uuid4(),
            )

    async def test_raises_entity_not_found_when_org_not_found(
        self, service, mock_user_repo, mock_org_repo, sample_user_with_org
    ):
        """Verifica que se lanza EntityNotFoundError si la organización no existe."""
        org_id = sample_user_with_org.organization_ids[0]
        mock_user_repo.get_by_id.return_value = sample_user_with_org
        mock_org_repo.get_by_id.return_value = None

        with pytest.raises(EntityNotFoundError, match="Organización no encontrada"):
            await service.remove_user_from_organization(
                user_id=sample_user_with_org.id,
                organization_id=org_id,
                requested_by=uuid4(),
            )

    async def test_raises_validation_error_for_owner(
        self, service, mock_user_repo, mock_org_repo, sample_user_with_org
    ):
        """Verifica que se lanza ValidationError al intentar eliminar al Owner."""
        org_id = sample_user_with_org.organization_ids[0]
        org = MagicMock()
        org.id = org_id
        org.owner_id = sample_user_with_org.id
        mock_org_repo.get_by_id.return_value = org
        mock_user_repo.get_by_id.return_value = sample_user_with_org

        with pytest.raises(ValidationError, match="No se puede eliminar al Owner"):
            await service.remove_user_from_organization(
                user_id=sample_user_with_org.id,
                organization_id=org_id,
                requested_by=uuid4(),
            )


class TestCreateUser:
    """Pruebas para crear un nuevo usuario."""

    async def test_creates_user_successfully(
        self, service, mock_user_repo, mock_password_hasher
    ):
        """Verifica que se crea un usuario nuevo exitosamente con contraseña hasheada."""
        mock_user_repo.get_by_email.return_value = None
        mock_password_hasher.hash_password.return_value = "hashed_secret"

        result = await service.create_user(
            email="newuser@example.com",
            display_name="New User",
            password="secure123", # NOSONAR
            role=UserRole.U2,
        )

        assert result.email == "newuser@example.com"
        assert result.display_name == "New User"
        assert result.hashed_password == "hashed_secret"
        assert result.role == UserRole.U2
        assert result.is_active is True
        mock_password_hasher.hash_password.assert_called_once_with("secure123")
        mock_user_repo.create.assert_called_once()

    async def test_raises_duplicate_for_existing_email(
        self, service, mock_user_repo, sample_user
    ):
        """Verifica que se lanza DuplicateEntityError si el email ya está registrado."""
        mock_user_repo.get_by_email.return_value = sample_user

        with pytest.raises(DuplicateEntityError, match="Ya existe un usuario con email"):
            await service.create_user(
                email=sample_user.email,
                display_name="Another",
                password="pass123", # NOSONAR
                role=UserRole.U2,
            )

    async def test_creates_user_with_terms_and_privacy(
        self, service, mock_user_repo, mock_password_hasher
    ):
        """Verifica que se crea un usuario con términos y privacidad aceptados."""
        from datetime import datetime, timezone
        mock_user_repo.get_by_email.return_value = None
        now = datetime.now(timezone.utc)

        result = await service.create_user(
            email="terms@example.com",
            display_name="Terms User",
            password="pass123", # NOSONAR
            role=UserRole.U2,
            terms_accepted_at=now,
            privacy_accepted_at=now,
        )

        assert result.terms_accepted_at == now
        assert result.privacy_accepted_at == now


class TestActivateUser:
    """Pruebas para activar un usuario."""

    async def test_activates_user_successfully(self, service, mock_user_repo, sample_user):
        """Verifica que se activa un usuario inactivo exitosamente."""
        sample_user.is_active = False
        mock_user_repo.get_by_id.return_value = sample_user

        result = await service.activate_user(sample_user.id)

        assert result.is_active is True
        mock_user_repo.update.assert_called_once()

    async def test_raises_entity_not_found(self, service, mock_user_repo):
        """Verifica que se lanza EntityNotFoundError si el usuario no existe."""
        mock_user_repo.get_by_id.return_value = None

        with pytest.raises(EntityNotFoundError, match="Usuario no encontrado"):
            await service.activate_user(uuid4())


class TestDeactivateUser:
    """Pruebas para desactivar un usuario."""

    async def test_deactivates_user_successfully(
        self, service, mock_user_repo, mock_audit_logger, sample_user
    ):
        """Verifica que se desactiva un usuario activo exitosamente."""
        sample_user.is_active = True
        mock_user_repo.get_by_id.return_value = sample_user
        requested_by = uuid4()

        result = await service.deactivate_user(sample_user.id, requested_by)

        assert result.is_active is False
        mock_user_repo.update.assert_called_once()
        mock_audit_logger.log.assert_called_once()

    async def test_raises_entity_not_found(self, service, mock_user_repo):
        """Verifica que se lanza EntityNotFoundError si el usuario no existe."""
        mock_user_repo.get_by_id.return_value = None

        with pytest.raises(EntityNotFoundError, match="Usuario no encontrado"):
            await service.deactivate_user(uuid4(), uuid4())


class TestUpdateGlobalRole:
    """Pruebas para actualizar el rol global de un usuario."""

    async def test_updates_role_successfully(
        self, service, mock_user_repo, mock_audit_logger, sample_user
    ):
        """Verifica que se actualiza el rol global de un usuario exitosamente."""
        sample_user.role = UserRole.U2
        mock_user_repo.get_by_id.return_value = sample_user
        requested_by = uuid4()

        result = await service.update_global_role(
            user_id=sample_user.id,
            new_role=UserRole.U3,
            requested_by=requested_by,
        )

        assert result.role == UserRole.U3
        mock_user_repo.update.assert_called_once()
        mock_audit_logger.log.assert_called_once()

    async def test_raises_entity_not_found(self, service, mock_user_repo):
        """Verifica que se lanza EntityNotFoundError si el usuario no existe."""
        mock_user_repo.get_by_id.return_value = None

        with pytest.raises(EntityNotFoundError, match="Usuario no encontrado"):
            await service.update_global_role(
                user_id=uuid4(),
                new_role=UserRole.U3,
                requested_by=uuid4(),
            )


class TestListAllUsers:
    """Pruebas para listar todos los usuarios con filtros opcionales."""

    async def test_returns_all_active_users_by_default(
        self, service, mock_user_repo, sample_user
    ):
        """Verifica que por defecto se listan solo usuarios activos."""
        mock_user_repo.list_all.return_value = [sample_user]

        result = await service.list_all_users()

        assert result == [sample_user]
        mock_user_repo.list_all.assert_called_once_with(
            organization_id=None, active_only=True, skip=0, limit=50
        )

    async def test_filters_by_role(self, service, mock_user_repo, sample_user):
        """Verifica que se filtran los usuarios por rol cuando se especifica."""
        admin_user = User(
            id=uuid4(),
            email="admin@example.com",
            hashed_password="hashed", # NOSONAR
            display_name="Admin",
            role=UserRole.U3,
            is_active=True,
        )
        mock_user_repo.list_all.return_value = [sample_user, admin_user]

        result = await service.list_all_users(role=UserRole.U3)

        assert result == [admin_user]
        assert len(result) == 1

    async def test_respects_is_active_false(self, service, mock_user_repo, sample_user):
        """Verifica que se pueden listar usuarios inactivos cuando is_active=False."""
        sample_user.is_active = False
        mock_user_repo.list_all.return_value = [sample_user]

        result = await service.list_all_users(is_active=False)

        assert result == [sample_user]
        mock_user_repo.list_all.assert_called_once_with(
            organization_id=None, active_only=False, skip=0, limit=50
        )

    async def test_with_custom_pagination(self, service, mock_user_repo):
        """Verifica que se respetan los parámetros de paginación personalizados."""
        mock_user_repo.list_all.return_value = []

        await service.list_all_users(skip=20, limit=10)

        mock_user_repo.list_all.assert_called_once_with(
            organization_id=None, active_only=True, skip=20, limit=10
        )


class TestDeleteUserAccount:
    """Pruebas para eliminar una cuenta de usuario."""

    async def test_deletes_account_successfully(
        self, service, mock_user_repo, mock_org_repo, mock_password_hasher, mock_audit_logger, sample_user
    ):
        """Verifica que se elimina la cuenta exitosamente cuando la contraseña es correcta."""
        mock_user_repo.get_by_id.return_value = sample_user
        mock_password_hasher.verify_password.return_value = True
        requested_by = sample_user.id

        await service.delete_user_account(
            user_id=sample_user.id,
            requested_by=requested_by,
            password="correct_pass", # NOSONAR
        )

        mock_password_hasher.verify_password.assert_called_once_with("correct_pass", sample_user.hashed_password)
        mock_user_repo.delete.assert_called_once_with(sample_user.id)
        mock_audit_logger.log.assert_called_once()

    async def test_raises_authentication_error_when_wrong_password(
        self, service, mock_user_repo, mock_password_hasher, sample_user
    ):
        """Verifica que se lanza AuthenticationError cuando la contraseña es incorrecta."""
        mock_user_repo.get_by_id.return_value = sample_user
        mock_password_hasher.verify_password.return_value = False

        with pytest.raises(AuthenticationError, match="Contraseña incorrecta"):
            await service.delete_user_account(
                user_id=sample_user.id,
                requested_by=sample_user.id,
                password="wrong_pass", # NOSONAR
            )

        mock_user_repo.delete.assert_not_called()

    async def test_raises_entity_not_found(self, service, mock_user_repo):
        """Verifica que se lanza EntityNotFoundError si el usuario no existe."""
        mock_user_repo.get_by_id.return_value = None

        with pytest.raises(EntityNotFoundError, match="Usuario no encontrado"):
            await service.delete_user_account(
                user_id=uuid4(),
                requested_by=uuid4(),
                password="any_pass", # NOSONAR
            )

    async def test_raises_validation_error_when_user_is_org_owner(
        self, service, mock_user_repo, mock_org_repo, mock_password_hasher, sample_user_with_org
    ):
        """Verifica que se lanza ValidationError si el usuario es propietario de una organización."""
        org_id = sample_user_with_org.organization_ids[0]
        org = MagicMock()
        org.id = org_id
        org.owner_id = sample_user_with_org.id
        mock_user_repo.get_by_id.return_value = sample_user_with_org
        mock_password_hasher.verify_password.return_value = True
        mock_org_repo.get_by_id.return_value = org

        with pytest.raises(ValidationError, match="propietario de una organización"):
            await service.delete_user_account(
                user_id=sample_user_with_org.id,
                requested_by=sample_user_with_org.id,
                password="correct", # NOSONAR
            )

        mock_user_repo.delete.assert_not_called()

    async def test_deletes_account_when_org_not_found(
        self, service, mock_user_repo, mock_org_repo, mock_password_hasher, mock_audit_logger, sample_user_with_org
    ):
        """Verifica que se elimina la cuenta incluso si la organización referenciada ya no existe."""
        mock_user_repo.get_by_id.return_value = sample_user_with_org
        mock_password_hasher.verify_password.return_value = True
        mock_org_repo.get_by_id.return_value = None

        await service.delete_user_account(
            user_id=sample_user_with_org.id,
            requested_by=sample_user_with_org.id,
            password="correct", # NOSONAR
        )

        mock_user_repo.delete.assert_called_once()

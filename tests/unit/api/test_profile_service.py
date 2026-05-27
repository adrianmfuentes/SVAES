import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from application.use_cases.main.profile_service import ProfileService
from domain.entities.verification_profile import VerificationProfile
from domain.entities.verification_rule import VerificationRule
from domain.enums import SeverityType
from domain.exceptions import EntityNotFoundError


@pytest.fixture
def mock_audit_logger():
    logger = MagicMock()
    logger.log = MagicMock()
    return logger


@pytest.fixture
def profile_repo():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock()
    repo.list_by_organization = AsyncMock(return_value=[])
    repo.get_default_for_organization = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def rule_repo():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock()
    return repo


@pytest.fixture
def service(profile_repo, rule_repo, mock_audit_logger):
    with patch(
        "application.use_cases.main.profile_service.get_audit_logger",
        return_value=mock_audit_logger,
    ):
        return ProfileService(profile_repo, rule_repo)


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


@pytest.fixture
def sample_rule(sample_profile):
    return VerificationRule(
        profile_id=sample_profile.id,
        rule_template="check_unit_tests",
        severity=SeverityType.HIGH,
        params={"min_coverage": 80},
        connector_instance_id=None,
        display_order=0,
        is_active=True,
    )


pytestmark = pytest.mark.unit


class TestCreateProfile:
    async def test_create_profile_success(self, service, profile_repo):
        """Verifica la creación exitosa de un perfil con los datos correctos y reglas vacías."""
        org_id = uuid4()
        created_profile = VerificationProfile(
            id=uuid4(),
            organization_id=org_id,
            name="Mi Perfil",
            description="Descripción",
            is_default=False,
            rules=[],
        )
        profile_repo.create.return_value = created_profile

        result = await service.create_profile(
            organization_id=org_id,
            name="Mi Perfil",
            description="Descripción",
            is_default=False,
            requested_by=uuid4(),
        )

        assert result.name == "Mi Perfil"
        assert result.organization_id == org_id
        assert result.description == "Descripción"
        assert result.is_default is False
        assert result.rules == []
        profile_repo.create.assert_called_once()

    async def test_create_profile_with_default_no_existing(self, service, profile_repo):
        """Verifica que al crear un perfil como default sin otro default existente, se cree correctamente."""
        org_id = uuid4()
        profile_repo.get_default_for_organization.return_value = None
        created_profile = VerificationProfile(
            id=uuid4(),
            organization_id=org_id,
            name="Default Profile",
            description="",
            is_default=True,
            rules=[],
        )
        profile_repo.create.return_value = created_profile

        result = await service.create_profile(
            organization_id=org_id,
            name="Default Profile",
            is_default=True,
        )

        assert result.is_default is True
        profile_repo.get_default_for_organization.assert_called_once_with(org_id)
        profile_repo.update.assert_not_called()

    async def test_create_profile_with_default_existing_unnmarks_old(self, service, profile_repo):
        """Verifica que al crear un perfil default cuando ya existe uno, se desmarque el anterior."""
        org_id = uuid4()
        existing_default = VerificationProfile(
            id=uuid4(),
            organization_id=org_id,
            name="Old Default",
            description="",
            is_default=True,
            rules=[],
        )
        profile_repo.get_default_for_organization.return_value = existing_default
        created_profile = VerificationProfile(
            id=uuid4(),
            organization_id=org_id,
            name="New Default",
            description="",
            is_default=True,
            rules=[],
        )
        profile_repo.create.return_value = created_profile

        result = await service.create_profile(
            organization_id=org_id,
            name="New Default",
            is_default=True,
        )

        assert result.is_default is True
        assert existing_default.is_default is False
        profile_repo.update.assert_any_call(existing_default)

    async def test_create_profile_with_minimal_data(self, service, profile_repo):
        """Verifica la creación exitosa de un perfil con solo nombre y organización, usando valores por defecto."""
        org_id = uuid4()
        created_profile = VerificationProfile(
            id=uuid4(),
            organization_id=org_id,
            name="Minimal",
            description="",
            is_default=False,
            rules=[],
        )
        profile_repo.create.return_value = created_profile

        result = await service.create_profile(
            organization_id=org_id,
            name="Minimal",
        )

        assert result.name == "Minimal"
        assert result.description == ""
        assert result.is_default is False
        assert result.rules == []


class TestUpdateProfile:
    async def test_update_profile_all_fields(self, service, sample_profile, profile_repo):
        """Verifica la actualización exitosa de todos los campos de un perfil."""
        profile_repo.get_by_id.return_value = sample_profile
        profile_repo.update.return_value = sample_profile

        result = await service.update_profile(
            profile_id=sample_profile.id,
            name="Updated Name",
            description="Updated Description",
            is_default=True,
            requested_by=uuid4(),
        )

        assert result.name == "Updated Name"
        assert result.description == "Updated Description"
        assert result.is_default is True
        profile_repo.get_default_for_organization.assert_called_once_with(
            sample_profile.organization_id
        )
        profile_repo.update.assert_called_once_with(sample_profile)

    async def test_update_profile_name_only(self, service, sample_profile, profile_repo):
        """Verifica que solo se actualice el campo name sin modificar los demás."""
        profile_repo.get_by_id.return_value = sample_profile
        profile_repo.update.return_value = sample_profile
        original_description = sample_profile.description
        original_is_default = sample_profile.is_default

        result = await service.update_profile(
            profile_id=sample_profile.id, name="New Name"
        )

        assert result.name == "New Name"
        assert result.description == original_description
        assert result.is_default == original_is_default
        profile_repo.update.assert_called_once()

    async def test_update_profile_not_found(self, service, profile_repo):
        """Verifica que se lance EntityNotFoundError al actualizar un perfil inexistente."""
        profile_repo.get_by_id.return_value = None
        with pytest.raises(EntityNotFoundError, match="Perfil no encontrado"):
            await service.update_profile(profile_id=uuid4(), name="Test")

    async def test_update_profile_set_default_existing(self, service, sample_profile, profile_repo):
        """Verifica que al marcar un perfil como default, se desmarque el default anterior."""
        profile_repo.get_by_id.return_value = sample_profile
        profile_repo.update.return_value = sample_profile
        existing_default = VerificationProfile(
            id=uuid4(),
            organization_id=sample_profile.organization_id,
            name="Existing Default",
            description="",
            is_default=True,
            rules=[],
        )
        profile_repo.get_default_for_organization.return_value = existing_default

        result = await service.update_profile(
            profile_id=sample_profile.id, is_default=True
        )

        assert result.is_default is True
        assert existing_default.is_default is False
        profile_repo.update.assert_any_call(existing_default)

    async def test_update_profile_set_default_already_default(self, service, sample_profile, profile_repo):
        """Verifica que no se consulte el default existente si el perfil ya era default."""
        sample_profile.is_default = True
        profile_repo.get_by_id.return_value = sample_profile
        profile_repo.update.return_value = sample_profile

        result = await service.update_profile(
            profile_id=sample_profile.id, is_default=True
        )

        assert result.is_default is True
        profile_repo.get_default_for_organization.assert_not_called()

    async def test_update_profile_unset_default(self, service, sample_profile, profile_repo):
        """Verifica que se pueda desmarcar un perfil como default sin errores."""
        sample_profile.is_default = True
        profile_repo.get_by_id.return_value = sample_profile
        profile_repo.update.return_value = sample_profile

        result = await service.update_profile(
            profile_id=sample_profile.id, is_default=False
        )

        assert result.is_default is False
        profile_repo.update.assert_called_once_with(sample_profile)


class TestListProfiles:
    async def test_list_profiles_returns_items(self, service, sample_profile, profile_repo):
        """Verifica que se listen correctamente los perfiles de una organización cuando existen."""
        profile_repo.list_by_organization.return_value = [sample_profile]
        org_id = sample_profile.organization_id

        result = await service.list_profiles(org_id)

        assert len(result) == 1
        assert result[0] == sample_profile
        profile_repo.list_by_organization.assert_called_once_with(
            org_id, skip=0, limit=50
        )

    async def test_list_profiles_empty(self, service, profile_repo):
        """Verifica que se retorne una lista vacía cuando la organización no tiene perfiles."""
        org_id = uuid4()

        result = await service.list_profiles(org_id)

        assert result == []
        profile_repo.list_by_organization.assert_called_once_with(
            org_id, skip=0, limit=50
        )

    async def test_list_profiles_with_pagination(self, service, profile_repo):
        """Verifica que se respeten los parámetros skip y limit en la paginación de perfiles."""
        org_id = uuid4()

        await service.list_profiles(org_id, skip=10, limit=5)

        profile_repo.list_by_organization.assert_called_once_with(
            org_id, skip=10, limit=5
        )


class TestGetProfile:
    async def test_get_profile_found(self, service, sample_profile, profile_repo):
        """Verifica que al buscar un perfil existente se retorne el objeto correcto."""
        profile_repo.get_by_id.return_value = sample_profile

        result = await service.get_profile(sample_profile.id)

        assert result == sample_profile
        profile_repo.get_by_id.assert_called_once_with(sample_profile.id)

    async def test_get_profile_not_found(self, service, profile_repo):
        """Verifica que se retorne None cuando el perfil solicitado no existe."""
        profile_id = uuid4()

        result = await service.get_profile(profile_id)

        assert result is None
        profile_repo.get_by_id.assert_called_once_with(profile_id)


class TestDuplicateProfile:
    async def test_duplicate_profile_with_rules(self, service, sample_profile, sample_rule, profile_repo, rule_repo):
        """Verifica la duplicación exitosa de un perfil con todas sus reglas."""
        sample_profile.rules = [sample_rule]
        duplicated_profile = VerificationProfile(
            id=uuid4(),
            organization_id=sample_profile.organization_id,
            name="Copia de Perfil",
            description=sample_profile.description,
            is_default=False,
            rules=[],
        )
        profile_repo.get_by_id.side_effect = lambda pid: (
            sample_profile if pid == sample_profile.id
            else duplicated_profile if pid == duplicated_profile.id
            else None
        )
        profile_repo.create.return_value = duplicated_profile

        result = await service.duplicate_profile(
            profile_id=sample_profile.id,
            new_name="Copia de Perfil",
            requested_by=uuid4(),
        )

        assert result.id == duplicated_profile.id
        assert result.name == "Copia de Perfil"
        assert result.organization_id == sample_profile.organization_id
        assert result.description == sample_profile.description
        assert result.is_default is False
        profile_repo.create.assert_called_once()
        rule_repo.create.assert_called_once()
        created_rule_call = rule_repo.create.call_args[0][0]
        assert created_rule_call.profile_id == duplicated_profile.id
        assert created_rule_call.rule_template == sample_rule.rule_template
        assert created_rule_call.severity == sample_rule.severity
        assert created_rule_call.params == sample_rule.params
        assert created_rule_call.display_order == sample_rule.display_order
        assert created_rule_call.is_active == sample_rule.is_active

    async def test_duplicate_profile_without_rules(self, service, sample_profile, profile_repo, rule_repo):
        """Verifica la duplicación exitosa de un perfil que no tiene reglas."""
        sample_profile.rules = []
        duplicated_profile = VerificationProfile(
            id=uuid4(),
            organization_id=sample_profile.organization_id,
            name="Copia Vacía",
            description=sample_profile.description,
            is_default=False,
            rules=[],
        )
        profile_repo.get_by_id.side_effect = lambda pid: (
            sample_profile if pid == sample_profile.id
            else duplicated_profile if pid == duplicated_profile.id
            else None
        )
        profile_repo.create.return_value = duplicated_profile

        result = await service.duplicate_profile(
            profile_id=sample_profile.id,
            new_name="Copia Vacía",
        )

        assert result.name == "Copia Vacía"
        assert result.is_default is False
        rule_repo.create.assert_not_called()

    async def test_duplicate_profile_not_found(self, service, profile_repo):
        """Verifica que se lance EntityNotFoundError al duplicar un perfil inexistente."""
        profile_repo.get_by_id.return_value = None
        with pytest.raises(EntityNotFoundError, match="Perfil no encontrado"):
            await service.duplicate_profile(profile_id=uuid4(), new_name="Copia")

    async def test_duplicate_profile_always_sets_is_default_false(self, service, sample_profile, profile_repo):
        """Verifica que el perfil duplicado siempre tenga is_default=False sin importar el original."""
        sample_profile.is_default = True
        sample_profile.rules = []
        duplicated_profile = VerificationProfile(
            id=uuid4(),
            organization_id=sample_profile.organization_id,
            name="Copia de Default",
            description=sample_profile.description,
            is_default=False,
            rules=[],
        )
        profile_repo.get_by_id.side_effect = lambda pid: (
            sample_profile if pid == sample_profile.id
            else duplicated_profile if pid == duplicated_profile.id
            else None
        )
        profile_repo.create.return_value = duplicated_profile

        result = await service.duplicate_profile(
            profile_id=sample_profile.id,
            new_name="Copia de Default",
        )

        assert result.is_default is False
        assert sample_profile.is_default is True


class TestDeleteProfile:
    async def test_delete_profile_success(self, service, sample_profile, profile_repo):
        """Verifica la eliminación exitosa de un perfil existente."""
        profile_repo.get_by_id.return_value = sample_profile

        await service.delete_profile(sample_profile.id, requested_by=uuid4())

        profile_repo.delete.assert_called_once_with(sample_profile.id)

    async def test_delete_profile_not_found(self, service, profile_repo):
        """Verifica que se lance EntityNotFoundError al eliminar un perfil inexistente."""
        profile_repo.get_by_id.return_value = None
        with pytest.raises(EntityNotFoundError, match="Perfil no encontrado"):
            await service.delete_profile(profile_id=uuid4(), requested_by=uuid4())


class TestAddRule:
    async def test_add_rule_success_with_all_params(self, service, sample_profile, profile_repo, rule_repo):
        """Verifica la adición exitosa de una regla con todos los parámetros a un perfil."""
        profile_repo.get_by_id.return_value = sample_profile
        conn_instance_id = uuid4()

        created_rule = VerificationRule(
            profile_id=sample_profile.id,
            rule_template="check_code_review",
            severity=SeverityType.CRITICAL,
            params={"reviewers": 2, "mandatory": True},
            connector_instance_id=conn_instance_id,
            display_order=5,
            is_active=True,
        )
        rule_repo.create.return_value = created_rule

        result = await service.add_rule(
            profile_id=sample_profile.id,
            rule_template="check_code_review",
            severity=SeverityType.CRITICAL,
            connector_instance_id=conn_instance_id,
            params={"reviewers": 2, "mandatory": True},
            display_order=5,
            requested_by=uuid4(),
        )

        assert result.profile_id == sample_profile.id
        assert result.rule_template == "check_code_review"
        assert result.severity == SeverityType.CRITICAL
        assert result.params == {"reviewers": 2, "mandatory": True}
        assert result.connector_instance_id == conn_instance_id
        assert result.display_order == 5
        rule_repo.create.assert_called_once()
        profile_repo.get_by_id.assert_called_once_with(sample_profile.id)

    async def test_add_rule_success_with_defaults(self, service, sample_profile, profile_repo, rule_repo):
        """Verifica la adición exitosa de una regla usando valores por defecto."""
        profile_repo.get_by_id.return_value = sample_profile
        created_rule = VerificationRule(
            profile_id=sample_profile.id,
            rule_template="check_defaults",
            severity=SeverityType.HIGH,
            params={},
            connector_instance_id=None,
            display_order=0,
            is_active=True,
        )
        rule_repo.create.return_value = created_rule

        result = await service.add_rule(
            profile_id=sample_profile.id,
            rule_template="check_defaults",
        )

        assert result.severity == SeverityType.HIGH
        assert result.params == {}
        assert result.connector_instance_id is None
        assert result.display_order == 0
        rule_repo.create.assert_called_once()

    async def test_add_rule_profile_not_found(self, service, profile_repo, rule_repo):
        """Verifica que se lance EntityNotFoundError al agregar una regla a un perfil inexistente."""
        profile_repo.get_by_id.return_value = None
        with pytest.raises(EntityNotFoundError, match="Perfil no encontrado"):
            await service.add_rule(
                profile_id=uuid4(),
                rule_template="check_something",
            )
        rule_repo.create.assert_not_called()


class TestUpdateRule:
    async def test_update_rule_all_fields(self, service, sample_rule, rule_repo):
        """Verifica la actualización exitosa de todos los campos de una regla."""
        rule_repo.get_by_id.return_value = sample_rule
        rule_repo.update.return_value = sample_rule
        new_conn_id = uuid4()

        result = await service.update_rule(
            rule_id=sample_rule.id,
            severity=SeverityType.CRITICAL,
            connector_instance_id=new_conn_id,
            params={"min_coverage": 90},
            display_order=3,
            is_active=False,
            requested_by=uuid4(),
        )

        assert result.severity == SeverityType.CRITICAL
        assert result.connector_instance_id == new_conn_id
        assert result.params == {"min_coverage": 90}
        assert result.display_order == 3
        assert result.is_active is False
        rule_repo.update.assert_called_once_with(sample_rule)

    async def test_update_rule_severity_only(self, service, sample_rule, rule_repo):
        """Verifica que solo se actualice la severidad sin modificar los demás campos."""
        rule_repo.get_by_id.return_value = sample_rule
        rule_repo.update.return_value = sample_rule
        original_params = sample_rule.params
        original_display_order = sample_rule.display_order
        original_is_active = sample_rule.is_active

        result = await service.update_rule(
            rule_id=sample_rule.id, severity=SeverityType.INFO
        )

        assert result.severity == SeverityType.INFO
        assert result.params == original_params
        assert result.display_order == original_display_order
        assert result.is_active == original_is_active
        rule_repo.update.assert_called_once()

    async def test_update_rule_not_found(self, service, rule_repo):
        """Verifica que se lance EntityNotFoundError al actualizar una regla inexistente."""
        rule_repo.get_by_id.return_value = None
        with pytest.raises(EntityNotFoundError, match="Regla no encontrada"):
            await service.update_rule(
                rule_id=uuid4(),
                severity=SeverityType.LOW,
            )

    async def test_update_rule_params_none_does_not_change(self, service, sample_rule, rule_repo):
        """Verifica que pasar None en un campo no modifique su valor actual."""
        rule_repo.get_by_id.return_value = sample_rule
        rule_repo.update.return_value = sample_rule
        original_params = sample_rule.params
        original_severity = sample_rule.severity

        result = await service.update_rule(
            rule_id=sample_rule.id,
            params=None,
            severity=None,
            display_order=None,
            is_active=None,
        )

        assert result.params == original_params
        assert result.severity == original_severity
        rule_repo.update.assert_called_once()


class TestDeleteRule:
    async def test_delete_rule_success(self, service, sample_rule, rule_repo):
        """Verifica la eliminación exitosa de una regla existente."""
        rule_repo.get_by_id.return_value = sample_rule

        await service.delete_rule(sample_rule.id, requested_by=uuid4())

        rule_repo.delete.assert_called_once_with(sample_rule.id)

    async def test_delete_rule_not_found(self, service, rule_repo):
        """Verifica que se lance EntityNotFoundError al eliminar una regla inexistente."""
        rule_repo.get_by_id.return_value = None
        with pytest.raises(EntityNotFoundError, match="Regla no encontrada"):
            await service.delete_rule(rule_id=uuid4(), requested_by=uuid4())


class TestReorderRules:
    async def test_reorder_rules_success(self, service, sample_profile, rule_repo, profile_repo):
        """Verifica el reordenamiento exitoso de reglas según el orden de rule_ids proporcionado."""
        profile_repo.get_by_id.return_value = sample_profile
        rule1 = VerificationRule(
            profile_id=sample_profile.id,
            rule_template="rule_1",
            severity=SeverityType.HIGH,
            display_order=99,
        )
        rule2 = VerificationRule(
            profile_id=sample_profile.id,
            rule_template="rule_2",
            severity=SeverityType.MEDIUM,
            display_order=99,
        )
        rule3 = VerificationRule(
            profile_id=sample_profile.id,
            rule_template="rule_3",
            severity=SeverityType.LOW,
            display_order=99,
        )
        rule_repo.get_by_id.side_effect = lambda rid: {
            rule1.id: rule1,
            rule2.id: rule2,
            rule3.id: rule3,
        }.get(rid)
        rule_repo.update.side_effect = lambda r: r

        result = await service.reorder_rules(
            profile_id=sample_profile.id,
            rule_ids=[rule1.id, rule2.id, rule3.id],
        )

        assert len(result) == 3
        assert result[0].display_order == 0
        assert result[1].display_order == 1
        assert result[2].display_order == 2
        assert result[0].rule_template == "rule_1"
        assert result[1].rule_template == "rule_2"
        assert result[2].rule_template == "rule_3"
        assert rule_repo.update.call_count == 3

    async def test_reorder_rules_skips_rules_from_other_profile(self, service, sample_profile, rule_repo, profile_repo):
        """Verifica que se omitan reglas cuyo profile_id no coincida con el perfil."""
        profile_repo.get_by_id.return_value = sample_profile
        foreign_rule = VerificationRule(
            profile_id=uuid4(),
            rule_template="foreign_rule",
            severity=SeverityType.HIGH,
        )
        local_rule = VerificationRule(
            profile_id=sample_profile.id,
            rule_template="local_rule",
            severity=SeverityType.MEDIUM,
        )
        rule_repo.get_by_id.side_effect = lambda rid: {
            foreign_rule.id: foreign_rule,
            local_rule.id: local_rule,
        }.get(rid)
        rule_repo.update.side_effect = lambda r: r

        result = await service.reorder_rules(
            profile_id=sample_profile.id,
            rule_ids=[foreign_rule.id, local_rule.id],
        )

        assert len(result) == 1
        assert result[0].rule_template == "local_rule"
        assert result[0].display_order == 1

    async def test_reorder_rules_skips_nonexistent_rules(self, service, sample_profile, rule_repo, profile_repo):
        """Verifica que se omitan rule_ids que no correspondan a reglas existentes."""
        profile_repo.get_by_id.return_value = sample_profile
        local_rule = VerificationRule(
            profile_id=sample_profile.id,
            rule_template="existing_rule",
            severity=SeverityType.HIGH,
        )
        rule_repo.get_by_id.side_effect = lambda rid: (
            local_rule if rid == local_rule.id else None
        )
        rule_repo.update.side_effect = lambda r: r

        result = await service.reorder_rules(
            profile_id=sample_profile.id,
            rule_ids=[uuid4(), local_rule.id, uuid4()],
        )

        assert len(result) == 1
        assert result[0].rule_template == "existing_rule"

    async def test_reorder_rules_empty_ids(self, service, sample_profile, rule_repo, profile_repo):
        """Verifica que se retorne una lista vacía cuando rule_ids está vacío."""
        profile_repo.get_by_id.return_value = sample_profile

        result = await service.reorder_rules(
            profile_id=sample_profile.id,
            rule_ids=[],
        )

        assert result == []
        rule_repo.get_by_id.assert_not_called()
        rule_repo.update.assert_not_called()

    async def test_reorder_rules_profile_not_found(self, service, profile_repo):
        """Verifica que se lance EntityNotFoundError al reordenar reglas de un perfil inexistente."""
        profile_repo.get_by_id.return_value = None
        with pytest.raises(EntityNotFoundError, match="Perfil no encontrado"):
            await service.reorder_rules(
                profile_id=uuid4(),
                rule_ids=[uuid4()],
            )

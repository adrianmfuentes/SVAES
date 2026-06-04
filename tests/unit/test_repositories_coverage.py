"""
Branch-coverage tests for SQL repository implementations with low coverage:
template, connector, custom_role, rule, api_key.
Uses AsyncMock to simulate SQLAlchemy async sessions.
"""

import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
from datetime import datetime, timezone

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api", "src"))

pytestmark = pytest.mark.unit


# ── helpers ────────────────────────────────────────────────────────────────────

def _make_mock_session():
    session = AsyncMock()
    session_mgr = MagicMock()
    session_mgr.__aenter__ = AsyncMock(return_value=session)
    session_mgr.__aexit__ = AsyncMock(return_value=None)
    return session, session_mgr


def _make_scalar_result(row):
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=row)
    return result


def _make_scalars_result(rows):
    scalars = MagicMock()
    scalars.all = MagicMock(return_value=rows)
    result = MagicMock()
    result.scalars = MagicMock(return_value=scalars)
    return result


# ── mock row builders ──────────────────────────────────────────────────────────

def _make_template_row(template_id=None, org_id=None, name="tpl",
                       description="desc", profile_id=None, created_by=None,
                       project_name_template=None, is_archived=False):
    row = MagicMock()
    row.id = str(template_id or uuid4())
    row.organization_id = str(org_id or uuid4())
    row.name = name
    row.description = description
    row.profile_id = str(profile_id or uuid4())
    row.created_by = str(created_by or uuid4())
    row.project_name_template = project_name_template
    row.is_archived = is_archived
    row.created_at = datetime.now(timezone.utc)
    row.updated_at = datetime.now(timezone.utc)
    return row


def _make_connector_row(conn_id=None, org_id=None, conn_type="GESTOR_TAREAS",
                        conn_impl="JIRA", name="jira-conn", config=None,
                        status="ACTIVO", last_tested_at=None):
    row = MagicMock()
    row.id = str(conn_id or uuid4())
    row.organization_id = str(org_id or uuid4())
    row.connector_type = conn_type
    row.connector_implementation = conn_impl
    row.name = name
    row.config_encrypted = config or b"encrypted"
    row.status = status
    row.created_at = datetime.now(timezone.utc)
    row.updated_at = datetime.now(timezone.utc)
    row.last_tested_at = last_tested_at
    return row


def _make_custom_role_row(role_id=None, org_id=None, name="viewer",
                          permissions=None, is_active=True):
    row = MagicMock()
    row.id = str(role_id or uuid4())
    row.organization_id = str(org_id or uuid4())
    row.name = name
    row.permissions = ["VIEW_DASHBOARD"] if permissions is None else permissions
    row.is_active = is_active
    row.created_at = datetime.now(timezone.utc)
    row.updated_at = datetime.now(timezone.utc)
    return row


def _make_rule_row(rule_id=None, profile_id=None, rule_template="check_version",
                   severity="HIGH", params=None, connector_instance_id=None,
                   display_order=1, is_active=True):
    row = MagicMock()
    row.id = str(rule_id or uuid4())
    row.profile_id = str(profile_id or uuid4())
    row.rule_template = rule_template
    row.severity = severity
    row.params = params or {}
    row.connector_instance_id = connector_instance_id
    row.display_order = display_order
    row.is_active = is_active
    row.created_at = datetime.now(timezone.utc)
    return row


def _make_api_key_row(key_id=None, user_id=None, org_id=None, name="my-key",
                      key_hash="abc123", prefix="sv_s0", is_active=True,
                      expires_at=None, last_used_at=None):
    row = MagicMock()
    row.id = str(key_id or uuid4())
    row.user_id = str(user_id or uuid4())
    row.organization_id = str(org_id or uuid4())
    row.name = name
    row.key_hash = key_hash
    row.prefix = prefix
    row.is_active = is_active
    row.created_at = datetime.now(timezone.utc)
    row.expires_at = expires_at
    row.last_used_at = last_used_at
    return row


# ── SqlTemplateRepository ──────────────────────────────────────────────────────

class TestSqlTemplateRepository:
    @pytest.fixture
    def repo(self):
        from infrastructure.secondary.database.repositories.template_repository import SqlTemplateRepository
        return SqlTemplateRepository()

    def test_model_to_entity_full(self, repo):
        """Branch: _model_to_entity with all fields including description"""
        row = _make_template_row(description="my desc", project_name_template="PROJ-{name}")
        entity = repo._model_to_entity(row)
        assert entity.name == "tpl"
        assert entity.description == "my desc"
        assert entity.project_name_template == "PROJ-{name}"
        assert entity.is_archived is False

    def test_model_to_entity_none_description(self, repo):
        """Branch: _model_to_entity with description=None → "" """
        row = _make_template_row(description=None)
        entity = repo._model_to_entity(row)
        assert entity.description == ""

    async def test_create_success(self, repo):
        """Branch: create adds model, commits, refreshes"""
        session, mgr = _make_mock_session()
        from domain.entities.template import Template
        tpl = Template(
            id=uuid4(), organization_id=uuid4(), name="my-tpl",
            description="desc", profile_id=uuid4(), created_by=uuid4(),
        )
        with patch("infrastructure.secondary.database.repositories.template_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.create(tpl)
        session.add.assert_called_once()
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert result is not None

    async def test_get_by_id_found(self, repo):
        """Branch: get_by_id finds row → returns Template"""
        session, mgr = _make_mock_session()
        row = _make_template_row()
        result = _make_scalar_result(row)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.template_repository.AsyncSessionLocal", return_value=mgr):
            entity = await repo.get_by_id(uuid4())
        assert entity is not None
        assert entity.name == "tpl"

    async def test_get_by_id_not_found(self, repo):
        """Branch: get_by_id returns None → returns None"""
        session, mgr = _make_mock_session()
        result = _make_scalar_result(None)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.template_repository.AsyncSessionLocal", return_value=mgr):
            entity = await repo.get_by_id(uuid4())
        assert entity is None

    async def test_list_by_organization_returns_list(self, repo):
        """Branch: list_by_organization with results → returns list"""
        session, mgr = _make_mock_session()
        rows = [_make_template_row(), _make_template_row(name="tpl2")]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.template_repository.AsyncSessionLocal", return_value=mgr):
            entities = await repo.list_by_organization(uuid4())
        assert len(entities) == 2

    async def test_list_by_organization_empty(self, repo):
        """Branch: list_by_organization no results → empty list"""
        session, mgr = _make_mock_session()
        result = _make_scalars_result([])
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.template_repository.AsyncSessionLocal", return_value=mgr):
            entities = await repo.list_by_organization(uuid4())
        assert entities == []

    async def test_list_by_organization_include_archived(self, repo):
        """Branch: list_by_organization with include_archived=True → no archive filter"""
        session, mgr = _make_mock_session()
        rows = [_make_template_row(is_archived=True)]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.template_repository.AsyncSessionLocal", return_value=mgr):
            entities = await repo.list_by_organization(uuid4(), include_archived=True)
        assert len(entities) == 1

    async def test_list_by_organization_skip_limit(self, repo):
        """Branch: list_by_organization with skip/limit → pagination applied"""
        session, mgr = _make_mock_session()
        result = _make_scalars_result([])
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.template_repository.AsyncSessionLocal", return_value=mgr):
            entities = await repo.list_by_organization(uuid4(), skip=10, limit=5)
        assert entities == []

    async def test_update_found(self, repo):
        """Branch: update finds model → updates and returns"""
        session, mgr = _make_mock_session()
        model = _make_template_row()
        session.get = AsyncMock(return_value=model)
        from domain.entities.template import Template
        tpl = Template(
            id=UUID(model.id), organization_id=uuid4(), name="updated",
            description="new-desc", profile_id=uuid4(), created_by=uuid4(),
            is_archived=True,
        )
        with patch("infrastructure.secondary.database.repositories.template_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.update(tpl)
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert result is not None

    async def test_update_not_found_raises(self, repo):
        """Branch: update not found → ValueError"""
        session, mgr = _make_mock_session()
        session.get = AsyncMock(return_value=None)
        from domain.entities.template import Template
        tpl = Template(
            id=uuid4(), organization_id=uuid4(), name="ghost",
            description="", profile_id=uuid4(), created_by=uuid4(),
        )
        with patch("infrastructure.secondary.database.repositories.template_repository.AsyncSessionLocal", return_value=mgr):
            with pytest.raises(ValueError, match="Template not found"):
                await repo.update(tpl)

    async def test_delete_found(self, repo):
        """Branch: delete finds model → deletes"""
        session, mgr = _make_mock_session()
        model = _make_template_row()
        session.get = AsyncMock(return_value=model)
        with patch("infrastructure.secondary.database.repositories.template_repository.AsyncSessionLocal", return_value=mgr):
            await repo.delete(uuid4())
        session.delete.assert_awaited_once()
        session.commit.assert_awaited_once()

    async def test_delete_not_found_raises(self, repo):
        """Branch: delete not found → ValueError"""
        session, mgr = _make_mock_session()
        session.get = AsyncMock(return_value=None)
        with patch("infrastructure.secondary.database.repositories.template_repository.AsyncSessionLocal", return_value=mgr):
            with pytest.raises(ValueError, match="Template not found"):
                await repo.delete(uuid4())


# ── SqlConnectorRepository ─────────────────────────────────────────────────────

class TestSqlConnectorRepository:
    @pytest.fixture
    def repo(self):
        from infrastructure.secondary.database.repositories.connector_repository import SqlConnectorRepository
        return SqlConnectorRepository()

    def test_model_to_entity_full(self, repo):
        """Branch: _model_to_entity maps all fields including last_tested_at"""
        from infrastructure.secondary.database.repositories.connector_repository import _model_to_entity
        now = datetime.now(timezone.utc)
        row = _make_connector_row(status="ACTIVO", last_tested_at=now)
        entity = _model_to_entity(row)
        assert entity.connector_type == "GESTOR_TAREAS"
        assert entity.connector_implementation == "JIRA"
        assert entity.name == "jira-conn"
        assert entity.status.value == "ACTIVO"
        assert entity.last_tested_at == now

    def test_model_to_entity_none_dates(self, repo):
        """Branch: _model_to_entity with None updated_at/last_tested_at"""
        from infrastructure.secondary.database.repositories.connector_repository import _model_to_entity
        row = _make_connector_row(last_tested_at=None)
        row.updated_at = None
        entity = _model_to_entity(row)
        assert entity.updated_at is None
        assert entity.last_tested_at is None

    async def test_save_success(self, repo):
        """Branch: save adds model, commits, returns entity"""
        session, mgr = _make_mock_session()
        from domain.entities.connector_instance import ConnectorInstance
        from domain.enums import ConnectorStatus
        ci = ConnectorInstance(
            id=uuid4(), organization_id=uuid4(),
            connector_type="REPO_CODIGO", connector_implementation="GITHUB",
            name="gh-conn", encrypted_credentials=b"enc",
            status=ConnectorStatus.ACTIVO,
        )
        with patch("infrastructure.secondary.database.repositories.connector_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.save(ci)
        session.add.assert_called_once()
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert result is not None

    async def test_save_inactive_status(self, repo):
        """Branch: save with INACTIVO status → conversion works"""
        session, mgr = _make_mock_session()
        from domain.entities.connector_instance import ConnectorInstance
        from domain.enums import ConnectorStatus
        ci = ConnectorInstance(
            id=uuid4(), organization_id=uuid4(),
            connector_type="GESTOR_TAREAS", connector_implementation="TRELLO",
            name="trello", encrypted_credentials=b"x",
            status=ConnectorStatus.INACTIVO,
        )
        with patch("infrastructure.secondary.database.repositories.connector_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.save(ci)
        assert result.status == ConnectorStatus.INACTIVO

    async def test_get_by_id_found(self, repo):
        """Branch: get_by_id finds → returns ConnectorInstance"""
        session, mgr = _make_mock_session()
        row = _make_connector_row()
        result = _make_scalar_result(row)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.connector_repository.AsyncSessionLocal", return_value=mgr):
            entity = await repo.get_by_id(uuid4())
        assert entity is not None
        assert entity.name == "jira-conn"

    async def test_get_by_id_not_found(self, repo):
        """Branch: get_by_id None → returns None"""
        session, mgr = _make_mock_session()
        result = _make_scalar_result(None)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.connector_repository.AsyncSessionLocal", return_value=mgr):
            entity = await repo.get_by_id(uuid4())
        assert entity is None

    async def test_list_by_organization_active_only(self, repo):
        """Branch: list_by_organization with active_only=True → filters active"""
        session, mgr = _make_mock_session()
        rows = [_make_connector_row()]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.connector_repository.AsyncSessionLocal", return_value=mgr):
            entities = await repo.list_by_organization(uuid4(), active_only=True)
        assert len(entities) == 1

    async def test_list_by_organization_all(self, repo):
        """Branch: list_by_organization with active_only=False → no status filter"""
        session, mgr = _make_mock_session()
        rows = [_make_connector_row(status="ACTIVO"), _make_connector_row(status="INACTIVO")]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.connector_repository.AsyncSessionLocal", return_value=mgr):
            entities = await repo.list_by_organization(uuid4(), active_only=False)
        assert len(entities) == 2

    async def test_list_by_organization_empty(self, repo):
        """Branch: list_by_organization no results → empty list"""
        session, mgr = _make_mock_session()
        result = _make_scalars_result([])
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.connector_repository.AsyncSessionLocal", return_value=mgr):
            entities = await repo.list_by_organization(uuid4())
        assert entities == []

    async def test_list_active_delegates(self, repo):
        """Branch: list_active delegates to list_by_organization"""
        session, mgr = _make_mock_session()
        rows = [_make_connector_row()]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.connector_repository.AsyncSessionLocal", return_value=mgr):
            entities = await repo.list_active(uuid4())
        assert len(entities) == 1

    async def test_update_found(self, repo):
        """Branch: update finds → updates fields and returns"""
        session, mgr = _make_mock_session()
        model = _make_connector_row()
        session.get = AsyncMock(return_value=model)
        from domain.entities.connector_instance import ConnectorInstance
        from domain.enums import ConnectorStatus
        ci = ConnectorInstance(
            id=UUID(model.id), organization_id=uuid4(),
            connector_type="SISTEMA_DOCUMENTAL", connector_implementation="CONFLUENCE",
            name="conf", encrypted_credentials=b"new-enc",
            status=ConnectorStatus.ERROR,
        )
        with patch("infrastructure.secondary.database.repositories.connector_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.update(ci)
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert result is not None

    async def test_update_not_found_raises(self, repo):
        """Branch: update not found → ValueError"""
        session, mgr = _make_mock_session()
        session.get = AsyncMock(return_value=None)
        from domain.entities.connector_instance import ConnectorInstance
        from domain.enums import ConnectorStatus
        ci = ConnectorInstance(
            id=uuid4(), organization_id=uuid4(),
            connector_type="GESTOR_TAREAS", connector_implementation="JIRA",
            name="ghost", encrypted_credentials=b"x",
            status=ConnectorStatus.ACTIVO,
        )
        with patch("infrastructure.secondary.database.repositories.connector_repository.AsyncSessionLocal", return_value=mgr):
            with pytest.raises(ValueError, match="Connector not found"):
                await repo.update(ci)

    async def test_delete_found(self, repo):
        """Branch: delete finds → deletes"""
        session, mgr = _make_mock_session()
        model = _make_connector_row()
        session.get = AsyncMock(return_value=model)
        with patch("infrastructure.secondary.database.repositories.connector_repository.AsyncSessionLocal", return_value=mgr):
            await repo.delete(uuid4())
        session.delete.assert_awaited_once()
        session.commit.assert_awaited_once()

    async def test_delete_not_found_raises(self, repo):
        """Branch: delete not found → ValueError"""
        session, mgr = _make_mock_session()
        session.get = AsyncMock(return_value=None)
        with patch("infrastructure.secondary.database.repositories.connector_repository.AsyncSessionLocal", return_value=mgr):
            with pytest.raises(ValueError, match="Connector not found"):
                await repo.delete(uuid4())


# ── SqlCustomRoleRepository ────────────────────────────────────────────────────

class TestSqlCustomRoleRepository:
    @pytest.fixture
    def repo(self):
        from infrastructure.secondary.database.repositories.custom_role_repository import SqlCustomRoleRepository
        return SqlCustomRoleRepository()

    def test_model_to_entity_multiple_permissions(self, repo):
        """Branch: _model_to_entity with multiple permissions"""
        row = _make_custom_role_row(permissions=["VIEW_DASHBOARD", "CREATE_RELEASE", "MANAGE_PROFILES"])
        entity = repo._model_to_entity(row)
        assert entity.name == "viewer"
        assert len(entity.permissions) == 3
        assert entity.is_active is True

    def test_model_to_entity_empty_permissions(self, repo):
        """Branch: _model_to_entity with empty permissions"""
        row = _make_custom_role_row(permissions=[])
        entity = repo._model_to_entity(row)
        assert entity.permissions == []

    def test_model_to_entity_inactive(self, repo):
        """Branch: _model_to_entity with is_active=False"""
        row = _make_custom_role_row(is_active=False)
        entity = repo._model_to_entity(row)
        assert entity.is_active is False

    async def test_create_success(self, repo):
        """Branch: create adds model, commits, returns entity"""
        session, mgr = _make_mock_session()
        from domain.entities.custom_role import CustomRole
        from domain.enums import Permission
        role = CustomRole(
            id=uuid4(), organization_id=uuid4(), name="editor",
            permissions=[Permission.VIEW_DASHBOARD, Permission.CREATE_RELEASE],
        )
        with patch("infrastructure.secondary.database.repositories.custom_role_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.create(role)
        session.add.assert_called_once()
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert result is not None

    async def test_get_by_id_found(self, repo):
        """Branch: get_by_id finds → returns CustomRole"""
        session, mgr = _make_mock_session()
        row = _make_custom_role_row()
        result = _make_scalar_result(row)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.custom_role_repository.AsyncSessionLocal", return_value=mgr):
            entity = await repo.get_by_id(uuid4())
        assert entity is not None
        assert entity.name == "viewer"

    async def test_get_by_id_not_found(self, repo):
        """Branch: get_by_id None → returns None"""
        session, mgr = _make_mock_session()
        result = _make_scalar_result(None)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.custom_role_repository.AsyncSessionLocal", return_value=mgr):
            entity = await repo.get_by_id(uuid4())
        assert entity is None

    async def test_list_by_organization_returns_list(self, repo):
        """Branch: list_by_organization with results → returns list"""
        session, mgr = _make_mock_session()
        rows = [_make_custom_role_row(), _make_custom_role_row(name="admin")]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.custom_role_repository.AsyncSessionLocal", return_value=mgr):
            entities = await repo.list_by_organization(uuid4())
        assert len(entities) == 2

    async def test_list_by_organization_empty(self, repo):
        """Branch: list_by_organization no results → empty list"""
        session, mgr = _make_mock_session()
        result = _make_scalars_result([])
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.custom_role_repository.AsyncSessionLocal", return_value=mgr):
            entities = await repo.list_by_organization(uuid4())
        assert entities == []

    async def test_update_found(self, repo):
        """Branch: update finds → updates fields and returns"""
        session, mgr = _make_mock_session()
        model = _make_custom_role_row()
        session.get = AsyncMock(return_value=model)
        from domain.entities.custom_role import CustomRole
        from domain.enums import Permission
        role = CustomRole(
            id=UUID(model.id), organization_id=uuid4(), name="updated-role",
            permissions=[Permission.MANAGE_ROLES], is_active=False,
        )
        with patch("infrastructure.secondary.database.repositories.custom_role_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.update(role)
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert result is not None

    async def test_update_not_found_raises(self, repo):
        """Branch: update not found → ValueError"""
        session, mgr = _make_mock_session()
        session.get = AsyncMock(return_value=None)
        from domain.entities.custom_role import CustomRole
        from domain.enums import Permission
        role = CustomRole(
            id=uuid4(), organization_id=uuid4(), name="ghost",
            permissions=[Permission.VIEW_DASHBOARD],
        )
        with patch("infrastructure.secondary.database.repositories.custom_role_repository.AsyncSessionLocal", return_value=mgr):
            with pytest.raises(ValueError, match="Custom role not found"):
                await repo.update(role)

    async def test_delete_found(self, repo):
        """Branch: delete finds → deletes"""
        session, mgr = _make_mock_session()
        model = _make_custom_role_row()
        session.get = AsyncMock(return_value=model)
        with patch("infrastructure.secondary.database.repositories.custom_role_repository.AsyncSessionLocal", return_value=mgr):
            await repo.delete(uuid4())
        session.delete.assert_awaited_once()
        session.commit.assert_awaited_once()

    async def test_delete_not_found_raises(self, repo):
        """Branch: delete not found → ValueError"""
        session, mgr = _make_mock_session()
        session.get = AsyncMock(return_value=None)
        with patch("infrastructure.secondary.database.repositories.custom_role_repository.AsyncSessionLocal", return_value=mgr):
            with pytest.raises(ValueError, match="Custom role not found"):
                await repo.delete(uuid4())


# ── SqlVerificationRuleRepository ──────────────────────────────────────────────

class TestSqlVerificationRuleRepository:
    @pytest.fixture
    def repo(self):
        from infrastructure.secondary.database.repositories.rule_repository import SqlVerificationRuleRepository
        return SqlVerificationRuleRepository()

    def test_model_to_entity_full(self, repo):
        """Branch: _model_to_entity with all fields"""
        conn_id = uuid4()
        row = _make_rule_row(severity="CRITICAL", connector_instance_id=conn_id, params={"key": "val"})
        entity = repo._model_to_entity(row)
        assert entity.rule_template == "check_version"
        assert entity.severity.value == "CRITICAL"
        assert entity.params == {"key": "val"}
        assert entity.connector_instance_id == conn_id
        assert entity.is_active is True

    def test_model_to_entity_none_params(self, repo):
        """Branch: _model_to_entity with params=None → {}"""
        row = _make_rule_row(params=None)
        entity = repo._model_to_entity(row)
        assert entity.params == {}

    def test_model_to_entity_none_connector(self, repo):
        """Branch: _model_to_entity with connector_instance_id=None"""
        row = _make_rule_row(connector_instance_id=None)
        entity = repo._model_to_entity(row)
        assert entity.connector_instance_id is None

    def test_entity_to_model_attrs(self, repo):
        """Branch: _entity_to_model_attrs maps all fields"""
        from domain.entities.verification_rule import VerificationRule
        from domain.enums import SeverityType
        rule = VerificationRule(
            id=uuid4(), profile_id=uuid4(),
            rule_template="check_docs", severity=SeverityType.MEDIUM,
            params={"doc": "readme"}, connector_instance_id=uuid4(),
            display_order=2, is_active=False,
        )
        attrs = repo._entity_to_model_attrs(rule)
        assert attrs["severity"] == "MEDIUM"
        assert attrs["params"] == {"doc": "readme"}
        assert attrs["is_active"] is False

    async def test_create_success(self, repo):
        """Branch: create adds model, commits, returns entity"""
        session, mgr = _make_mock_session()
        from domain.entities.verification_rule import VerificationRule
        from domain.enums import SeverityType
        rule = VerificationRule(
            id=uuid4(), profile_id=uuid4(),
            rule_template="check_tests", severity=SeverityType.HIGH,
        )
        with patch("infrastructure.secondary.database.repositories.rule_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.create(rule)
        session.add.assert_called_once()
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert result is not None

    async def test_get_by_id_found(self, repo):
        """Branch: get_by_id finds → returns VerificationRule"""
        session, mgr = _make_mock_session()
        row = _make_rule_row()
        result = _make_scalar_result(row)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.rule_repository.AsyncSessionLocal", return_value=mgr):
            entity = await repo.get_by_id(uuid4())
        assert entity is not None
        assert entity.rule_template == "check_version"

    async def test_get_by_id_not_found(self, repo):
        """Branch: get_by_id None → returns None"""
        session, mgr = _make_mock_session()
        result = _make_scalar_result(None)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.rule_repository.AsyncSessionLocal", return_value=mgr):
            entity = await repo.get_by_id(uuid4())
        assert entity is None

    async def test_list_all_returns_list(self, repo):
        """Branch: list_all with results → returns list"""
        session, mgr = _make_mock_session()
        rows = [_make_rule_row(), _make_rule_row(rule_template="check_other")]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.rule_repository.AsyncSessionLocal", return_value=mgr):
            entities = await repo.list_all()
        assert len(entities) == 2

    async def test_list_all_empty(self, repo):
        """Branch: list_all no results → empty list"""
        session, mgr = _make_mock_session()
        result = _make_scalars_result([])
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.rule_repository.AsyncSessionLocal", return_value=mgr):
            entities = await repo.list_all()
        assert entities == []

    async def test_list_by_profile_returns_list(self, repo):
        """Branch: list_by_profile with results → returns ordered list"""
        session, mgr = _make_mock_session()
        rows = [_make_rule_row(), _make_rule_row(display_order=2)]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.rule_repository.AsyncSessionLocal", return_value=mgr):
            entities = await repo.list_by_profile(uuid4())
        assert len(entities) == 2

    async def test_list_by_profile_empty(self, repo):
        """Branch: list_by_profile no results → empty list"""
        session, mgr = _make_mock_session()
        result = _make_scalars_result([])
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.rule_repository.AsyncSessionLocal", return_value=mgr):
            entities = await repo.list_by_profile(uuid4())
        assert entities == []

    async def test_update_found(self, repo):
        """Branch: update finds → updates via setattr, returns entity"""
        session, mgr = _make_mock_session()
        model = _make_rule_row()
        session.get = AsyncMock(return_value=model)
        from domain.entities.verification_rule import VerificationRule
        from domain.enums import SeverityType
        rule = VerificationRule(
            id=UUID(model.id), profile_id=uuid4(),
            rule_template="updated_rule", severity=SeverityType.LOW,
            params={"updated": True}, display_order=99, is_active=False,
        )
        with patch("infrastructure.secondary.database.repositories.rule_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.update(rule)
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert result is not None

    async def test_update_not_found_raises(self, repo):
        """Branch: update not found → ValueError"""
        session, mgr = _make_mock_session()
        session.get = AsyncMock(return_value=None)
        from domain.entities.verification_rule import VerificationRule
        from domain.enums import SeverityType
        rule = VerificationRule(
            id=uuid4(), profile_id=uuid4(),
            rule_template="ghost", severity=SeverityType.INFO,
        )
        with patch("infrastructure.secondary.database.repositories.rule_repository.AsyncSessionLocal", return_value=mgr):
            with pytest.raises(ValueError, match="Rule not found"):
                await repo.update(rule)

    async def test_delete_found(self, repo):
        """Branch: delete finds → deletes"""
        session, mgr = _make_mock_session()
        model = _make_rule_row()
        session.get = AsyncMock(return_value=model)
        with patch("infrastructure.secondary.database.repositories.rule_repository.AsyncSessionLocal", return_value=mgr):
            await repo.delete(uuid4())
        session.delete.assert_awaited_once()
        session.commit.assert_awaited_once()

    async def test_delete_not_found_raises(self, repo):
        """Branch: delete not found → ValueError"""
        session, mgr = _make_mock_session()
        session.get = AsyncMock(return_value=None)
        with patch("infrastructure.secondary.database.repositories.rule_repository.AsyncSessionLocal", return_value=mgr):
            with pytest.raises(ValueError, match="Rule not found"):
                await repo.delete(uuid4())


# ── SqlAPIKeyRepository ────────────────────────────────────────────────────────

class TestSqlAPIKeyRepository:
    @pytest.fixture
    def repo(self):
        from infrastructure.secondary.database.repositories.api_key_repository import SqlAPIKeyRepository
        return SqlAPIKeyRepository()

    def test_model_to_entity_full(self, repo):
        """Branch: _model_to_entity with all fields"""
        from infrastructure.secondary.database.repositories.api_key_repository import _model_to_entity
        now = datetime.now(timezone.utc)
        expires = datetime(2025, 12, 31, tzinfo=timezone.utc)
        row = _make_api_key_row(expires_at=expires, last_used_at=now)
        entity = _model_to_entity(row)
        assert entity.name == "my-key"
        assert entity.key_hash == "abc123"
        assert entity.prefix == "sv_s0"
        assert entity.is_active is True
        assert entity.expires_at == expires
        assert entity.last_used_at == now

    def test_model_to_entity_none_dates(self, repo):
        """Branch: _model_to_entity with None expires_at/last_used_at"""
        from infrastructure.secondary.database.repositories.api_key_repository import _model_to_entity
        row = _make_api_key_row(expires_at=None, last_used_at=None)
        entity = _model_to_entity(row)
        assert entity.expires_at is None
        assert entity.last_used_at is None

    async def test_save_success(self, repo):
        """Branch: save adds model, commits, returns entity"""
        session, mgr = _make_mock_session()
        from domain.entities.api_key import APIKey
        key = APIKey(
            id=uuid4(), user_id=uuid4(), organization_id=uuid4(),
            name="prod-key", key_hash="hash123", prefix="sv_p0",
            is_active=True,
        )
        with patch("infrastructure.secondary.database.repositories.api_key_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.save(key)
        session.add.assert_called_once()
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert result is not None

    async def test_get_by_id_found(self, repo):
        """Branch: get_by_id finds → returns APIKey"""
        session, mgr = _make_mock_session()
        row = _make_api_key_row()
        result = _make_scalar_result(row)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.api_key_repository.AsyncSessionLocal", return_value=mgr):
            entity = await repo.get_by_id(uuid4())
        assert entity is not None
        assert entity.name == "my-key"

    async def test_get_by_id_not_found(self, repo):
        """Branch: get_by_id None → returns None"""
        session, mgr = _make_mock_session()
        result = _make_scalar_result(None)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.api_key_repository.AsyncSessionLocal", return_value=mgr):
            entity = await repo.get_by_id(uuid4())
        assert entity is None

    async def test_get_by_hash_found(self, repo):
        """Branch: get_by_hash finds → returns APIKey"""
        session, mgr = _make_mock_session()
        row = _make_api_key_row(key_hash="findme")
        result = _make_scalar_result(row)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.api_key_repository.AsyncSessionLocal", return_value=mgr):
            entity = await repo.get_by_hash("findme")
        assert entity is not None
        assert entity.key_hash == "findme"

    async def test_get_by_hash_not_found(self, repo):
        """Branch: get_by_hash None → returns None"""
        session, mgr = _make_mock_session()
        result = _make_scalar_result(None)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.api_key_repository.AsyncSessionLocal", return_value=mgr):
            entity = await repo.get_by_hash("nope")
        assert entity is None

    async def test_list_by_organization_returns_list(self, repo):
        """Branch: list_by_organization with results"""
        session, mgr = _make_mock_session()
        rows = [_make_api_key_row(), _make_api_key_row(name="key2")]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.api_key_repository.AsyncSessionLocal", return_value=mgr):
            entities = await repo.list_by_organization(uuid4())
        assert len(entities) == 2

    async def test_list_by_organization_empty(self, repo):
        """Branch: list_by_organization no results → empty list"""
        session, mgr = _make_mock_session()
        result = _make_scalars_result([])
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.api_key_repository.AsyncSessionLocal", return_value=mgr):
            entities = await repo.list_by_organization(uuid4())
        assert entities == []

    async def test_list_by_user_returns_list(self, repo):
        """Branch: list_by_user with results"""
        session, mgr = _make_mock_session()
        rows = [_make_api_key_row()]
        result = _make_scalars_result(rows)
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.api_key_repository.AsyncSessionLocal", return_value=mgr):
            entities = await repo.list_by_user(uuid4())
        assert len(entities) == 1

    async def test_list_by_user_empty(self, repo):
        """Branch: list_by_user no results → empty list"""
        session, mgr = _make_mock_session()
        result = _make_scalars_result([])
        session.execute = AsyncMock(return_value=result)
        with patch("infrastructure.secondary.database.repositories.api_key_repository.AsyncSessionLocal", return_value=mgr):
            entities = await repo.list_by_user(uuid4())
        assert entities == []

    async def test_update_found(self, repo):
        """Branch: update finds → updates fields and returns"""
        session, mgr = _make_mock_session()
        model = _make_api_key_row()
        session.get = AsyncMock(return_value=model)
        from domain.entities.api_key import APIKey
        now = datetime.now(timezone.utc)
        key = APIKey(
            id=UUID(model.id), user_id=uuid4(), organization_id=uuid4(),
            name="renamed", key_hash="h", prefix="p",
            is_active=False, expires_at=now, last_used_at=now,
        )
        with patch("infrastructure.secondary.database.repositories.api_key_repository.AsyncSessionLocal", return_value=mgr):
            result = await repo.update(key)
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert result is not None

    async def test_update_not_found_raises(self, repo):
        """Branch: update not found → ValueError"""
        session, mgr = _make_mock_session()
        session.get = AsyncMock(return_value=None)
        from domain.entities.api_key import APIKey
        key = APIKey(
            id=uuid4(), user_id=uuid4(), organization_id=uuid4(),
            name="ghost", key_hash="gh", prefix="g",
            is_active=True,
        )
        with patch("infrastructure.secondary.database.repositories.api_key_repository.AsyncSessionLocal", return_value=mgr):
            with pytest.raises(ValueError, match="API key not found"):
                await repo.update(key)

    async def test_delete_found(self, repo):
        """Branch: delete finds → deletes"""
        session, mgr = _make_mock_session()
        model = _make_api_key_row()
        session.get = AsyncMock(return_value=model)
        with patch("infrastructure.secondary.database.repositories.api_key_repository.AsyncSessionLocal", return_value=mgr):
            await repo.delete(uuid4())
        session.delete.assert_awaited_once()
        session.commit.assert_awaited_once()

    async def test_delete_not_found_raises(self, repo):
        """Branch: delete not found → ValueError"""
        session, mgr = _make_mock_session()
        session.get = AsyncMock(return_value=None)
        with patch("infrastructure.secondary.database.repositories.api_key_repository.AsyncSessionLocal", return_value=mgr):
            with pytest.raises(ValueError, match="API key not found"):
                await repo.delete(uuid4())

    def test_hash_key(self, repo):
        """Branch: hash_key static method returns sha256 hex digest"""
        result = repo.hash_key("test-key")
        assert isinstance(result, str)
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

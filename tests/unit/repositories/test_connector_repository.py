import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from domain.entities.connector_instance import ConnectorInstance
from domain.enums import ConnectorStatus

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    session.get = AsyncMock(return_value=None)
    session.execute = AsyncMock()
    return session


@pytest.fixture
def repo(mock_session):
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_session)
    ctx.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "infrastructure.secondary.database.repositories.connector_repository.select",
        return_value=MagicMock(),
    ):
        with patch(
            "infrastructure.secondary.database.repositories.connector_repository.AsyncSessionLocal",
            return_value=ctx,
        ):
            with patch(
                "infrastructure.secondary.database.repositories.connector_repository.ConnectorInstanceModel",
                side_effect=lambda **kw: (lambda m: (m.configure_mock(**kw), m)[1])(MagicMock()) if kw else MagicMock(),
            ):
                from infrastructure.secondary.database.repositories.connector_repository import (
                    SqlConnectorRepository,
                )
                yield SqlConnectorRepository()


class TestSave:
    async def test_save_connector_success(self, repo, mock_session):
        connector = ConnectorInstance(
            id=uuid4(),
            organization_id=uuid4(),
            connector_type="REPO_CODIGO",
            connector_implementation="GITLAB",
            name="My GitLab",
            encrypted_credentials=b"encrypted",
            status=ConnectorStatus.ACTIVO,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        result = await repo.save(connector)
        assert result is not None
        assert result.name == "My GitLab"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()


class TestGetById:
    async def test_get_by_id_returns_connector(self, repo, mock_session):
        row = MagicMock()
        row.id = uuid4()
        row.organization_id = uuid4()
        row.connector_type = "REPO_CODIGO"
        row.connector_implementation = "GITLAB"
        row.name = "Test Connector"
        row.config_encrypted = b"enc"
        row.status = ConnectorStatus.ACTIVO.value
        row.created_at = datetime.now(timezone.utc)
        row.updated_at = None
        row.last_tested_at = None

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = row
        mock_session.execute.return_value = result_mock

        connector = await repo.get_by_id(uuid4())
        assert connector is not None
        assert connector.name == "Test Connector"

    async def test_get_by_id_returns_none(self, repo, mock_session):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result_mock

        connector = await repo.get_by_id(uuid4())
        assert connector is None


class TestListByOrganization:
    async def test_list_by_organization_returns_connectors(self, repo, mock_session):
        row = MagicMock()
        row.id = uuid4()
        row.organization_id = uuid4()
        row.connector_type = "GESTOR_TAREAS"
        row.connector_implementation = "JIRA"
        row.name = "JIRA Instance"
        row.config_encrypted = b"enc"
        row.status = ConnectorStatus.ACTIVO.value
        row.created_at = datetime.now(timezone.utc)
        row.updated_at = None
        row.last_tested_at = None

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [row]
        mock_session.execute.return_value = result_mock

        connectors = await repo.list_by_organization(uuid4())
        assert len(connectors) == 1

    async def test_list_active_returns_connectors(self, repo, mock_session):
        row = MagicMock()
        row.id = uuid4()
        row.organization_id = uuid4()
        row.connector_type = "GESTOR_TAREAS"
        row.connector_implementation = "JIRA"
        row.name = "JIRA Active"
        row.config_encrypted = b"enc"
        row.status = ConnectorStatus.ACTIVO.value
        row.created_at = datetime.now(timezone.utc)
        row.updated_at = None
        row.last_tested_at = None

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [row]
        mock_session.execute.return_value = result_mock

        connectors = await repo.list_active(uuid4())
        assert len(connectors) == 1


class TestUpdate:
    async def test_update_connector_success(self, repo, mock_session):
        connector_id = uuid4()
        model = MagicMock()
        model.id = connector_id
        mock_session.get.return_value = model

        connector = ConnectorInstance(
            id=connector_id,
            organization_id=uuid4(),
            connector_type="GESTOR_TAREAS",
            connector_implementation="JIRA",
            name="Updated JIRA",
            encrypted_credentials=b"new",
            status=ConnectorStatus.INACTIVO,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            last_tested_at=None,
        )
        result = await repo.update(connector)
        assert result is not None
        mock_session.commit.assert_called_once()

    async def test_update_not_found(self, repo, mock_session):
        mock_session.get.return_value = None
        connector = ConnectorInstance(
            id=uuid4(),
            organization_id=uuid4(),
            connector_type="GESTOR_TAREAS",
            connector_implementation="JIRA",
            name="Nope",
            encrypted_credentials=b"enc",
            status=ConnectorStatus.ACTIVO,
            created_at=datetime.now(timezone.utc),
        )
        with pytest.raises(ValueError, match="Connector not found"):
            await repo.update(connector)


class TestDelete:
    async def test_delete_connector_success(self, repo, mock_session):
        model = MagicMock()
        mock_session.get.return_value = model

        await repo.delete(uuid4())

        mock_session.delete.assert_called_once_with(model)
        mock_session.commit.assert_called_once()

    async def test_delete_not_found(self, repo, mock_session):
        mock_session.get.return_value = None
        with pytest.raises(ValueError, match="Connector not found"):
            await repo.delete(uuid4())

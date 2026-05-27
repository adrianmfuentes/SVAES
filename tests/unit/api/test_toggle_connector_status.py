import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from application.use_cases.others.toggle_connector_status import (
    ToggleConnectorStatusUseCase,
)
from domain.enums import ConnectorStatus
from domain.exceptions import EntityNotFoundError

pytestmark = pytest.mark.unit


@pytest.fixture
def connector_repo():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.update = AsyncMock()
    return repo


@pytest.fixture
def use_case(connector_repo):
    return ToggleConnectorStatusUseCase(connector_repo)


@pytest.fixture
def sample_connector():
    connector = MagicMock()
    connector.id = uuid4()
    connector.status = ConnectorStatus.ACTIVO
    return connector


class TestToggleConnectorStatusSuccess:
    async def test_activate_connector(self, use_case, connector_repo, sample_connector):
        sample_connector.status = ConnectorStatus.INACTIVO
        connector_repo.get_by_id.return_value = sample_connector
        connector_repo.update.return_value = sample_connector

        result = await use_case.execute(sample_connector.id, ConnectorStatus.ACTIVO)

        assert result.status == ConnectorStatus.ACTIVO
        connector_repo.get_by_id.assert_called_once_with(sample_connector.id)
        connector_repo.update.assert_called_once_with(sample_connector)

    async def test_deactivate_connector(self, use_case, connector_repo, sample_connector):
        sample_connector.status = ConnectorStatus.ACTIVO
        connector_repo.get_by_id.return_value = sample_connector
        connector_repo.update.return_value = sample_connector

        result = await use_case.execute(sample_connector.id, ConnectorStatus.INACTIVO)

        assert result.status == ConnectorStatus.INACTIVO
        connector_repo.update.assert_called_once_with(sample_connector)

    async def test_toggle_error_status(self, use_case, connector_repo, sample_connector):
        sample_connector.status = ConnectorStatus.ACTIVO
        connector_repo.get_by_id.return_value = sample_connector
        connector_repo.update.return_value = sample_connector

        result = await use_case.execute(sample_connector.id, ConnectorStatus.ERROR)

        assert result.status == ConnectorStatus.ERROR


class TestToggleConnectorStatusFailure:
    async def test_connector_not_found(self, use_case, connector_repo):
        conn_id = uuid4()
        connector_repo.get_by_id.return_value = None

        with pytest.raises(EntityNotFoundError, match="Conector no encontrado"):
            await use_case.execute(conn_id, ConnectorStatus.ACTIVO)

    async def test_connector_not_found_does_not_update(self, use_case, connector_repo):
        connector_repo.get_by_id.return_value = None

        with pytest.raises(EntityNotFoundError):
            await use_case.execute(uuid4(), ConnectorStatus.ACTIVO)

        connector_repo.update.assert_not_called()

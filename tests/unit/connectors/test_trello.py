import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock

pytestmark = pytest.mark.unit


@pytest.fixture
def connector():
    from infrastructure.secondary.connectors.task_management.trello_connector import (
        TrelloConnector,
    )
    return TrelloConnector()


class TestTrelloConnectorMetadata:
    def test_connector_type(self, connector):
        assert connector.connector_type == "GESTOR_TAREAS"

    def test_connector_implementation(self, connector):
        assert connector.connector_implementation == "TRELLO"

    def test_get_connector_type(self, connector):
        assert connector.get_connector_type() == "GESTOR_TAREAS"

    def test_get_connector_implementation(self, connector):
        assert connector.get_connector_implementation() == "TRELLO"

    def test_get_metadata(self, connector):
        metadata = connector.get_metadata()
        assert metadata["name"] == "Trello"
        assert metadata["version"] == "1.0"
        assert "card" in metadata["artifact_types"]


class TestTrelloConnectorAuth:
    def test_build_auth_params(self, connector):
        params = connector._build_auth_params({"api_key": "key123", "token": "tok456"})
        assert params["key"] == "key123"
        assert params["token"] == "tok456"


class TestTrelloConnectorConnection:
    async def test_test_connection_success(self, connector):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "__aenter__", AsyncMock(return_value=mock_client))
            mp.setattr(httpx.AsyncClient, "__aexit__", AsyncMock(return_value=False))

            result = await connector.test_connection({"api_key": "key", "token": "tok"})
            assert result is True

    async def test_test_connection_failure(self, connector):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "__aenter__", AsyncMock(return_value=mock_client))
            mp.setattr(httpx.AsyncClient, "__aexit__", AsyncMock(return_value=False))

            result = await connector.test_connection({"api_key": "bad", "token": "bad"})
            assert result is False


class TestTrelloConnectorFetch:
    async def test_fetch_artifact_success(self, connector):
        expected = {"id": "card1", "name": "My Card"}
        mock_response = MagicMock()
        mock_response.json.return_value = expected
        mock_response.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "__aenter__", AsyncMock(return_value=mock_client))
            mp.setattr(httpx.AsyncClient, "__aexit__", AsyncMock(return_value=False))

            result = await connector.fetch_artifact("card1", {"api_key": "key", "token": "tok"})
            assert result == expected

    async def test_fetch_artifact_error(self, connector):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "__aenter__", AsyncMock(return_value=mock_client))
            mp.setattr(httpx.AsyncClient, "__aexit__", AsyncMock(return_value=False))

            with pytest.raises(httpx.HTTPStatusError):
                await connector.fetch_artifact("fake", {"api_key": "key", "token": "tok"})


class TestTrelloConnectorList:
    async def test_list_artifacts_with_board_id(self, connector):
        items = [{"id": "card1", "name": "Card 1"}]
        mock_response = MagicMock()
        mock_response.json.return_value = items
        mock_response.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "__aenter__", AsyncMock(return_value=mock_client))
            mp.setattr(httpx.AsyncClient, "__aexit__", AsyncMock(return_value=False))

            result = await connector.list_artifacts({}, {"api_key": "key", "token": "tok", "board_id": "board1"})
            assert result == items

    async def test_list_artifacts_without_board_id(self, connector):
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "__aenter__", AsyncMock(return_value=mock_client))
            mp.setattr(httpx.AsyncClient, "__aexit__", AsyncMock(return_value=False))

            result = await connector.list_artifacts({}, {"api_key": "key", "token": "tok"})
            assert result == []

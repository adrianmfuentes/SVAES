import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock

pytestmark = pytest.mark.unit


@pytest.fixture
def connector():
    from infrastructure.secondary.connectors.change_management.redmine_connector import (
        RedmineConnector,
    )
    return RedmineConnector()


class TestRedmineConnectorMetadata:
    def test_connector_type(self, connector):
        assert connector.connector_type == "GESTION_CAMBIOS"

    def test_connector_implementation(self, connector):
        assert connector.connector_implementation == "REDMINE"

    def test_get_connector_type(self, connector):
        assert connector.get_connector_type() == "GESTION_CAMBIOS"

    def test_get_connector_implementation(self, connector):
        assert connector.get_connector_implementation() == "REDMINE"

    def test_get_metadata(self, connector):
        metadata = connector.get_metadata()
        assert metadata["name"] == "Redmine"
        assert metadata["version"] == "1.0"
        assert "issue" in metadata["artifact_types"]


class TestRedmineConnectorConnection:
    async def test_test_connection_success(self, connector):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "__aenter__", AsyncMock(return_value=mock_client))
            mp.setattr(httpx.AsyncClient, "__aexit__", AsyncMock(return_value=False))

            result = await connector.test_connection({"api_key": "test-key"})
            assert result is True

    async def test_test_connection_failure(self, connector):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "__aenter__", AsyncMock(return_value=mock_client))
            mp.setattr(httpx.AsyncClient, "__aexit__", AsyncMock(return_value=False))

            result = await connector.test_connection({"api_key": "bad-key"})
            assert result is False


class TestRedmineConnectorFetch:
    async def test_fetch_artifact_success(self, connector):
        expected = {"id": 1, "subject": "Test Issue"}
        mock_response = MagicMock()
        mock_response.json.return_value = {"issue": expected}
        mock_response.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "__aenter__", AsyncMock(return_value=mock_client))
            mp.setattr(httpx.AsyncClient, "__aexit__", AsyncMock(return_value=False))

            result = await connector.fetch_artifact("123", {"api_key": "key"})
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
                await connector.fetch_artifact("999", {"api_key": "key"})


class TestRedmineConnectorList:
    async def test_list_artifacts_success(self, connector):
        expected = [{"id": 1, "subject": "Issue 1"}, {"id": 2, "subject": "Issue 2"}]
        mock_response = MagicMock()
        mock_response.json.return_value = {"issues": expected}
        mock_response.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "__aenter__", AsyncMock(return_value=mock_client))
            mp.setattr(httpx.AsyncClient, "__aexit__", AsyncMock(return_value=False))

            result = await connector.list_artifacts({}, {"api_key": "key"})
            assert result == expected

    async def test_list_artifacts_with_project_id(self, connector):
        mock_response = MagicMock()
        mock_response.json.return_value = {"issues": []}
        mock_response.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "__aenter__", AsyncMock(return_value=mock_client))
            mp.setattr(httpx.AsyncClient, "__aexit__", AsyncMock(return_value=False))

            result = await connector.list_artifacts({}, {"api_key": "key", "project_id": "42"})
            assert result == []


class TestRedmineConnectorAuth:
    def test_build_auth(self, connector):
        auth = connector._build_auth({"api_key": "my-api-key"})
        assert auth["X-Redmine-API-Key"] == "my-api-key"
        assert auth["Accept"] == "application/json"

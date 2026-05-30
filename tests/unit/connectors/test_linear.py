import pytest
from unittest.mock import AsyncMock, MagicMock

pytestmark = pytest.mark.unit


@pytest.fixture
def connector():
    from infrastructure.secondary.connectors.task_management.linear_connector import (
        LinearConnector,
    )
    return LinearConnector()


class TestLinearConnectorMetadata:
    def test_connector_type(self, connector):
        assert connector.get_connector_type() == "GESTOR_TAREAS"

    def test_connector_implementation(self, connector):
        assert connector.get_connector_implementation() == "LINEAR"

    def test_get_artifact_types(self, connector):
        types = connector.get_artifact_types()
        assert "issue" in types
        assert "cycle" in types
        assert "project" in types

    def test_get_metadata(self, connector):
        metadata = connector.get_metadata()
        assert metadata["name"] == "Linear"
        assert metadata["version"] == "1.0"


class TestLinearConnectorHeaders:
    def test_build_headers(self, connector):
        headers = connector._build_headers({"api_key": "lin_api_key"})
        assert headers["Content-Type"] == "application/json"
        assert headers["Authorization"] == "Bearer lin_api_key"


class TestLinearConnectorUrls:
    def test_base_url(self, connector):
        assert connector.BASE_URL == "https://api.linear.app/graphql"

    def test_get_health_url(self, connector):
        url = connector._get_health_url({})
        assert url == "https://api.linear.app/graphql"

    def test_get_fetch_url(self, connector):
        url = connector._get_fetch_url("ISSUE-123", {})
        assert url == "https://api.linear.app/graphql"

    def test_get_fetch_params_returns_none(self, connector):
        assert connector._get_fetch_params({}) is None

    def test_get_list_url(self, connector):
        url = connector._get_list_url({}, {})
        assert url == "https://api.linear.app/graphql"

    def test_get_list_params_returns_none(self, connector):
        assert connector._get_list_params({}, {}) is None

    def test_get_list_json_returns_none(self, connector):
        assert connector._get_list_json({}, {}) is None

    def test_get_results_key(self, connector):
        assert connector._get_results_key() == ""


class TestLinearConnectorConnection:
    async def test_test_connection_success(self, connector):
        mock_response = MagicMock()
        mock_response.status_code = 200
        connector._post = AsyncMock(return_value=mock_response)

        result = await connector.test_connection({"api_key": "key"})
        assert result is True

    async def test_test_connection_failure(self, connector):
        mock_response = MagicMock()
        mock_response.status_code = 401
        connector._post = AsyncMock(return_value=mock_response)

        result = await connector.test_connection({"api_key": "bad"})
        assert result is False


class TestLinearConnectorFetch:
    async def test_fetch_artifact_success(self, connector):
        expected = {"data": {"issue": {"id": "ISSUE-1", "title": "Test"}}}
        mock_response = MagicMock()
        mock_response.json.return_value = expected
        mock_response.raise_for_status = MagicMock()
        connector._post = AsyncMock(return_value=mock_response)

        result = await connector.fetch_artifact("ISSUE-1", {})
        assert result == expected


class TestLinearConnectorList:
    async def test_list_artifacts_success(self, connector):
        items = [{"id": "1"}, {"id": "2"}]
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"issues": {"nodes": items}}}
        mock_response.raise_for_status = MagicMock()
        connector._post = AsyncMock(return_value=mock_response)

        result = await connector.list_artifacts({"first": 10}, {})
        assert result == items

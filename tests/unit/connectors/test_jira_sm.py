import pytest
from unittest.mock import AsyncMock, MagicMock, patch

pytestmark = pytest.mark.unit


@pytest.fixture
def connector():
    from infrastructure.secondary.connectors.change_management.jira_sm_connector import (
        JiraServiceManagementConnector,
    )
    return JiraServiceManagementConnector()


class TestJiraSMConnectorMetadata:
    def test_connector_type(self, connector):
        assert connector.get_connector_type() == "GESTION_CAMBIOS"

    def test_connector_implementation(self, connector):
        assert connector.get_connector_implementation() == "JIRA_SM"

    def test_get_artifact_types(self, connector):
        types = connector.get_artifact_types()
        assert "request" in types
        assert "request_type" in types
        assert "approval" in types

    def test_get_metadata(self, connector):
        metadata = connector.get_metadata()
        assert metadata["name"] == "JiraServiceManagement"
        assert metadata["version"] == "1.0"


class TestJiraSMConnectorUrls:
    def test_get_health_url_without_site_id(self, connector):
        url = connector._get_health_url({})
        assert "/rest/servicedesk/1/servicedesk" in url

    def test_get_health_url_with_site_id(self, connector):
        url = connector._get_health_url({"site_id": "abc123"})
        assert "siteId=abc123" in url

    def test_get_fetch_url(self, connector):
        url = connector._get_fetch_url("REQ-123", {})
        assert "/rest/servicedesk/1/request/REQ-123" in url

    def test_get_fetch_params_returns_none(self, connector):
        assert connector._get_fetch_params({}) is None

    def test_get_list_url_with_service_desk(self, connector):
        url = connector._get_list_url({}, {"service_desk_id": "10"})
        assert "/servicedesk/10/request" in url

    def test_get_list_url_without_service_desk(self, connector):
        url = connector._get_list_url({}, {})
        assert "/rest/servicedesk/1/request" in url

    def test_get_list_params_with_service_desk(self, connector):
        params = connector._get_list_params({"request_type": "incident"}, {"service_desk_id": "10"})
        assert params is not None
        assert params["limit"] == 50

    def test_get_list_params_without_service_desk(self, connector):
        params = connector._get_list_params({}, {})
        assert params == {"limit": 50}

    def test_get_list_json_returns_none(self, connector):
        assert connector._get_list_json({}, {}) is None

    def test_get_results_key(self, connector):
        assert connector._get_results_key() == "values"


class TestJiraSMConnectorConnection:
    async def test_test_connection_success(self, connector):
        mock_response = MagicMock()
        mock_response.status_code = 200
        connector._get = AsyncMock(return_value=mock_response)

        result = await connector.test_connection({})
        assert result is True

    async def test_test_connection_failure(self, connector):
        mock_response = MagicMock()
        mock_response.status_code = 401
        connector._get = AsyncMock(return_value=mock_response)

        result = await connector.test_connection({})
        assert result is False


class TestJiraSMConnectorFetch:
    async def test_fetch_artifact_success(self, connector):
        expected = {"id": "REQ-1", "summary": "Test"}
        mock_response = MagicMock()
        mock_response.json.return_value = expected
        mock_response.raise_for_status = MagicMock()
        connector._get = AsyncMock(return_value=mock_response)

        result = await connector.fetch_artifact("REQ-1", {})
        assert result == expected


class TestJiraSMConnectorList:
    async def test_list_artifacts_success(self, connector):
        items = [{"id": "REQ-1"}, {"id": "REQ-2"}]
        mock_response = MagicMock()
        mock_response.json.return_value = {"values": items}
        mock_response.raise_for_status = MagicMock()
        connector._get = AsyncMock(return_value=mock_response)

        result = await connector.list_artifacts({}, {})
        assert result == items

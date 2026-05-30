import pytest
from unittest.mock import AsyncMock, MagicMock

pytestmark = pytest.mark.unit


@pytest.fixture
def connector():
    from infrastructure.secondary.connectors.planning.plane_connector import (
        PlaneConnector,
    )
    return PlaneConnector()


class TestPlaneConnectorMetadata:
    def test_connector_type(self, connector):
        assert connector.get_connector_type() == "HERRAMIENTA_PLANIFICACION"

    def test_connector_implementation(self, connector):
        assert connector.get_connector_implementation() == "PLANE"

    def test_get_artifact_types(self, connector):
        types = connector.get_artifact_types()
        assert "issue" in types
        assert "cycle" in types
        assert "module" in types
        assert "project" in types

    def test_get_metadata(self, connector):
        metadata = connector.get_metadata()
        assert metadata["name"] == "Plane"
        assert metadata["version"] == "1.0"


class TestPlaneConnectorHeaders:
    def test_build_headers_with_api_key(self, connector):
        headers = connector._build_headers({"api_key": "pk_test", "instance_url": "https://app.plane.so"})
        assert headers["Accept"] == "application/json"
        assert headers["x-api-key"] == "pk_test"
        assert headers["x-api-host"] == "https://app.plane.so"


class TestPlaneConnectorUrls:
    def test_get_health_url(self, connector):
        url = connector._get_health_url({"workspace": "my-workspace"})
        assert "/workspaces/my-workspace/projects" in url

    def test_get_fetch_url(self, connector):
        url = connector._get_fetch_url("ISSUE-123", {"workspace": "my-workspace"})
        assert "/workspaces/my-workspace/issues/ISSUE-123" in url

    def test_get_fetch_params_returns_none(self, connector):
        assert connector._get_fetch_params({}) is None

    def test_get_list_url_with_project(self, connector):
        url = connector._get_list_url({}, {"workspace": "ws1", "project": "proj1"})
        assert "/workspaces/ws1/projects/proj1/issues" in url

    def test_get_list_url_without_project(self, connector):
        url = connector._get_list_url({}, {"workspace": "ws1"})
        assert "/workspaces/ws1/issues" in url

    def test_get_list_params_with_project(self, connector):
        params = connector._get_list_params({"cycle": "sprint1"}, {"project": "proj1"})
        assert params is not None
        assert params["cycle"] == "sprint1"

    def test_get_list_params_without_project(self, connector):
        params = connector._get_list_params({}, {})
        assert params is None

    def test_get_list_json_returns_none(self, connector):
        assert connector._get_list_json({}, {}) is None

    def test_get_results_key(self, connector):
        assert connector._get_results_key() == "results"


class TestPlaneConnectorConnection:
    async def test_test_connection_success(self, connector):
        mock_response = MagicMock()
        mock_response.status_code = 200
        connector._get = AsyncMock(return_value=mock_response)

        result = await connector.test_connection({"workspace": "ws1", "api_key": "key"})
        assert result is True

    async def test_test_connection_failure(self, connector):
        mock_response = MagicMock()
        mock_response.status_code = 500
        connector._get = AsyncMock(return_value=mock_response)

        result = await connector.test_connection({"workspace": "ws1", "api_key": "key"})
        assert result is False


class TestPlaneConnectorFetch:
    async def test_fetch_artifact_success(self, connector):
        expected = {"id": "ISSUE-1", "name": "Test Issue"}
        mock_response = MagicMock()
        mock_response.json.return_value = expected
        mock_response.raise_for_status = MagicMock()
        connector._get = AsyncMock(return_value=mock_response)

        result = await connector.fetch_artifact("ISSUE-1", {"workspace": "ws1"})
        assert result == expected


class TestPlaneConnectorList:
    async def test_list_artifacts_success(self, connector):
        items = [{"id": "1"}, {"id": "2"}]
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": items}
        mock_response.raise_for_status = MagicMock()
        connector._get = AsyncMock(return_value=mock_response)

        result = await connector.list_artifacts({}, {"workspace": "ws1"})
        assert result == items

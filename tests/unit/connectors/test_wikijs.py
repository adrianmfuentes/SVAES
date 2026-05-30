import pytest
from unittest.mock import AsyncMock, MagicMock

pytestmark = pytest.mark.unit


@pytest.fixture
def connector():
    from infrastructure.secondary.connectors.documentation.wikijs_connector import (
        WikiJsConnector,
    )
    return WikiJsConnector()


class TestWikiJsConnectorMetadata:
    def test_connector_type(self, connector):
        assert connector.get_connector_type() == "SISTEMA_DOCUMENTAL"

    def test_connector_implementation(self, connector):
        assert connector.get_connector_implementation() == "WIKIJS"

    def test_get_artifact_types(self, connector):
        types = connector.get_artifact_types()
        assert "page" in types
        assert "asset" in types

    def test_get_metadata(self, connector):
        metadata = connector.get_metadata()
        assert metadata["name"] == "WikiJs"
        assert metadata["version"] == "1.0"


class TestWikiJsConnectorHeaders:
    def test_build_headers(self, connector):
        headers = connector._build_headers({"token": "wiki-token"})
        assert headers["Accept"] == "application/json"
        assert headers["Authorization"] == "Bearer wiki-token"


class TestWikiJsConnectorUrls:
    def test_get_base_url_custom(self, connector):
        url = connector._get_base_url({"base_url": "https://wiki.example.com"})
        assert url == "https://wiki.example.com"

    def test_get_base_url_default(self, connector):
        url = connector._get_base_url({})
        assert url == "http://localhost:3000"

    def test_get_health_url(self, connector):
        url = connector._get_health_url({})
        assert "/graphql" in url

    def test_get_fetch_url(self, connector):
        url = connector._get_fetch_url("some-page", {})
        assert "/graphql" in url

    def test_get_fetch_params_returns_none(self, connector):
        assert connector._get_fetch_params({}) is None

    def test_get_list_url(self, connector):
        url = connector._get_list_url({}, {})
        assert "/graphql" in url

    def test_get_list_params_returns_none(self, connector):
        assert connector._get_list_params({}, {}) is None

    def test_get_list_json_returns_none(self, connector):
        assert connector._get_list_json({}, {}) is None

    def test_get_results_key(self, connector):
        assert connector._get_results_key() == ""


class TestWikiJsConnectorConnection:
    async def test_test_connection_success(self, connector):
        mock_response = MagicMock()
        mock_response.status_code = 200
        connector._post = AsyncMock(return_value=mock_response)

        result = await connector.test_connection({"token": "token"})
        assert result is True

    async def test_test_connection_failure(self, connector):
        mock_response = MagicMock()
        mock_response.status_code = 500
        connector._post = AsyncMock(return_value=mock_response)

        result = await connector.test_connection({"token": "bad"})
        assert result is False


class TestWikiJsConnectorFetch:
    async def test_fetch_artifact_success(self, connector):
        expected = {"data": {"page": {"id": 1, "title": "Home"}}}
        mock_response = MagicMock()
        mock_response.json.return_value = expected
        mock_response.raise_for_status = MagicMock()
        connector._post = AsyncMock(return_value=mock_response)

        result = await connector.fetch_artifact("home-page", {})
        assert result == expected


class TestWikiJsConnectorList:
    async def test_list_artifacts_success(self, connector):
        items = [{"id": 1, "title": "Page 1"}, {"id": 2, "title": "Page 2"}]
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"pages": {"results": items}}}
        mock_response.raise_for_status = MagicMock()
        connector._post = AsyncMock(return_value=mock_response)

        result = await connector.list_artifacts({}, {})
        assert result == items

    async def test_list_artifacts_empty(self, connector):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"pages": {"results": []}}}
        mock_response.raise_for_status = MagicMock()
        connector._post = AsyncMock(return_value=mock_response)

        result = await connector.list_artifacts({}, {})
        assert result == []

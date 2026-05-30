import pytest
from unittest.mock import AsyncMock, MagicMock

pytestmark = pytest.mark.unit


@pytest.fixture
def connector():
    from infrastructure.secondary.connectors.source_control.gitea_connector import (
        GiteaConnector,
    )
    return GiteaConnector()


class TestGiteaConnectorMetadata:
    def test_connector_type(self, connector):
        assert connector.get_connector_type() == "REPO_CODIGO"

    def test_connector_implementation(self, connector):
        assert connector.get_connector_implementation() == "GITEA"

    def test_get_artifact_types(self, connector):
        types = connector.get_artifact_types()
        assert "pull_request" in types
        assert "release" in types
        assert "commit" in types

    def test_get_metadata(self, connector):
        metadata = connector.get_metadata()
        assert metadata["name"] == "Gitea"
        assert metadata["version"] == "1.0"


class TestGiteaConnectorHeaders:
    def test_build_headers_with_token(self, connector):
        headers = connector._build_headers({"token": "gitea-token"})
        assert headers["Authorization"] == "token gitea-token"
        assert headers["Accept"] == "application/json"


class TestGiteaConnectorUrls:
    def test_get_base_url_custom(self, connector):
        url = connector._get_base_url({"base_url": "https://git.example.com/api/v1"})
        assert url == "https://git.example.com/api/v1"

    def test_get_base_url_default(self, connector):
        url = connector._get_base_url({})
        assert url == "https://gitea.com/api/v1"

    def test_get_health_url(self, connector):
        url = connector._get_health_url({})
        assert "/user" in url

    def test_get_fetch_url(self, connector):
        url = connector._get_fetch_url("owner/repo/42", {})
        assert "/repos/owner/repo/pulls/42" in url

    def test_get_fetch_params_returns_none(self, connector):
        assert connector._get_fetch_params({}) is None

    def test_get_list_url_with_owner_repo(self, connector):
        url = connector._get_list_url({}, {"owner": "org", "repo": "test"})
        assert "/repos/org/test/pulls" in url

    def test_get_list_url_without_owner_repo(self, connector):
        url = connector._get_list_url({}, {})
        assert "/user/repos" in url

    def test_get_list_params_with_owner_repo(self, connector):
        params = connector._get_list_params({"state": "closed"}, {"owner": "org", "repo": "test"})
        assert params == {"state": "closed", "limit": 50}

    def test_get_list_params_without_owner_repo(self, connector):
        params = connector._get_list_params({}, {})
        assert params == {"limit": 50}

    def test_get_list_json_returns_none(self, connector):
        assert connector._get_list_json({}, {}) is None

    def test_get_results_key(self, connector):
        assert connector._get_results_key() == ""


class TestGiteaConnectorConnection:
    async def test_test_connection_success(self, connector):
        mock_response = MagicMock()
        mock_response.status_code = 200
        connector._get = AsyncMock(return_value=mock_response)

        result = await connector.test_connection({"token": "token"})
        assert result is True

    async def test_test_connection_failure(self, connector):
        mock_response = MagicMock()
        mock_response.status_code = 403
        connector._get = AsyncMock(return_value=mock_response)

        result = await connector.test_connection({"token": "bad-token"})
        assert result is False


class TestGiteaConnectorFetch:
    async def test_fetch_artifact_success(self, connector):
        expected = {"id": 42, "title": "PR Title"}
        mock_response = MagicMock()
        mock_response.json.return_value = expected
        mock_response.raise_for_status = MagicMock()
        connector._get = AsyncMock(return_value=mock_response)

        result = await connector.fetch_artifact("owner/repo/42", {})
        assert result == expected


class TestGiteaConnectorList:
    async def test_list_artifacts_success(self, connector):
        items = [{"id": 1}, {"id": 2}]
        mock_response = MagicMock()
        mock_response.json.return_value = {"": items}
        mock_response.raise_for_status = MagicMock()
        connector._get = AsyncMock(return_value=mock_response)

        result = await connector.list_artifacts({}, {"owner": "org", "repo": "test"})
        assert result == items

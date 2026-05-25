import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock

pytestmark = pytest.mark.unit


class TestJiraConnectorMetadata:
    def test_get_connector_type(self, jira_connector):
        """Verifica que el tipo de conector sea GESTOR_TAREAS."""
        assert jira_connector.get_connector_type() == "GESTOR_TAREAS"

    def test_get_connector_implementation(self, jira_connector):
        """Verifica que la implementación sea JIRA."""
        assert jira_connector.get_connector_implementation() == "JIRA"

    def test_get_artifact_types(self, jira_connector):
        """Verifica que los tipos de artifact incluyan issue, project y board."""
        assert jira_connector.get_artifact_types() == ["issue", "project", "board"]

    def test_get_metadata(self, jira_connector):
        """Verifica que los metadatos incluyan nombre, versión y tipos de artifact."""
        metadata = jira_connector.get_metadata()
        assert metadata["name"] == "Jira"
        assert metadata["version"] == "1.0"
        assert metadata["artifact_types"] == ["issue", "project", "board"]


class TestJiraConnectorHeaders:
    def test_build_headers_atlassian_auth(self, jira_connector):
        """Verifica que los headers usen email y api_token para autenticación Atlassian."""
        headers = jira_connector._build_headers(
            {"email": "user@example.com", "api_token": "atlassian-token-123"}
        )
        assert headers == {
            "Accept": "application/json",
            "email": "user@example.com",
            "api_token": "atlassian-token-123",
        }

    def test_build_headers_empty_config(self, jira_connector):
        """Verifica que los headers se construyan con valores vacíos cuando no hay configuración."""
        headers = jira_connector._build_headers({})
        assert headers == {
            "Accept": "application/json",
            "email": "",
            "api_token": "",
        }


class TestJiraConnectorUrls:
    def test_get_base_url_default(self, jira_connector):
        """Verifica que la URL base por defecto sea api.atlassian.com."""
        url = jira_connector._get_base_url({})
        assert url == "https://api.atlassian.com"

    def test_get_base_url_custom(self, jira_connector):
        """Verifica que la URL base respete la configuración personalizada."""
        url = jira_connector._get_base_url(
            {"base_url": "https://mycompany.atlassian.net"}
        )
        assert url == "https://mycompany.atlassian.net"

    def test_get_health_url_default(self, jira_connector):
        """Verifica que la URL de health por defecto apunte a /rest/api/3/myself."""
        url = jira_connector._get_health_url({})
        assert url == "https://api.atlassian.com/rest/api/3/myself"

    def test_get_health_url_with_cloud_id(self, jira_connector):
        """Verifica que la URL de health incluya cloudId cuando se provee en la configuración."""
        url = jira_connector._get_health_url({"cloud_id": "abc-123"})
        assert url == "https://api.atlassian.com/rest/api/3/myself?cloudId=abc-123"

    def test_get_health_url_with_custom_base_and_cloud_id(self, jira_connector):
        """Verifica que la URL de health combine base_url personalizada y cloudId."""
        url = jira_connector._get_health_url({
            "base_url": "https://custom.atlassian.net",
            "cloud_id": "xyz-789",
        })
        assert url == "https://custom.atlassian.net/rest/api/3/myself?cloudId=xyz-789"

    def test_get_fetch_url(self, jira_connector):
        """Verifica que la URL de fetch construya correctamente el endpoint de issue."""
        url = jira_connector._get_fetch_url("PROJ-123", {})
        assert url == "https://api.atlassian.com/rest/api/3/issue/PROJ-123"

    def test_get_fetch_url_with_custom_base(self, jira_connector):
        """Verifica que fetch use la base_url personalizada."""
        url = jira_connector._get_fetch_url(
            "PROJ-123", {"base_url": "https://custom.atlassian.net"}
        )
        assert url == "https://custom.atlassian.net/rest/api/3/issue/PROJ-123"

    def test_get_fetch_params_returns_none(self, jira_connector):
        """Verifica que _get_fetch_params retorne None."""
        assert jira_connector._get_fetch_params({}) is None

    def test_get_list_url(self, jira_connector):
        """Verifica que la URL de listado use el endpoint JQL search."""
        url = jira_connector._get_list_url({}, {})
        assert url == "https://api.atlassian.com/rest/api/3/search"

    def test_get_list_url_with_custom_base(self, jira_connector):
        """Verifica que list use la base_url personalizada."""
        url = jira_connector._get_list_url(
            {}, {"base_url": "https://custom.atlassian.net"}
        )
        assert url == "https://custom.atlassian.net/rest/api/3/search"

    def test_get_list_params_default(self, jira_connector):
        """Verifica los parámetros JQL por defecto (último día, 50 resultados)."""
        params = jira_connector._get_list_params({}, {})
        assert params == {"jql": "updated >= -1d", "maxResults": 50}

    def test_get_list_params_with_custom_jql(self, jira_connector):
        """Verifica que se respete la JQL y max_results personalizadas."""
        params = jira_connector._get_list_params(
            {"jql": "project = PROJ", "max_results": 10}, {}
        )
        assert params == {"jql": "project = PROJ", "maxResults": 10}

    def test_get_list_json_returns_none(self, jira_connector):
        """Verifica que _get_list_json retorne None (Jira usa GET con query params)."""
        assert jira_connector._get_list_json({}, {}) is None

    def test_get_results_key(self, jira_connector):
        """Verifica que la clave de resultados sea 'issues'."""
        assert jira_connector._get_results_key() == "issues"


class TestJiraConnectorTestConnection:
    async def test_connection_success(self, jira_connector):
        """Verifica que test_connection retorne True cuando el endpoint responde 200."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        jira_connector._get = AsyncMock(return_value=mock_response)

        result = await jira_connector.test_connection({})

        assert result is True
        jira_connector._get.assert_called_once_with(
            "https://api.atlassian.com/rest/api/3/myself", {}
        )

    async def test_connection_failure_401(self, jira_connector):
        """Verifica que test_connection retorne False con credenciales inválidas (401)."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        jira_connector._get = AsyncMock(return_value=mock_response)

        result = await jira_connector.test_connection({})

        assert result is False

    async def test_connection_with_cloud_id(self, jira_connector):
        """Verifica que test_connection incluya cloudId en la URL cuando se configura."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        jira_connector._get = AsyncMock(return_value=mock_response)

        config = {"cloud_id": "cloud-abc"}
        result = await jira_connector.test_connection(config)

        assert result is True
        jira_connector._get.assert_called_once_with(
            "https://api.atlassian.com/rest/api/3/myself?cloudId=cloud-abc", config
        )

    async def test_connection_with_custom_base_url(self, jira_connector):
        """Verifica que test_connection use la base_url personalizada."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        jira_connector._get = AsyncMock(return_value=mock_response)

        config = {"base_url": "https://mycompany.atlassian.net"}
        result = await jira_connector.test_connection(config)

        assert result is True
        jira_connector._get.assert_called_once_with(
            "https://mycompany.atlassian.net/rest/api/3/myself", config
        )


class TestJiraConnectorFetchArtifact:
    async def test_fetch_artifact_success(self, jira_connector):
        """Verifica la obtención exitosa de un issue de Jira por clave."""
        expected_data = {
            "id": "10000",
            "key": "PROJ-123",
            "fields": {"summary": "Fix login bug"},
        }
        mock_response = MagicMock()
        mock_response.json.return_value = expected_data
        mock_response.raise_for_status = MagicMock()
        jira_connector._get = AsyncMock(return_value=mock_response)

        result = await jira_connector.fetch_artifact("PROJ-123", {})

        assert result == expected_data
        mock_response.raise_for_status.assert_called_once()
        jira_connector._get.assert_called_once_with(
            "https://api.atlassian.com/rest/api/3/issue/PROJ-123", {}, None
        )

    async def test_fetch_artifact_with_custom_base(self, jira_connector):
        """Verifica que fetch use la base_url personalizada."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"key": "PROJ-123"}
        mock_response.raise_for_status = MagicMock()
        jira_connector._get = AsyncMock(return_value=mock_response)

        config = {"base_url": "https://custom.atlassian.net"}
        await jira_connector.fetch_artifact("PROJ-123", config)

        jira_connector._get.assert_called_once_with(
            "https://custom.atlassian.net/rest/api/3/issue/PROJ-123", config, None
        )

    async def test_fetch_artifact_http_error(self, jira_connector):
        """Verifica que se propague HTTPStatusError cuando el issue no se encuentra."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )
        jira_connector._get = AsyncMock(return_value=mock_response)

        with pytest.raises(httpx.HTTPStatusError):
            await jira_connector.fetch_artifact("NONEXIST-1", {})


class TestJiraConnectorListArtifacts:
    async def test_list_artifacts_success(self, jira_connector):
        """Verifica el listado exitoso de issues desde Jira usando JQL."""
        issues = [
            {"id": "10001", "key": "PROJ-1", "fields": {"summary": "Task one"}},
            {"id": "10002", "key": "PROJ-2", "fields": {"summary": "Task two"}},
        ]
        api_response = {"issues": issues, "total": 2}
        mock_response = MagicMock()
        mock_response.json.return_value = api_response
        mock_response.raise_for_status = MagicMock()
        jira_connector._get = AsyncMock(return_value=mock_response)

        result = await jira_connector.list_artifacts({}, {})

        assert result == issues
        mock_response.raise_for_status.assert_called_once()

    async def test_list_artifacts_empty(self, jira_connector):
        """Verifica que se retorne lista vacía cuando no hay issues."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"issues": [], "total": 0}
        mock_response.raise_for_status = MagicMock()
        jira_connector._get = AsyncMock(return_value=mock_response)

        result = await jira_connector.list_artifacts({}, {})

        assert result == []

    async def test_list_artifacts_with_custom_jql(self, jira_connector):
        """Verifica que se pase la JQL personalizada en los parámetros de búsqueda."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"issues": []}
        mock_response.raise_for_status = MagicMock()
        jira_connector._get = AsyncMock(return_value=mock_response)

        await jira_connector.list_artifacts(
            {"jql": "project = DEMO AND status = Done", "max_results": 10}, {}
        )

        jira_connector._get.assert_called_once_with(
            "https://api.atlassian.com/rest/api/3/search",
            {},
            {"jql": "project = DEMO AND status = Done", "maxResults": 10},
        )

    async def test_list_artifacts_with_custom_base_url(self, jira_connector):
        """Verifica que list use la base_url personalizada desde la configuración."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"issues": []}
        mock_response.raise_for_status = MagicMock()
        jira_connector._get = AsyncMock(return_value=mock_response)

        config = {"base_url": "https://custom.atlassian.net"}
        await jira_connector.list_artifacts({}, config)

        jira_connector._get.assert_called_once_with(
            "https://custom.atlassian.net/rest/api/3/search",
            config,
            {"jql": "updated >= -1d", "maxResults": 50},
        )

    async def test_list_artifacts_results_key_missing(self, jira_connector):
        """Verifica que se retorne lista vacía cuando la respuesta no contiene la clave issues."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"other_data": "no issues here"}
        mock_response.raise_for_status = MagicMock()
        jira_connector._get = AsyncMock(return_value=mock_response)

        result = await jira_connector.list_artifacts({}, {})

        assert result == []

    async def test_list_artifacts_http_error(self, jira_connector):
        """Verifica que se propague HTTPStatusError cuando la búsqueda JQL falla."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Request", request=MagicMock(), response=mock_response
        )
        jira_connector._get = AsyncMock(return_value=mock_response)

        with pytest.raises(httpx.HTTPStatusError):
            await jira_connector.list_artifacts(
                {"jql": "INVALID JQL!!!"}, {}
            )


class TestJiraConnectorHttpGetPost:
    async def test_get_success(self, jira_connector, mock_httpx_client):
        """Verifica que _get realice una petición GET con headers Atlassian y retorne la respuesta."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_httpx_client.get = AsyncMock(return_value=mock_response)

        config = {"email": "user@example.com", "api_token": "token"}
        response = await jira_connector._get(
            "https://api.atlassian.com/rest/api/3/myself", config
        )

        assert response.status_code == 200
        mock_httpx_client.get.assert_called_once()

    async def test_get_connect_error(self, jira_connector, mock_httpx_client):
        """Verifica que los errores de conexión en _get se propaguen como httpx.ConnectError."""
        mock_httpx_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        with pytest.raises(httpx.ConnectError, match="Connection refused"):
            await jira_connector._get(
                "https://api.atlassian.com/rest/api/3/myself", {}
            )

    async def test_post_success(self, jira_connector, mock_httpx_client):
        """Verifica que _post realice una petición POST con headers Atlassian y body JSON."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_httpx_client.post = AsyncMock(return_value=mock_response)

        response = await jira_connector._post(
            "https://api.atlassian.com/rest/api/3/issue",
            {"email": "user@example.com", "api_token": "token"},
            {"fields": {"summary": "New issue"}},
        )

        assert response.status_code == 201
        mock_httpx_client.post.assert_called_once()

    async def test_post_connect_error(self, jira_connector, mock_httpx_client):
        """Verifica que los errores de conexión en _post se propaguen como httpx.ConnectError."""
        mock_httpx_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        with pytest.raises(httpx.ConnectError, match="Connection refused"):
            await jira_connector._post(
                "https://api.atlassian.com/rest/api/3/issue", {}, {}
            )

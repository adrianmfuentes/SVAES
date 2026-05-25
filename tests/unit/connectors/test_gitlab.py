import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock

pytestmark = pytest.mark.unit

class TestGitLabConnectorMetadata:
    def test_get_connector_type(self, gitlab_connector):
        """Verifica que el tipo de conector sea REPO_CODIGO."""
        assert gitlab_connector.get_connector_type() == "REPO_CODIGO"

    def test_get_connector_implementation(self, gitlab_connector):
        """Verifica que la implementación sea GITLAB."""
        assert gitlab_connector.get_connector_implementation() == "GITLAB"

    def test_get_artifact_types(self, gitlab_connector):
        """Verifica que los tipos de artifact incluyan merge_request, commit, pipeline y release."""
        assert gitlab_connector.get_artifact_types() == [
            "merge_request",
            "commit",
            "pipeline",
            "release",
        ]

    def test_get_metadata(self, gitlab_connector):
        """Verifica que los metadatos incluyan nombre, versión y tipos de artifact."""
        metadata = gitlab_connector.get_metadata()
        assert metadata["name"] == "GitLab"
        assert metadata["version"] == "1.0"
        assert metadata["artifact_types"] == [
            "merge_request",
            "commit",
            "pipeline",
            "release",
        ]


class TestGitLabConnectorHeaders:
    def test_build_headers_with_token(self, gitlab_connector):
        """Verifica que se construyan los headers con el token Bearer."""
        # Use a non-sensitive placeholder token for tests
        headers = gitlab_connector._build_headers({"token": "token-placeholder"})
        assert headers == {"Authorization": "Bearer token-placeholder"}

    def test_build_headers_without_token(self, gitlab_connector):
        """Verifica que los headers se construyan con token None cuando no se provee."""
        headers = gitlab_connector._build_headers({})
        assert headers == {"Authorization": "Bearer None"}


class TestGitLabConnectorUrls:
    def test_get_health_url(self, gitlab_connector):
        """Verifica que la URL de health apunte al endpoint /user de GitLab."""
        url = gitlab_connector._get_health_url({})
        assert url == "https://gitlab.com/api/v4/user"

    def test_get_health_url_with_custom_base(self, gitlab_connector):
        """Verifica que la URL de health se construya con BASE_URL por defecto."""
        url = gitlab_connector._get_health_url({"base_url": "https://gitlab.custom.com/api/v4"})
        assert url == "https://gitlab.com/api/v4/user"

    def test_get_fetch_url(self, gitlab_connector):
        """Verifica que la URL de fetch construya project_id y mr_iid desde la referencia."""
        url = gitlab_connector._get_fetch_url("12345/42", {})
        assert url == "https://gitlab.com/api/v4/projects/12345/merge_requests/42"

    def test_get_fetch_params_returns_none(self, gitlab_connector):
        """Verifica que _get_fetch_params retorne None."""
        assert gitlab_connector._get_fetch_params({}) is None

    def test_get_list_url_with_project_id(self, gitlab_connector):
        """Verifica la URL de listado cuando se especifica project_id en la configuración."""
        url = gitlab_connector._get_list_url({}, {"project_id": "42"})
        assert url == "https://gitlab.com/api/v4/projects/42/merge_requests"

    def test_get_list_url_without_project_id(self, gitlab_connector):
        """Verifica la URL de listado por defecto cuando no hay project_id."""
        url = gitlab_connector._get_list_url({}, {})
        assert url == "https://gitlab.com/api/v4/merge_requests"

    def test_get_list_params_default(self, gitlab_connector):
        """Verifica que los parámetros de listado usen state=opened por defecto."""
        params = gitlab_connector._get_list_params({}, {})
        assert params == {"state": "opened", "per_page": 50}

    def test_get_list_params_with_custom_state(self, gitlab_connector):
        """Verifica que los parámetros de listado respeten el filtro de estado."""
        params = gitlab_connector._get_list_params({"state": "merged"}, {})
        assert params == {"state": "merged", "per_page": 50}

    def test_get_list_json_returns_none(self, gitlab_connector):
        """Verifica que _get_list_json retorne None (GitLab usa GET con query params)."""
        assert gitlab_connector._get_list_json({}, {}) is None

    def test_get_results_key_empty(self, gitlab_connector):
        """Verifica que la clave de resultados sea cadena vacía (el array es la raíz de la respuesta)."""
        assert gitlab_connector._get_results_key() == ""


class TestGitLabConnectorTestConnection:
    async def test_connection_success(self, gitlab_connector):
        """Verifica que test_connection retorne True cuando el endpoint responde 200."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        gitlab_connector._get = AsyncMock(return_value=mock_response)

        result = await gitlab_connector.test_connection({})

        assert result is True
        gitlab_connector._get.assert_called_once_with(
            "https://gitlab.com/api/v4/user", {}
        )

    async def test_connection_failure_401(self, gitlab_connector):
        """Verifica que test_connection retorne False cuando la API responde 401."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        gitlab_connector._get = AsyncMock(return_value=mock_response)

        result = await gitlab_connector.test_connection({})

        assert result is False

    async def test_connection_failure_500(self, gitlab_connector):
        """Verifica que test_connection retorne False cuando la API responde 500."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        gitlab_connector._get = AsyncMock(return_value=mock_response)

        result = await gitlab_connector.test_connection({})

        assert result is False

    async def test_connection_with_custom_config(self, gitlab_connector):
        """Verifica que test_connection use la configuración personalizada."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        gitlab_connector._get = AsyncMock(return_value=mock_response)

        config = {"token": "glpat-custom", "project_id": "99"}
        result = await gitlab_connector.test_connection(config)

        assert result is True
        gitlab_connector._get.assert_called_once_with(
            "https://gitlab.com/api/v4/user", config
        )


class TestGitLabConnectorFetchArtifact:
    async def test_fetch_artifact_success(self, gitlab_connector):
        """Verifica la obtención exitosa de un artifact por referencia project_id/mr_iid."""
        expected_data = {"id": 42, "title": "Fix bug", "state": "merged"}
        mock_response = MagicMock()
        mock_response.json.return_value = expected_data
        mock_response.raise_for_status = MagicMock()
        gitlab_connector._get = AsyncMock(return_value=mock_response)

        result = await gitlab_connector.fetch_artifact("12345/42", {})

        assert result == expected_data
        mock_response.raise_for_status.assert_called_once()
        gitlab_connector._get.assert_called_once_with(
            "https://gitlab.com/api/v4/projects/12345/merge_requests/42", {}, None
        )

    async def test_fetch_artifact_http_error(self, gitlab_connector):
        """Verifica que se propague HTTPStatusError cuando el artifact no se encuentra."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )
        gitlab_connector._get = AsyncMock(return_value=mock_response)

        with pytest.raises(httpx.HTTPStatusError):
            await gitlab_connector.fetch_artifact("12345/999", {})


class TestGitLabConnectorListArtifacts:
    async def test_list_artifacts_success(self, gitlab_connector):
        """Verifica el listado exitoso de merge requests desde GitLab."""
        items = [
            {"id": 1, "title": "MR One", "state": "opened"},
            {"id": 2, "title": "MR Two", "state": "merged"},
        ]
        mock_response = MagicMock()
        mock_response.json.return_value = {"": items}
        mock_response.raise_for_status = MagicMock()
        gitlab_connector._get = AsyncMock(return_value=mock_response)

        config = {"project_id": "12345"}
        result = await gitlab_connector.list_artifacts({}, config)

        assert result == items
        mock_response.raise_for_status.assert_called_once()

    async def test_list_artifacts_empty(self, gitlab_connector):
        """Verifica que se retorne lista vacía cuando no hay merge requests."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"": []}
        mock_response.raise_for_status = MagicMock()
        gitlab_connector._get = AsyncMock(return_value=mock_response)

        config = {"project_id": "12345"}
        result = await gitlab_connector.list_artifacts({}, config)

        assert result == []

    async def test_list_artifacts_with_state_filter(self, gitlab_connector):
        """Verifica que se aplique el filtro de estado en los parámetros de la petición."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"": []}
        mock_response.raise_for_status = MagicMock()
        gitlab_connector._get = AsyncMock(return_value=mock_response)

        config = {"project_id": "12345"}
        await gitlab_connector.list_artifacts({"state": "closed"}, config)

        gitlab_connector._get.assert_called_once_with(
            "https://gitlab.com/api/v4/projects/12345/merge_requests",
            config,
            {"state": "closed", "per_page": 50},
        )

    async def test_list_artifacts_without_project_id(self, gitlab_connector):
        """Verifica el listado sin project_id use la URL global de merge requests."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"": []}
        mock_response.raise_for_status = MagicMock()
        gitlab_connector._get = AsyncMock(return_value=mock_response)

        await gitlab_connector.list_artifacts({}, {})

        gitlab_connector._get.assert_called_once_with(
            "https://gitlab.com/api/v4/merge_requests",
            {},
            {"state": "opened", "per_page": 50},
        )

    async def test_list_artifacts_http_error(self, gitlab_connector):
        """Verifica que se propague HTTPStatusError cuando el listado falla."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Forbidden", request=MagicMock(), response=mock_response
        )
        gitlab_connector._get = AsyncMock(return_value=mock_response)

        with pytest.raises(httpx.HTTPStatusError):
            await gitlab_connector.list_artifacts({}, {"project_id": "12345"})


class TestGitLabConnectorHttpGetPost:
    async def test_get_success(self, gitlab_connector, mock_httpx_client):
        """Verifica que _get realice una petición GET y retorne la respuesta."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_httpx_client.get = AsyncMock(return_value=mock_response)

        response = await gitlab_connector._get("https://gitlab.com/api/v4/user", {})

        assert response.status_code == 200
        mock_httpx_client.get.assert_called_once()

    async def test_get_connect_error(self, gitlab_connector, mock_httpx_client):
        """Verifica que los errores de conexión en _get se propaguen como httpx.ConnectError."""
        mock_httpx_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        with pytest.raises(httpx.ConnectError, match="Connection refused"):
            await gitlab_connector._get("https://gitlab.com/api/v4/user", {})

    async def test_post_success(self, gitlab_connector, mock_httpx_client):
        """Verifica que _post realice una petición POST con body JSON y retorne la respuesta."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_httpx_client.post = AsyncMock(return_value=mock_response)

        response = await gitlab_connector._post(
            "https://gitlab.com/api/v4/issues", {}, {"title": "New issue"}
        )

        assert response.status_code == 201
        mock_httpx_client.post.assert_called_once()

    async def test_post_connect_error(self, gitlab_connector, mock_httpx_client):
        """Verifica que los errores de conexión en _post se propaguen como httpx.ConnectError."""
        mock_httpx_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        with pytest.raises(httpx.ConnectError, match="Connection refused"):
            await gitlab_connector._post("https://gitlab.com/api/v4/issues", {}, {})

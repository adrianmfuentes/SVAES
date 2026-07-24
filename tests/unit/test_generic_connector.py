"""Pruebas unitarias del conector genérico (GenericHttpConnector).

Cubre construcción de cabeceras por tipo de autenticación, construcción de
URL, extracción de claves anidadas y el ciclo test_connection/fetch_artifact/
list_artifacts, además de que sigue protegido por el guardarraíl SSRF
compartido con el resto de conectores HTTP.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

pytestmark = pytest.mark.unit

from infrastructure.secondary.connectors.generic.generic_http_connector import (
    GenericHttpConnector,
    _build_url,
    _dig,
)
from domain.exceptions import ConnectorConnectionFailedError


def _mock_response(status_code, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    if json_data is not None:
        resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


class TestBuildUrl:
    def test_joins_base_and_relative_path(self):
        assert _build_url("https://api.example.com", "issues/1") == "https://api.example.com/issues/1"

    def test_joins_base_and_absolute_path(self):
        assert _build_url("https://api.example.com/", "/issues/1") == "https://api.example.com/issues/1"

    def test_empty_path_returns_base(self):
        assert _build_url("https://api.example.com", "") == "https://api.example.com"


class TestDig:
    def test_empty_key_returns_data_unchanged(self):
        data = {"a": 1}
        assert _dig(data, "") is data
        assert _dig(data, None) is data

    def test_nested_key_extracted(self):
        data = {"data": {"items": [1, 2, 3]}}
        assert _dig(data, "data.items") == [1, 2, 3]

    def test_missing_key_returns_none(self):
        assert _dig({"a": {}}, "a.b.c") is None

    def test_non_dict_intermediate_returns_none(self):
        assert _dig({"a": [1, 2]}, "a.b") is None


class TestBuildHeaders:
    @pytest.fixture
    def connector(self):
        return GenericHttpConnector()

    def test_bearer_auth(self, connector):
        headers = connector._build_headers({"auth_type": "bearer", "token": "secret-token"})  # NOSONAR
        assert headers["Authorization"] == "Bearer secret-token"

    def test_basic_auth(self, connector):
        headers = connector._build_headers(
            {"auth_type": "basic", "username": "admin", "password": "pw"}  # NOSONAR
        )
        assert headers["Authorization"].startswith("Basic ")

    def test_header_auth(self, connector):
        headers = connector._build_headers(
            {"auth_type": "header", "auth_header_name": "X-Api-Key", "auth_header_value": "abc123"}  # NOSONAR
        )
        assert headers["X-Api-Key"] == "abc123"

    def test_none_auth_has_no_authorization_header(self, connector):
        headers = connector._build_headers({"auth_type": "none"})
        assert "Authorization" not in headers

    def test_missing_auth_type_defaults_to_none(self, connector):
        headers = connector._build_headers({})
        assert "Authorization" not in headers


class TestGenericConnectorMetadata:
    def test_implementation_name(self):
        connector = GenericHttpConnector()
        assert connector.get_connector_implementation() == "CUSTOM"

    def test_connector_type_is_a_real_category(self):
        from domain.enums import ConnectorType
        connector = GenericHttpConnector()
        assert connector.get_connector_type() in {t.value for t in ConnectorType}


class TestGenericConnectorLifecycle:
    @pytest.fixture
    def connector(self):
        return GenericHttpConnector()

    @pytest.fixture
    def config(self):
        return {
            "base_url": "https://internal.example.com",
            "auth_type": "bearer",
            "token": "tok",  # NOSONAR
            "health_path": "/health",
            "fetch_path_template": "/issues/{ref}",
            "fetch_result_key": "issue",
            "list_path": "/issues",
            "list_result_key": "issues",
        }

    async def test_test_connection_success(self, connector, config):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = _mock_response(200)
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            result = await connector.test_connection(config)
        assert result is True

    async def test_test_connection_failure(self, connector, config):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = _mock_response(401)
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            result = await connector.test_connection(config)
        assert result is False

    async def test_fetch_artifact_extracts_result_key(self, connector, config):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = _mock_response(200, {"issue": {"id": "42", "title": "Bug"}})
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            result = await connector.fetch_artifact("42", config)
        assert result == {"id": "42", "title": "Bug"}
        called_url = mock_client.get.call_args.args[0]
        assert called_url == "https://internal.example.com/issues/42"

    async def test_fetch_artifact_without_result_key_returns_raw_dict(self, connector, config):
        config = {**config, "fetch_result_key": ""}
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = _mock_response(200, {"id": "42"})
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            result = await connector.fetch_artifact("42", config)
        assert result == {"id": "42"}

    async def test_list_artifacts_extracts_result_key(self, connector, config):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = _mock_response(200, {"issues": [{"id": "1"}, {"id": "2"}]})
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            result = await connector.list_artifacts({}, config)
        assert result == [{"id": "1"}, {"id": "2"}]

    async def test_list_artifacts_bare_array_response(self, connector, config):
        config = {**config, "list_result_key": ""}
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = _mock_response(200, [{"id": "1"}])
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            result = await connector.list_artifacts({}, config)
        assert result == [{"id": "1"}]

    async def test_rejects_internal_host_ssrf(self, connector, config):
        config = {**config, "base_url": "http://169.254.169.254"}
        with pytest.raises(ConnectorConnectionFailedError):
            await connector.test_connection(config)

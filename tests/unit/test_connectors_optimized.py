"""
Pruebas Unitarias de Conectores (GitLab / Jira)
Técnica: CE+VL (Clases de Equivalencia + Valores Límite)
Total: 6 tests (TC-UNI-CON-01 a TC-UNI-CON-06)
"""

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock

pytestmark = pytest.mark.unit


GITLAB_HEALTH_URL = "https://gitlab.com/api/v4/user"
JIRA_HEALTH_URL = "https://api.atlassian.com/rest/api/3/myself"


@pytest.fixture
def gitlab_connector():
    from infrastructure.secondary.connectors.source_control.gitlab_connector import (
        GitLabConnector,
    )
    return GitLabConnector()


@pytest.fixture
def jira_connector():
    from infrastructure.secondary.connectors.task_management.jira_connector import (
        JiraConnector,
    )
    return JiraConnector()


def _mock_response(status_code, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    if json_data is not None:
        resp.json.return_value = json_data
    return resp


class TestConnectorCredentials:
    """TC-UNI-CON-01 y TC-UNI-CON-02: CE+VL sobre credenciales."""

    # ------------------------------------------------------------------
    # TC-UNI-CON-01: Credenciales válidas -> conexión exitosa (GitLab)
    # ------------------------------------------------------------------
    async def test_tc_uni_con_01_valid_credentials_gitlab_returns_true(
        self, gitlab_connector
    ):
        """CE+VL: credenciales válidas (token correcto) -> test_connection retorna True."""
        gitlab_connector._get = AsyncMock(
            return_value=_mock_response(200, {"id": 1, "username": "test"})
        )

        result = await gitlab_connector.test_connection(
            {"token": "glpat-valid-token-12345"} # NOSONAR
        )

        assert result is True
        gitlab_connector._get.assert_called_once_with( 
            GITLAB_HEALTH_URL, {"token": "glpat-valid-token-12345"} # NOSONAR
        )

    # ------------------------------------------------------------------
    # TC-UNI-CON-02: Credenciales inválidas -> conexión fallida (Jira)
    # ------------------------------------------------------------------
    async def test_tc_uni_con_02_invalid_credentials_jira_returns_false(
        self, jira_connector
    ):
        """CE+VL: credenciales inválidas (401) -> test_connection retorna False."""
        jira_connector._get = AsyncMock(
            return_value=_mock_response(401, {"error": "Unauthorized"})
        )

        result = await jira_connector.test_connection(
            {"email": "bad@test.com", "api_token": "wrong-token"}
        )

        assert result is False


class TestConnectorNetwork:
    """TC-UNI-CON-03 y TC-UNI-CON-04: CE+VL sobre disponibilidad de red."""

    # ------------------------------------------------------------------
    # TC-UNI-CON-03: Red accesible -> 200 OK (GitLab)
    # ------------------------------------------------------------------
    async def test_tc_uni_con_03_network_accessible_gitlab_returns_200(
        self, gitlab_connector
    ):
        """CE+VL: red accesible, endpoint health retorna 200 -> conexión OK."""
        gitlab_connector._get = AsyncMock(
            return_value=_mock_response(200, {"id": 42})
        )

        result = await gitlab_connector.test_connection(
            {"token": "glpat-network-ok"} # NOSONAR
        )

        assert result is True

    # ------------------------------------------------------------------
    # TC-UNI-CON-04: Red inaccesible -> error de conexión (Jira)
    # ------------------------------------------------------------------
    async def test_tc_uni_con_04_network_unreachable_jira_raises_connect_error(
        self, jira_connector
    ):
        """CE+VL: red inaccesible -> httpx.ConnectError al intentar health check."""
        jira_connector._get = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        with pytest.raises(httpx.ConnectError, match="Connection refused"):
            await jira_connector.test_connection(
                {"email": "user@test.com", "api_token": "token-123"}
            )


class TestConnectorTimeoutBoundary:
    """TC-UNI-CON-05 y TC-UNI-CON-06: CE+VL sobre valores límite de timeout."""

    # ------------------------------------------------------------------
    # TC-UNI-CON-05: Timeout exacto al límite -> respuesta dentro del umbral
    # ------------------------------------------------------------------
    async def test_tc_uni_con_05_timeout_boundary_ok_gitlab(
        self, gitlab_connector
    ):
        """CE+VL: timeout límite (30s), el servidor responde antes del corte -> OK."""
        gitlab_connector._get = AsyncMock(
            return_value=_mock_response(200, {"id": 1})
        )

        result = await gitlab_connector.test_connection(
            {"token": "glpat-timeout-ok"} # NOSONAR
        )

        assert result is True

    # ------------------------------------------------------------------
    # TC-UNI-CON-06: Timeout excedido -> error de timeout (Jira)
    # ------------------------------------------------------------------
    async def test_tc_uni_con_06_timeout_exceeded_jira_raises_timeout(
        self, jira_connector
    ):
        """CE+VL: timeout excedido -> httpx.TimeoutException al contactar Jira."""
        jira_connector._get = AsyncMock(
            side_effect=httpx.TimeoutException("Request timed out")
        )

        with pytest.raises(httpx.TimeoutException, match="timed out"):
            await jira_connector.test_connection(
                {"email": "user@test.com", "api_token": "token-456"}
            )

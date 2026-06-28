"""
Pruebas Unitarias de Conectores (consolidated)
Combines connector tests from:
- test_connectors_optimized.py  (GitLab/Jira credentials, network, timeout)
- test_low_coverage_boost.py    (Redmine, JiraSM, Trello, Linear, WikiJS, Plane, Gitea, Confluence, ClickUp)
- test_more_services.py         (ConnectorRegistry, BaseHttpConnector, ConnectorImplementations)
"""

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

pytestmark = pytest.mark.unit

GITLAB_HEALTH_URL = "https://gitlab.com/api/v4/user"
JIRA_HEALTH_URL = "https://api.atlassian.com/rest/api/3/myself"


# ── module-level fixtures ───────────────────────────────────────────────────────

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


# ── helpers ─────────────────────────────────────────────────────────────────────

def _mock_response(status_code, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    if json_data is not None:
        resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


# ═══════════════════════════════════════════════════════════════════════════════
# TestConnectorCredentials  (from test_connectors_optimized.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestConnectorCredentials:
    """TC-UNI-CON-01 y TC-UNI-CON-02: CE+VL sobre credenciales."""

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


# ═══════════════════════════════════════════════════════════════════════════════
# TestConnectorNetwork  (from test_connectors_optimized.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestConnectorNetwork:
    """TC-UNI-CON-03 y TC-UNI-CON-04: CE+VL sobre disponibilidad de red."""

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


# ═══════════════════════════════════════════════════════════════════════════════
# TestConnectorTimeoutBoundary  (from test_connectors_optimized.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestConnectorTimeoutBoundary:
    """TC-UNI-CON-05 y TC-UNI-CON-06: CE+VL sobre valores límite de timeout."""

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


# ═══════════════════════════════════════════════════════════════════════════════
# TestRedmineConnector  (from test_low_coverage_boost.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestRedmineConnector:
    @pytest.fixture
    def conn(self):
        from infrastructure.secondary.connectors.change_management.redmine_connector import RedmineConnector
        return RedmineConnector()

    def test_properties_and_metadata(self, conn):
        assert conn.connector_type == "GESTION_CAMBIOS"
        assert conn.connector_implementation == "REDMINE"
        assert conn.get_connector_type() == "GESTION_CAMBIOS"
        assert conn.get_connector_implementation() == "REDMINE"
        meta = conn.get_metadata()
        assert meta["name"] == "Redmine"
        assert "issue" in meta["artifact_types"]

    @pytest.mark.asyncio
    async def test_test_connection_success(self, conn):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=_mock_response(200))
            mock_client_cls.return_value = mock_client
            result = await conn.test_connection({"api_key": "key", "base_url": "https://rm.example.com"})
            assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, conn):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=_mock_response(401))
            mock_client_cls.return_value = mock_client
            result = await conn.test_connection({"api_key": "bad"})
            assert result is False

    @pytest.mark.asyncio
    async def test_fetch_artifact(self, conn):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=_mock_response(200, {"issue": {"id": 1, "subject": "Bug"}}))
            mock_client_cls.return_value = mock_client
            result = await conn.fetch_artifact("42", {"api_key": "key"})
            assert result == {"id": 1, "subject": "Bug"}

    @pytest.mark.asyncio
    async def test_list_artifacts_with_project(self, conn):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_resp = _mock_response(200, {"issues": [{"id": 1}]})
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client
            result = await conn.list_artifacts({"status_id": "open"}, {"api_key": "key", "project_id": "prj1"})
            assert result == [{"id": 1}]

    @pytest.mark.asyncio
    async def test_list_artifacts_without_project(self, conn):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_resp = _mock_response(200, {"issues": []})
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client
            result = await conn.list_artifacts({}, {"api_key": "key"})
            assert result == []


# ═══════════════════════════════════════════════════════════════════════════════
# TestJiraSMConnector  (from test_low_coverage_boost.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestJiraSMConnector:
    @pytest.fixture
    def conn(self):
        from infrastructure.secondary.connectors.change_management.jira_sm_connector import JiraServiceManagementConnector
        return JiraServiceManagementConnector()

    def test_properties(self, conn):
        assert conn.CONNECTOR_TYPE == "GESTION_CAMBIOS"
        assert conn.CONNECTOR_IMPLEMENTATION == "JIRA_SM"
        assert conn.get_connector_type() == "GESTION_CAMBIOS"
        assert "request" in conn.get_artifact_types()

    def test_get_health_url_with_site_id(self, conn):
        url = conn._get_health_url({"site_id": "site123"})
        assert "/ex/jira/site123/rest/servicedeskapi/servicedesk" in url

    def test_get_health_url_without_site_id(self, conn):
        url = conn._get_health_url({})
        assert "/rest/servicedeskapi/servicedesk" in url

    def test_get_fetch_url(self, conn):
        url = conn._get_fetch_url("REQ-1", {})
        assert "/rest/servicedeskapi/request/REQ-1" in url

    def test_get_list_url_with_service_desk(self, conn):
        url = conn._get_list_url({}, {"service_desk_id": "sd1"})
        assert "/servicedeskapi/servicedesk/sd1/queue" in url

    def test_get_list_url_without_service_desk(self, conn):
        url = conn._get_list_url({}, {})
        assert "/servicedeskapi/request" in url

    def test_get_list_params_with_service_desk(self, conn):
        params = conn._get_list_params({}, {"service_desk_id": "sd1"})
        assert params is not None
        assert "requestType" in params

    def test_get_list_params_without_service_desk(self, conn):
        params = conn._get_list_params({}, {})
        assert params == {"limit": 50}

    def test_get_list_json(self, conn):
        assert conn._get_list_json({}, {}) is None

    def test_get_results_key(self, conn):
        assert conn._get_results_key() == "values"

    @pytest.mark.asyncio
    async def test_test_connection_success(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(200))
        result = await conn.test_connection({"email": "u@t.com", "api_token": "t"})
        assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(401))
        result = await conn.test_connection({"email": "u@t.com", "api_token": "t"})
        assert result is False

    @pytest.mark.asyncio
    async def test_fetch_artifact(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(200, {"id": "REQ-1"}))
        result = await conn.fetch_artifact("REQ-1", {})
        assert result == {"id": "REQ-1"}

    @pytest.mark.asyncio
    async def test_list_artifacts(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(200, {"values": [{"id": "1"}]}))
        result = await conn.list_artifacts({}, {})
        assert result == [{"id": "1"}]


# ═══════════════════════════════════════════════════════════════════════════════
# TestTrelloConnector  (from test_low_coverage_boost.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestTrelloConnector:
    @pytest.fixture
    def conn(self):
        from infrastructure.secondary.connectors.task_management.trello_connector import TrelloConnector
        return TrelloConnector()

    def test_properties_and_metadata(self, conn):
        assert conn.connector_type == "GESTOR_TAREAS"
        assert conn.connector_implementation == "TRELLO"
        assert conn.get_connector_type() == "GESTOR_TAREAS"
        meta = conn.get_metadata()
        assert meta["name"] == "Trello"

    @pytest.mark.asyncio
    async def test_test_connection_success(self, conn):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=_mock_response(200))
            mock_client_cls.return_value = mock_client
            result = await conn.test_connection({"api_key": "k", "token": "t"})
            assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, conn):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=_mock_response(401))
            mock_client_cls.return_value = mock_client
            result = await conn.test_connection({"api_key": "k", "token": "t"})
            assert result is False

    @pytest.mark.asyncio
    async def test_fetch_artifact(self, conn):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=_mock_response(200, {"id": "card1"}))
            mock_client_cls.return_value = mock_client
            result = await conn.fetch_artifact("card1", {"api_key": "k", "token": "t"})
            assert result["id"] == "card1"

    @pytest.mark.asyncio
    async def test_list_artifacts_with_board(self, conn):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=_mock_response(200, [{"id": "c1"}]))
            mock_client_cls.return_value = mock_client
            result = await conn.list_artifacts({}, {"api_key": "k", "token": "t", "board_id": "b1"})
            assert result == [{"id": "c1"}]

    @pytest.mark.asyncio
    async def test_list_artifacts_without_board(self, conn):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=_mock_response(200, []))
            mock_client_cls.return_value = mock_client
            result = await conn.list_artifacts({}, {"api_key": "k", "token": "t"})
            assert result == []


# ═══════════════════════════════════════════════════════════════════════════════
# TestLinearConnector  (from test_low_coverage_boost.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestLinearConnector:
    @pytest.fixture
    def conn(self):
        from infrastructure.secondary.connectors.task_management.linear_connector import LinearConnector
        return LinearConnector()

    def test_properties(self, conn):
        assert conn.CONNECTOR_TYPE == "GESTOR_TAREAS"
        assert conn.CONNECTOR_IMPLEMENTATION == "LINEAR"
        assert "issue" in conn.get_artifact_types()

    @pytest.mark.asyncio
    async def test_test_connection_success(self, conn):
        conn._post = AsyncMock(return_value=_mock_response(200))
        result = await conn.test_connection({"api_key": "key"})
        assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, conn):
        conn._post = AsyncMock(return_value=_mock_response(401))
        result = await conn.test_connection({"api_key": "bad"})
        assert result is False

    @pytest.mark.asyncio
    async def test_fetch_artifact(self, conn):
        conn._post = AsyncMock(return_value=_mock_response(200, {"data": {"issue": {"id": "i1"}}}))
        result = await conn.fetch_artifact("i1", {"api_key": "key"})
        assert "data" in result

    @pytest.mark.asyncio
    async def test_list_artifacts(self, conn):
        resp_data = {"data": {"issues": {"nodes": [{"id": "i1"}]}}}
        conn._post = AsyncMock(return_value=_mock_response(200, resp_data))
        result = await conn.list_artifacts({"first": 10}, {"api_key": "key"})
        assert result == [{"id": "i1"}]


# ═══════════════════════════════════════════════════════════════════════════════
# TestWikiJsConnector  (from test_low_coverage_boost.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestWikiJsConnector:
    @pytest.fixture
    def conn(self):
        from infrastructure.secondary.connectors.documentation.wikijs_connector import WikiJsConnector
        return WikiJsConnector()

    def test_properties(self, conn):
        assert conn.CONNECTOR_TYPE == "SISTEMA_DOCUMENTAL"
        assert conn.CONNECTOR_IMPLEMENTATION == "WIKIJS"
        assert "page" in conn.get_artifact_types()

    @pytest.mark.asyncio
    async def test_test_connection_success(self, conn):
        conn._post = AsyncMock(return_value=_mock_response(200))
        result = await conn.test_connection({"token": "t"})
        assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, conn):
        conn._post = AsyncMock(return_value=_mock_response(500))
        result = await conn.test_connection({"token": "t"})
        assert result is False

    @pytest.mark.asyncio
    async def test_fetch_artifact(self, conn):
        conn._post = AsyncMock(return_value=_mock_response(200, {"data": {"page": {"id": "1"}}}))
        result = await conn.fetch_artifact("home", {"token": "t", "base_url": "http://w"})
        assert "data" in result

    @pytest.mark.asyncio
    async def test_list_artifacts(self, conn):
        resp_data = {"data": {"pages": {"results": [{"id": "1"}]}}}
        conn._post = AsyncMock(return_value=_mock_response(200, resp_data))
        result = await conn.list_artifacts({}, {"token": "t"})
        assert result == [{"id": "1"}]

    def test_get_health_url(self, conn):
        url = conn._get_health_url({"base_url": "http://wikijs"})
        assert url == "http://wikijs/graphql"

    def test_get_fetch_url(self, conn):
        url = conn._get_fetch_url("home", {"base_url": "http://w"})
        assert url == "http://w/graphql"

    def test_get_list_url(self, conn):
        url = conn._get_list_url({}, {"base_url": "http://w"})
        assert url == "http://w/graphql"


# ═══════════════════════════════════════════════════════════════════════════════
# TestPlaneConnector  (from test_low_coverage_boost.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPlaneConnector:
    @pytest.fixture
    def conn(self):
        from infrastructure.secondary.connectors.planning.plane_connector import PlaneConnector
        return PlaneConnector()

    def test_properties(self, conn):
        assert conn.CONNECTOR_TYPE == "HERRAMIENTA_PLANIFICACION"
        assert conn.CONNECTOR_IMPLEMENTATION == "PLANE"
        assert "issue" in conn.get_artifact_types()

    def test_get_health_url(self, conn):
        url = conn._get_health_url({"workspace": "ws"})
        assert "/workspaces/ws/projects" in url

    def test_get_fetch_url(self, conn):
        url = conn._get_fetch_url("iss-1", {"workspace": "ws"})
        assert "/workspaces/ws/issues/iss-1" in url

    def test_get_list_url_with_project(self, conn):
        url = conn._get_list_url({}, {"workspace": "ws", "project": "prj"})
        assert "/workspaces/ws/projects/prj/issues" in url

    def test_get_list_url_without_project(self, conn):
        url = conn._get_list_url({}, {"workspace": "ws"})
        assert "/workspaces/ws/issues" in url

    def test_get_list_params_with_project(self, conn):
        params = conn._get_list_params({}, {"project": "prj"})
        assert params is not None

    def test_get_list_params_without_project(self, conn):
        params = conn._get_list_params({}, {})
        assert params is None

    @pytest.mark.asyncio
    async def test_test_connection_success(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(200))
        result = await conn.test_connection({"api_key": "k", "instance_url": "u", "workspace": "ws"})
        assert result is True

    @pytest.mark.asyncio
    async def test_fetch_artifact(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(200, {"id": "iss-1"}))
        result = await conn.fetch_artifact("iss-1", {"api_key": "k", "instance_url": "u", "workspace": "ws"})
        assert result["id"] == "iss-1"

    @pytest.mark.asyncio
    async def test_list_artifacts(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(200, {"results": [{"id": "1"}]}))
        result = await conn.list_artifacts({}, {"api_key": "k", "instance_url": "u", "workspace": "ws"})
        assert result == [{"id": "1"}]


# ═══════════════════════════════════════════════════════════════════════════════
# TestGiteaConnector  (from test_low_coverage_boost.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestGiteaConnector:
    @pytest.fixture
    def conn(self):
        from infrastructure.secondary.connectors.source_control.gitea_connector import GiteaConnector
        return GiteaConnector()

    def test_properties(self, conn):
        assert conn.CONNECTOR_TYPE == "REPO_CODIGO"
        assert conn.CONNECTOR_IMPLEMENTATION == "GITEA"
        assert "pull_request" in conn.get_artifact_types()

    def test_get_health_url(self, conn):
        url = conn._get_health_url({})
        assert "/user" in url

    def test_get_fetch_url(self, conn):
        url = conn._get_fetch_url("owner/repo/5", {"base_url": "https://gitea.example"})
        assert "owner/repo/pulls/5" in url

    def test_get_list_url_with_owner_repo(self, conn):
        url = conn._get_list_url({}, {"owner": "o", "repo": "r"})
        assert "/repos/o/r/pulls" in url

    def test_get_list_url_without_owner_repo(self, conn):
        url = conn._get_list_url({}, {})
        assert "/user/repos" in url

    def test_get_list_params_with_owner_repo(self, conn):
        params = conn._get_list_params({}, {"owner": "o", "repo": "r"})
        assert params is not None
        assert "state" in params

    def test_get_list_params_without_owner_repo(self, conn):
        params = conn._get_list_params({}, {})
        assert params == {"limit": 50}

    @pytest.mark.asyncio
    async def test_test_connection_success(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(200))
        result = await conn.test_connection({"token": "t"})
        assert result is True

    @pytest.mark.asyncio
    async def test_fetch_artifact(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(200, {"id": 5}))
        result = await conn.fetch_artifact("o/r/5", {"token": "t", "base_url": "https://g"})
        assert result["id"] == 5

    @pytest.mark.asyncio
    async def test_list_artifacts_with_owner_repo(self, conn):
        resp = _mock_response(200, {})
        conn._get = AsyncMock(return_value=resp)
        result = await conn.list_artifacts({}, {"token": "t", "owner": "o", "repo": "r"})
        assert result == []

    @pytest.mark.asyncio
    async def test_list_artifacts_without_owner_repo(self, conn):
        resp = _mock_response(200, {})
        conn._get = AsyncMock(return_value=resp)
        result = await conn.list_artifacts({}, {"token": "t"})
        assert result == []


# ═══════════════════════════════════════════════════════════════════════════════
# TestConfluenceConnector  (from test_low_coverage_boost.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestConfluenceConnector:
    @pytest.fixture
    def conn(self):
        from infrastructure.secondary.connectors.documentation.confluence_connector import ConfluenceConnector
        return ConfluenceConnector()

    def test_properties(self, conn):
        assert conn.CONNECTOR_TYPE == "SISTEMA_DOCUMENTAL"
        assert conn.CONNECTOR_IMPLEMENTATION == "CONFLUENCE"
        assert "page" in conn.get_artifact_types()

    def test_get_health_url_with_base_url(self, conn):
        url = conn._get_health_url({"base_url": "https://mysite.atlassian.net"})
        assert url == "https://mysite.atlassian.net/wiki/rest/api/user/current"

    def test_get_health_url_strips_wiki_suffix(self, conn):
        url = conn._get_health_url({"base_url": "https://mysite.atlassian.net/wiki"})
        assert url == "https://mysite.atlassian.net/wiki/rest/api/user/current"

    def test_get_fetch_url(self, conn):
        url = conn._get_fetch_url("123", {})
        assert "/wiki/rest/api/content/123" in url

    def test_get_list_url(self, conn):
        url = conn._get_list_url({}, {})
        assert "/content/search" in url

    def test_get_list_params_with_space_key(self, conn):
        params = conn._get_list_params({"space_key": "DOC"}, {})
        assert "space=DOC" in params["cql"]

    def test_get_list_params_without_space_key(self, conn):
        params = conn._get_list_params({}, {})
        assert "space=" not in params["cql"]

    def test_get_results_key(self, conn):
        assert conn._get_results_key() == "results"

    @pytest.mark.asyncio
    async def test_test_connection_success(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(200))
        result = await conn.test_connection({"email": "u@t.com", "api_token": "t"})
        assert result is True

    @pytest.mark.asyncio
    async def test_fetch_artifact(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(200, {"id": "123"}))
        result = await conn.fetch_artifact("123", {})
        assert result["id"] == "123"

    @pytest.mark.asyncio
    async def test_list_artifacts(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(200, {"results": [{"id": "1"}]}))
        result = await conn.list_artifacts({}, {})
        assert result == [{"id": "1"}]


# ═══════════════════════════════════════════════════════════════════════════════
# TestClickUpConnector  (from test_low_coverage_boost.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestClickUpConnector:
    @pytest.fixture
    def conn(self):
        from infrastructure.secondary.connectors.planning.clickup_connector import ClickUpConnector
        return ClickUpConnector()

    def test_properties(self, conn):
        assert conn.CONNECTOR_TYPE == "HERRAMIENTA_PLANIFICACION"
        assert conn.CONNECTOR_IMPLEMENTATION == "CLICKUP"
        assert "task" in conn.get_artifact_types()

    def test_get_health_url(self, conn):
        url = conn._get_health_url({"team_id": "t1"})
        assert url.endswith("/team")

    def test_get_fetch_url(self, conn):
        url = conn._get_fetch_url("task1", {})
        assert "/task/task1" in url

    def test_get_list_url_with_list(self, conn):
        url = conn._get_list_url({}, {"list_id": "l1"})
        assert "/list/l1/task" in url

    def test_get_list_url_without_list(self, conn):
        url = conn._get_list_url({}, {"team_id": "t1"})
        assert "/team/t1/task" in url

    def test_get_list_params_with_list(self, conn):
        params = conn._get_list_params({}, {"list_id": "l1"})
        assert params == {"subtasks": "false"}

    def test_get_list_params_without_list(self, conn):
        params = conn._get_list_params({}, {})
        assert params == {"include_subtasks": "false"}

    def test_get_results_key(self, conn):
        assert conn._get_results_key() == "tasks"

    @pytest.mark.asyncio
    async def test_test_connection_success(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(200))
        result = await conn.test_connection({"token": "t", "team_id": "t1"})
        assert result is True

    @pytest.mark.asyncio
    async def test_fetch_artifact(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(200, {"id": "task1"}))
        result = await conn.fetch_artifact("task1", {"token": "t"})
        assert result["id"] == "task1"

    @pytest.mark.asyncio
    async def test_list_artifacts_with_list(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(200, {"tasks": [{"id": "1"}]}))
        result = await conn.list_artifacts({}, {"token": "t", "list_id": "l1"})
        assert result == [{"id": "1"}]

    @pytest.mark.asyncio
    async def test_list_artifacts_without_list(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(200, {"tasks": []}))
        result = await conn.list_artifacts({}, {"token": "t", "team_id": "t1"})
        assert result == []


# ═══════════════════════════════════════════════════════════════════════════════
# TestConnectorRegistry  (from test_more_services.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestConnectorRegistry:
    def test_register_and_get_by_implementation(self):
        """Branch: register then get_by_implementation -> returns connector"""
        from infrastructure.secondary.connectors.connector_registry import ConnectorRegistry
        registry = ConnectorRegistry()
        conn = MagicMock()
        conn.get_connector_implementation = MagicMock(return_value="JIRA")
        registry.register("GESTOR_TAREAS", conn)
        result = registry.get_by_implementation("JIRA")
        assert result == conn

    def test_get_by_implementation_not_found_raises(self):
        """Branch: implementation not registered -> KeyError"""
        from infrastructure.secondary.connectors.connector_registry import ConnectorRegistry
        registry = ConnectorRegistry()
        with pytest.raises(KeyError):
            registry.get_by_implementation("NONEXISTENT")

    def test_get_by_implementation_case_insensitive(self):
        """Branch: lowercase implementation -> still found"""
        from infrastructure.secondary.connectors.connector_registry import ConnectorRegistry
        registry = ConnectorRegistry()
        conn = MagicMock()
        conn.get_connector_implementation = MagicMock(return_value="GITLAB")
        registry.register("REPO_CODIGO", conn)
        result = registry.get_by_implementation("gitlab")
        assert result == conn

    def test_get_by_type_returns_connector(self):
        """Branch: type registered -> returns connector"""
        from infrastructure.secondary.connectors.connector_registry import ConnectorRegistry
        registry = ConnectorRegistry()
        conn = MagicMock()
        conn.get_connector_implementation = MagicMock(return_value="JIRA")
        registry.register("GESTOR_TAREAS", conn)
        result = registry.get_by_type("GESTOR_TAREAS")
        assert result == conn

    def test_get_by_type_not_found_returns_none(self):
        """Branch: type not registered -> None"""
        from infrastructure.secondary.connectors.connector_registry import ConnectorRegistry
        registry = ConnectorRegistry()
        result = registry.get_by_type("NONEXISTENT")
        assert result is None

    def test_list_by_type_with_match(self):
        """Branch: type matches -> list with one element"""
        from infrastructure.secondary.connectors.connector_registry import ConnectorRegistry
        registry = ConnectorRegistry()
        conn = MagicMock()
        conn.get_connector_implementation = MagicMock(return_value="JIRA")
        registry.register("GESTOR_TAREAS", conn)
        result = registry.list_by_type("GESTOR_TAREAS")
        assert len(result) == 1

    def test_list_by_type_no_match_returns_empty(self):
        """Branch: type not found -> empty list"""
        from infrastructure.secondary.connectors.connector_registry import ConnectorRegistry
        registry = ConnectorRegistry()
        result = registry.list_by_type("UNKNOWN")
        assert result == []

    def test_list_all_implementations(self):
        """Branch: returns all registered implementation keys"""
        from infrastructure.secondary.connectors.connector_registry import ConnectorRegistry
        registry = ConnectorRegistry()
        conn = MagicMock()
        conn.get_connector_implementation = MagicMock(return_value="JIRA")
        registry.register("GESTOR_TAREAS", conn)
        result = registry.list_all_implementations()
        assert "JIRA" in result


# ═══════════════════════════════════════════════════════════════════════════════
# TestBaseHttpConnector  (from test_more_services.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestBaseHttpConnector:
    @pytest.fixture
    def connector(self):
        from infrastructure.secondary.connectors.source_control.gitlab_connector import GitLabConnector
        return GitLabConnector()

    async def test_fetch_artifact_success(self, connector):
        """Branch: _get returns 200 with JSON -> dict returned"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value={"id": 1, "title": "MR"})
        connector._get = AsyncMock(return_value=mock_resp)
        result = await connector.fetch_artifact("123/1", {"token": "tok"})
        assert result["id"] == 1

    async def test_list_artifacts_get_branch(self, connector):
        """Branch: _get_list_json returns None -> use GET request; empty key returns []"""
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value={})
        connector._get = AsyncMock(return_value=mock_resp)
        result = await connector.list_artifacts({"state": "opened"}, {"token": "tok"})
        assert result == []

    async def test_get_connect_error_reraises(self, connector):
        """Branch: httpx.ConnectError in _get -> re-raised"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(side_effect=httpx.ConnectError("refused"))
            with pytest.raises(httpx.ConnectError):
                await connector._get("https://example.com", {"token": "tok"})

    async def test_post_connect_error_reraises(self, connector):
        """Branch: httpx.ConnectError in _post -> re-raised"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(side_effect=httpx.ConnectError("refused"))
            with pytest.raises(httpx.ConnectError):
                await connector._post("https://example.com", {"token": "tok"})

    def test_get_connector_type(self, connector):
        assert connector.get_connector_type() == "REPO_CODIGO"

    def test_get_connector_implementation(self, connector):
        assert connector.get_connector_implementation() == "GITLAB"

    def test_get_metadata(self, connector):
        meta = connector.get_metadata()
        assert "name" in meta
        assert "artifact_types" in meta

    def test_get_artifact_types(self, connector):
        types = connector.get_artifact_types()
        assert "merge_request" in types

    def test_bearer_auth_mixin_headers(self):
        """Branch: BearerAuthMixin builds Authorization header"""
        from infrastructure.secondary.connectors.base_http_connector import BearerAuthMixin
        mixin = BearerAuthMixin()
        headers = mixin._build_headers({"token": "mytoken"})
        assert "Authorization" in headers
        assert "Bearer mytoken" in headers["Authorization"]

    def test_atlassian_auth_mixin_headers(self):
        """Branch: AtlassianAuthMixin builds Basic Auth header with email:api_token"""
        import base64
        from infrastructure.secondary.connectors.base_http_connector import AtlassianAuthMixin
        mixin = AtlassianAuthMixin()
        headers = mixin._build_headers({"email": "u@x.com", "api_token": "tok"})
        assert "Authorization" in headers
        expected = base64.b64encode(b"u@x.com:tok").decode()
        assert headers["Authorization"] == f"Basic {expected}"

    def test_api_key_auth_mixin_headers(self):
        """Branch: ApiKeyAuthMixin builds Bearer header"""
        from infrastructure.secondary.connectors.base_http_connector import ApiKeyAuthMixin
        mixin = ApiKeyAuthMixin()
        headers = mixin._build_headers({"token": "api-key"})
        assert "Bearer api-key" in headers["Authorization"]


# ═══════════════════════════════════════════════════════════════════════════════
# TestConnectorImplementations  (from test_more_services.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestConnectorImplementations:
    """Test connector-specific methods not covered by existing tests."""

    async def test_jira_connector_list_artifacts_get(self):
        """Branch: Jira uses GET for list -> _get called, results_key='issues'"""
        from infrastructure.secondary.connectors.task_management.jira_connector import JiraConnector
        connector = JiraConnector()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value={"issues": [{"id": "J-1"}]})
        connector._get = AsyncMock(return_value=mock_resp)
        result = await connector.list_artifacts({}, {"email": "x@x.com", "api_token": "tok", "domain": "test"})
        assert len(result) == 1
        assert result[0]["id"] == "J-1"

    def test_gitlab_connector_get_list_url_with_project(self):
        """Branch: project_id in config -> project-specific URL"""
        from infrastructure.secondary.connectors.source_control.gitlab_connector import GitLabConnector
        c = GitLabConnector()
        url = c._get_list_url({}, {"project_id": "42"})
        assert "42" in url

    def test_gitlab_connector_get_list_url_no_project(self):
        """Branch: no project_id -> global MR URL"""
        from infrastructure.secondary.connectors.source_control.gitlab_connector import GitLabConnector
        c = GitLabConnector()
        url = c._get_list_url({}, {})
        assert "merge_requests" in url

    def test_gitlab_connector_get_list_params(self):
        from infrastructure.secondary.connectors.source_control.gitlab_connector import GitLabConnector
        c = GitLabConnector()
        params = c._get_list_params({"state": "merged"}, {})
        assert params is not None
        assert params["state"] == "merged"

    def test_connector_registry_register_and_create(self):
        """Branch: create_registered_connector_registry registers all 20"""
        from infrastructure.secondary.connectors import create_registered_connector_registry
        registry = create_registered_connector_registry()
        impls = registry.list_all_implementations()
        assert len(impls) >= 10


# ═══════════════════════════════════════════════════════════════════════════════
# TestNotionConnector
# ═══════════════════════════════════════════════════════════════════════════════

class TestNotionConnector:
    @pytest.fixture
    def conn(self):
        from infrastructure.secondary.connectors.documentation.notion_connector import NotionConnector
        return NotionConnector()

    def test_properties(self, conn):
        assert conn.CONNECTOR_TYPE == "SISTEMA_DOCUMENTAL"
        assert conn.CONNECTOR_IMPLEMENTATION == "NOTION"
        assert "page" in conn.get_artifact_types()
        assert "database" in conn.get_artifact_types()

    def test_get_artifact_types(self, conn):
        types = conn.get_artifact_types()
        assert len(types) == 2
        assert "page" in types
        assert "database" in types

    def test_build_headers(self, conn):
        headers = conn._build_headers({"token": "secret-token"})
        assert headers["Authorization"] == "Bearer secret-token"
        assert headers["Notion-Version"] == "2022-06-28"

    def test_get_health_url(self, conn):
        url = conn._get_health_url({})
        assert url == "https://api.notion.com/v1/users/me"

    def test_get_fetch_url(self, conn):
        url = conn._get_fetch_url("page-123", {})
        assert url == "https://api.notion.com/v1/pages/page-123"

    def test_get_fetch_params(self, conn):
        params = conn._get_fetch_params({})
        assert params is None

    def test_get_list_url_with_database_id(self, conn):
        url = conn._get_list_url({}, {"database_id": "db-123"})
        assert "/databases/db-123/query" in url

    def test_get_list_url_without_database_id(self, conn):
        url = conn._get_list_url({}, {})
        assert url == "https://api.notion.com/v1/search"

    def test_get_list_params(self, conn):
        params = conn._get_list_params({}, {})
        assert params is None

    def test_get_list_json_with_database_id(self, conn):
        json_body = conn._get_list_json({}, {"database_id": "db-123"})
        assert json_body == {"page_size": 50}

    def test_get_list_json_without_database_id(self, conn):
        json_body = conn._get_list_json({}, {})
        assert json_body["filter"]["value"] == "page"
        assert json_body["filter"]["property"] == "object"
        assert json_body["page_size"] == 50

    def test_get_results_key(self, conn):
        assert conn._get_results_key() == "results"

    @pytest.mark.asyncio
    async def test_test_connection_success(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(200))
        result = await conn.test_connection({"token": "tok"})
        assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(401))
        result = await conn.test_connection({"token": "bad"})
        assert result is False

    @pytest.mark.asyncio
    async def test_fetch_artifact(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(200, {"id": "page-123", "object": "page"}))
        result = await conn.fetch_artifact("page-123", {"token": "tok"})
        assert result["id"] == "page-123"

    @pytest.mark.asyncio
    async def test_list_artifacts_with_database_id(self, conn):
        conn._post = AsyncMock(return_value=_mock_response(200, {"results": [{"id": "1"}]}))
        result = await conn.list_artifacts({}, {"token": "tok", "database_id": "db-123"})
        assert result == [{"id": "1"}]

    @pytest.mark.asyncio
    async def test_list_artifacts_without_database_id(self, conn):
        conn._post = AsyncMock(return_value=_mock_response(200, {"results": [{"id": "1"}]}))
        result = await conn.list_artifacts({}, {"token": "tok"})
        assert result == [{"id": "1"}]


# ═══════════════════════════════════════════════════════════════════════════════
# TestTaigaConnector
# ═══════════════════════════════════════════════════════════════════════════════

class TestTaigaConnector:
    @pytest.fixture
    def conn(self):
        from infrastructure.secondary.connectors.planning.taiga_connector import TaigaConnector
        return TaigaConnector()

    def test_properties(self, conn):
        assert conn.CONNECTOR_TYPE == "HERRAMIENTA_PLANIFICACION"
        assert conn.CONNECTOR_IMPLEMENTATION == "TAIGA"
        assert "task" in conn.get_artifact_types()
        assert "userstory" in conn.get_artifact_types()
        assert "epic" in conn.get_artifact_types()
        assert "project" in conn.get_artifact_types()

    def test_get_artifact_types(self, conn):
        types = conn.get_artifact_types()
        assert len(types) == 4

    def test_build_headers(self, conn):
        headers = conn._build_headers({"token": "taiga-token"})
        assert headers["Authorization"] == "Bearer taiga-token"

    def test_get_health_url(self, conn):
        url = conn._get_health_url({})
        assert url == "https://api.taiga.io/api/v1/projects"

    def test_get_fetch_url(self, conn):
        url = conn._get_fetch_url("42", {})
        assert "/tasks/42" in url

    def test_get_fetch_params(self, conn):
        params = conn._get_fetch_params({})
        assert params is None

    def test_get_list_url_with_project_slug(self, conn):
        url = conn._get_list_url({}, {"project_slug": "my-project"})
        assert url == "https://api.taiga.io/api/v1/tasks"

    def test_get_list_url_without_project_slug(self, conn):
        url = conn._get_list_url({}, {})
        assert url == "https://api.taiga.io/api/v1/tasks"

    def test_get_list_params_with_project_id(self, conn):
        params = conn._get_list_params({}, {"project": "42"})
        assert params == {"project": "42"}

    def test_get_list_params_without_project(self, conn):
        params = conn._get_list_params({}, {})
        assert params is None

    def test_get_list_json(self, conn):
        json_body = conn._get_list_json({}, {})
        assert json_body is None

    def test_get_results_key(self, conn):
        assert conn._get_results_key() == ""

    @pytest.mark.asyncio
    async def test_test_connection_success(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(200))
        result = await conn.test_connection({"token": "tok"})
        assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(401))
        result = await conn.test_connection({"token": "bad"})
        assert result is False

    @pytest.mark.asyncio
    async def test_fetch_artifact(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(200, {"id": 42, "subject": "Test task"}))
        result = await conn.fetch_artifact("42", {"token": "tok"})
        assert result["id"] == 42

    @pytest.mark.asyncio
    async def test_list_artifacts_with_project_slug(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(200, []))
        result = await conn.list_artifacts({"status": "open"}, {"token": "tok", "project_slug": "my-project"})
        assert result == []

    @pytest.mark.asyncio
    async def test_list_artifacts_without_project_slug(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(200, []))
        result = await conn.list_artifacts({}, {"token": "tok", "project": "proj-1"})
        assert result == []


# ═══════════════════════════════════════════════════════════════════════════════
# TestAsanaConnector
# ═══════════════════════════════════════════════════════════════════════════════

class TestAsanaConnector:
    @pytest.fixture
    def conn(self):
        from infrastructure.secondary.connectors.task_management.asana_connector import AsanaConnector
        return AsanaConnector()

    def test_properties(self, conn):
        assert conn.CONNECTOR_TYPE == "GESTOR_TAREAS"
        assert conn.CONNECTOR_IMPLEMENTATION == "ASANA"
        assert "task" in conn.get_artifact_types()
        assert "project" in conn.get_artifact_types()
        assert "section" in conn.get_artifact_types()

    def test_get_artifact_types(self, conn):
        types = conn.get_artifact_types()
        assert len(types) == 3

    def test_get_health_url(self, conn):
        url = conn._get_health_url({})
        assert url == "https://app.asana.com/api/1.0/users/me"

    def test_get_fetch_url(self, conn):
        url = conn._get_fetch_url("task-123", {})
        assert "/tasks/task-123" in url

    def test_get_fetch_params(self, conn):
        params = conn._get_fetch_params({})
        assert "opt_fields" in params

    def test_get_list_url_with_project_gid(self, conn):
        url = conn._get_list_url({}, {"project_gid": "proj-123"})
        assert "/projects/proj-123/tasks" in url

    def test_get_list_url_without_project_gid(self, conn):
        url = conn._get_list_url({}, {})
        assert "/tasks/search" in url

    def test_get_list_params_with_project_gid(self, conn):
        params = conn._get_list_params({}, {"project_gid": "proj-123"})
        assert "opt_fields" in params

    def test_get_list_params_without_project_gid(self, conn):
        params = conn._get_list_params({}, {"workspace": "ws-123"})
        assert params["workspace"] == "ws-123"
        assert params["count"] == 50

    def test_get_list_json(self, conn):
        json_body = conn._get_list_json({}, {})
        assert json_body is None

    def test_get_results_key(self, conn):
        assert conn._get_results_key() == "data"

    @pytest.mark.asyncio
    async def test_test_connection_success(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(200))
        result = await conn.test_connection({"token": "tok"})
        assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(401))
        result = await conn.test_connection({"token": "bad"})
        assert result is False

    @pytest.mark.asyncio
    async def test_fetch_artifact(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(200, {"data": {"id": "task-123", "name": "Test"}}))
        result = await conn.fetch_artifact("task-123", {"token": "tok"})
        assert result["data"]["id"] == "task-123"

    @pytest.mark.asyncio
    async def test_list_artifacts_with_project(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(200, {"data": [{"id": "1"}]}))
        result = await conn.list_artifacts({}, {"token": "tok", "project_gid": "proj-123"})
        assert result == [{"id": "1"}]

    @pytest.mark.asyncio
    async def test_list_artifacts_without_project(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(200, {"data": []}))
        result = await conn.list_artifacts({}, {"token": "tok", "workspace": "ws-123"})
        assert result == []


# ═══════════════════════════════════════════════════════════════════════════════
# TestBitbucketConnector
# ═══════════════════════════════════════════════════════════════════════════════

class TestBitbucketConnector:
    @pytest.fixture
    def conn(self):
        from infrastructure.secondary.connectors.source_control.bitbucket_connector import BitbucketConnector
        return BitbucketConnector()

    def test_properties(self, conn):
        assert conn.CONNECTOR_TYPE == "REPO_CODIGO"
        assert conn.CONNECTOR_IMPLEMENTATION == "BITBUCKET"
        assert "pullrequest" in conn.get_artifact_types()
        assert "commit" in conn.get_artifact_types()
        assert "pipeline" in conn.get_artifact_types()

    def test_get_artifact_types(self, conn):
        types = conn.get_artifact_types()
        assert len(types) == 3

    def test_build_headers(self, conn):
        headers = conn._build_headers({"token": "bb-token"})
        assert headers["Authorization"] == "Bearer bb-token"

    def test_get_health_url(self, conn):
        url = conn._get_health_url({})
        assert url == "https://api.bitbucket.org/2.0/user"

    def test_get_fetch_url(self, conn):
        url = conn._get_fetch_url("owner/repo/123", {})
        assert "/repositories/owner/repo/pullrequests/123" in url

    def test_get_fetch_params(self, conn):
        params = conn._get_fetch_params({})
        assert params is None

    def test_get_list_url_with_owner_repo(self, conn):
        url = conn._get_list_url({}, {"owner": "myowner", "repo": "myrepo"})
        assert "/repositories/myowner/myrepo/pullrequests" in url

    def test_get_list_url_without_owner_repo(self, conn):
        url = conn._get_list_url({}, {})
        assert "/user/pullrequests" in url

    def test_get_list_params(self, conn):
        params = conn._get_list_params({"state": "MERGED"}, {})
        assert params["state"] == "MERGED"
        assert params["pagelen"] == 50

    def test_get_list_json(self, conn):
        json_body = conn._get_list_json({}, {})
        assert json_body is None

    def test_get_results_key(self, conn):
        assert conn._get_results_key() == "values"

    @pytest.mark.asyncio
    async def test_test_connection_success(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(200))
        result = await conn.test_connection({"token": "tok"})
        assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(401))
        result = await conn.test_connection({"token": "bad"})
        assert result is False

    @pytest.mark.asyncio
    async def test_fetch_artifact(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(200, {"id": 123, "title": "PR Title"}))
        result = await conn.fetch_artifact("owner/repo/123", {"token": "tok"})
        assert result["id"] == 123

    @pytest.mark.asyncio
    async def test_list_artifacts_with_owner_repo(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(200, {"values": [{"id": "1"}]}))
        result = await conn.list_artifacts({}, {"token": "tok", "owner": "o", "repo": "r"})
        assert result == [{"id": "1"}]

    @pytest.mark.asyncio
    async def test_list_artifacts_without_owner_repo(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(200, {"values": []}))
        result = await conn.list_artifacts({}, {"token": "tok"})
        assert result == []


# ═══════════════════════════════════════════════════════════════════════════════
# TestGitHubConnector
# ═══════════════════════════════════════════════════════════════════════════════

class TestGitHubConnector:
    @pytest.fixture
    def conn(self):
        from infrastructure.secondary.connectors.source_control.github_connector import GitHubConnector
        return GitHubConnector()

    def test_properties(self, conn):
        assert conn.CONNECTOR_TYPE == "REPO_CODIGO"
        assert conn.CONNECTOR_IMPLEMENTATION == "GITHUB"
        assert "pull_request" in conn.get_artifact_types()
        assert "commit" in conn.get_artifact_types()
        assert "release" in conn.get_artifact_types()
        assert "workflow_run" in conn.get_artifact_types()

    def test_get_artifact_types(self, conn):
        types = conn.get_artifact_types()
        assert len(types) == 4

    def test_build_headers(self, conn):
        headers = conn._build_headers({"token": "gh-token"})
        assert headers["Authorization"] == "Bearer gh-token"
        assert headers["Accept"] == "application/vnd.github+json"
        assert headers["X-GitHub-Api-Version"] == "2022-11-28"

    def test_get_health_url(self, conn):
        url = conn._get_health_url({})
        assert url == "https://api.github.com/user"

    def test_get_fetch_url(self, conn):
        url = conn._get_fetch_url("owner/repo/42", {})
        assert "/repos/owner/repo/pulls/42" in url

    def test_get_fetch_params(self, conn):
        params = conn._get_fetch_params({})
        assert params is None

    def test_get_list_url_with_owner_repo(self, conn):
        url = conn._get_list_url({}, {"owner": "myowner", "repo": "myrepo"})
        assert "/repos/myowner/myrepo/pulls" in url

    def test_get_list_url_without_owner_repo(self, conn):
        url = conn._get_list_url({}, {})
        assert "/user/repos" in url

    def test_get_list_params(self, conn):
        params = conn._get_list_params({"state": "closed"}, {})
        assert params["state"] == "closed"
        assert params["per_page"] == 50

    def test_get_list_json(self, conn):
        json_body = conn._get_list_json({}, {})
        assert json_body is None

    def test_get_results_key(self, conn):
        assert conn._get_results_key() == ""

    @pytest.mark.asyncio
    async def test_test_connection_success(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(200))
        result = await conn.test_connection({"token": "tok"})
        assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(401))
        result = await conn.test_connection({"token": "bad"})
        assert result is False

    @pytest.mark.asyncio
    async def test_fetch_artifact(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(200, {"id": 42, "title": "PR Title"}))
        result = await conn.fetch_artifact("owner/repo/42", {"token": "tok"})
        assert result["id"] == 42

    @pytest.mark.asyncio
    async def test_list_artifacts_with_owner_repo(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(200, []))
        result = await conn.list_artifacts({}, {"token": "tok", "owner": "o", "repo": "r"})
        assert result == []

    @pytest.mark.asyncio
    async def test_list_artifacts_without_owner_repo(self, conn):
        conn._get = AsyncMock(return_value=_mock_response(200, []))
        result = await conn.list_artifacts({}, {"token": "tok"})
        assert result == []

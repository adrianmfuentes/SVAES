import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture
def mock_httpx_client():
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client
        yield mock_client


@pytest.fixture
def connector_config():
    return {
        "base_url": "https://gitlab.example.com",
        "token": "test-token",
        "project_id": "12345",
    }


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

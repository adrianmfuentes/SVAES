from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture(autouse=True)
def _no_migrations():
    with patch("main.command.upgrade"):
        yield


@pytest.fixture(autouse=True)
def _mock_db():
    mock_session = AsyncMock()
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    mock_factory = MagicMock(return_value=mock_cm)
    with patch("infrastructure.database.session._get_engine", return_value=mock_factory):
        yield


class TestHealthEndpoint:
    def test_returns_200(self):
        with TestClient(app) as client:
            response = client.get("/health")
        assert response.status_code == 200

    def test_response_has_ok_status(self):
        with TestClient(app) as client:
            response = client.get("/health")
        assert response.json()["status"] == "ok"

    def test_response_has_message(self):
        with TestClient(app) as client:
            response = client.get("/health")
        assert "message" in response.json()


class TestRequestLoggingMiddleware:
    def test_middleware_does_not_break_responses(self):
        with TestClient(app) as client:
            r1 = client.get("/health")
            r2 = client.get("/health")
        assert r1.status_code == 200
        assert r2.status_code == 200

    def test_unknown_path_returns_404_through_middleware(self):
        with TestClient(app) as client:
            response = client.get("/this-path-does-not-exist")
        assert response.status_code == 404

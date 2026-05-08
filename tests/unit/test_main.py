"""
Tests for FastAPI application setup.

Uses TestClient (sync ASGI driver) to verify the health endpoint and the
request-logging middleware without requiring an external server or database.
The lifespan context manager is exercised via the `with TestClient(app)` block.
"""

from fastapi.testclient import TestClient

from main import app


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

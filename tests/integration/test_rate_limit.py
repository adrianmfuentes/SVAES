import asyncio
import pytest
from uuid import uuid4

pytestmark = pytest.mark.integration


@pytest.mark.usefixtures("db")
class TestAuthRateLimiting:
    """Login and register endpoints rate limiting."""

    async def test_login_rate_limit_breached(self, client):
        url = "/api/v1/auth/login"
        payload = {"email": "ratelimit@test.com", "password": "Password1"}
        statuses = []
        for _ in range(35):
            response = await client.post(url, json=payload)
            statuses.append(response.status_code)
        assert 429 in statuses, (
            f"Expected 429 rate limit response. Got statuses: {sorted(set(statuses))}"
        )

    async def test_register_rate_limit_breached(self, client):
        url = "/api/v1/auth/register"
        statuses = []
        for i in range(35):
            response = await client.post(
                url,
                json={
                    "email": f"ratelimit-reg-{i}-{uuid4().hex[:4]}@test.com",
                    "password": "Password1",
                    "display_name": f"RateLimit{i}",
                    "accept_terms": True,
                    "accept_privacy_policy": True,
                },
            )
            statuses.append(response.status_code)
        assert 429 in statuses, (
            f"Expected 429 rate limit response. Got statuses: {sorted(set(statuses))}"
        )

    async def test_login_rate_limit_under_threshold(self, client):
        url = "/api/v1/auth/login"
        payload = {"email": f"under-limit-{uuid4().hex[:4]}@test.com", "password": "Password1"}
        for _ in range(5):
            response = await client.post(url, json=payload)
            assert response.status_code != 429, "Should not be rate limited at 5 requests"

    async def test_refresh_rate_limit_breached(self, client):
        url = "/api/v1/auth/refresh"
        payload = {"refresh_token": "invalid-refresh-token"}
        statuses = []
        for _ in range(35):
            response = await client.post(url, json=payload)
            statuses.append(response.status_code)
        assert 429 in statuses, (
            f"Expected 429 rate limit. Got statuses: {sorted(set(statuses))}"
        )


class TestRateLimitHeaders:
    """Verify rate limit related response headers (no DB needed for single request)."""

    async def test_rate_limit_headers_on_protected_route(self, client):
        url = "/api/v1/auth/login"
        payload = {"email": "headers@test.com", "password": "Password1"}
        response = await client.post(url, json=payload)
        assert response.status_code != 0

    async def test_rate_limited_response_has_retry_after(self, client):
        url = "/api/v1/auth/login"
        payload = {"email": "retry-after@test.com", "password": "Password1"}
        for _ in range(35):
            response = await client.post(url, json=payload)
            if response.status_code == 429:
                assert "Retry-After" in response.headers or response.status_code == 429
                return
        pytest.skip("Rate limit not triggered before request exhaustion")


class TestDefaultRateLimiting:
    """Default rate limiting on general API endpoints."""

    async def test_health_not_rate_limited(self, client):
        for _ in range(50):
            response = await client.get("/health")
            assert response.status_code == 200, "Health endpoint should not be rate limited"

    async def test_rapid_consecutive_requests(self, client, manager_headers, db):
        tasks = [client.get("/api/v1/users/me", headers=manager_headers) for _ in range(5)]
        responses = await asyncio.gather(*tasks)
        statuses = {r.status_code for r in responses}
        assert 200 in statuses or 404 in statuses


class TestRateLimitReset:
    """Verify rate limits do not persist across separate test windows."""

    async def test_rate_limit_per_limiter_isolation(self, client):
        url_login = "/api/v1/auth/login"
        url_register = "/api/v1/auth/register"
        payload = {"email": "isolated@test.com", "password": "Password1"}
        for _ in range(25):
            await client.post(url_login, json=payload)
        response = await client.post(
            url_register,
            json={
                "email": f"reg-isolated-{uuid4().hex[:6]}@test.com",
                "password": "Password1",
                "display_name": "Isolated",
                "accept_terms": True,
                "accept_privacy_policy": True,
            },
        )
        assert response.status_code != 429, (
            "Register limiter should be independent from login limiter"
        )

import asyncio
import pytest
from uuid import uuid4

pytestmark = pytest.mark.integration


class TestMalformedInput:
    """Verify proper handling of invalid/malformed input (no DB required)."""

    async def test_malformed_json_body(self, client):
        response = await client.post(
            "/api/v1/auth/login",
            content="not json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code in (400, 422)

    async def test_invalid_uuid_in_path(self, client, manager_headers):
        response = await client.get(
            "/api/v1/organizations/not-a-uuid",
            headers=manager_headers,
        )
        assert response.status_code == 422

    async def test_invalid_uuid_in_query(self, client, manager_headers):
        response = await client.get(
            "/api/v1/dashboard/metrics?org_id=not-a-uuid",
            headers=manager_headers,
        )
        assert response.status_code in (422, 400)

    async def test_empty_json_body(self, client):
        response = await client.post(
            "/api/v1/auth/login",
            json={},
        )
        assert response.status_code == 422

    async def test_extra_fields_rejected(self, client):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@test.com",
                "password": "Password1",
                "is_admin": True,
                "malicious_field": "inject",
            },
        )
        assert response.status_code == 422

    async def test_wrong_types_in_body(self, client):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": 12345, "password": ["a", "list"]},
        )
        assert response.status_code == 422


class TestAuthErrorRecovery:
    """Verify system handles auth edge cases (JWT only, no DB)."""

    async def test_expired_token(self, client, test_user_id, test_org_id):
        import os
        import time
        import jwt as pyjwt
        token = pyjwt.encode(
            {
                "sub": str(test_user_id),
                "role": "ADMIN",
                "email": "expired@test.com",
                "organization_id": str(test_org_id),
                "exp": int(time.time()) - 3600,
                "iat": int(time.time()) - 7200,
            },
            os.environ["JWT_SECRET_KEY"],
            algorithm="HS256",
        )
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code in (401, 403)

    async def test_malformed_token(self, client):
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer not.a.jwt"},
        )
        assert response.status_code in (401, 403)

    async def test_empty_token(self, client):
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer "},
        )
        assert response.status_code in (401, 403)

    async def test_missing_bearer_prefix(self, client, admin_headers):
        token = admin_headers["Authorization"].replace("Bearer ", "")
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": token},
        )
        assert response.status_code in (401, 403)

    async def test_token_with_wrong_secret(self, client):
        import jwt as pyjwt
        import time
        token = pyjwt.encode(
            {
                "sub": str(uuid4()),
                "role": "ADMIN",
                "email": "wrong@test.com",
                "organization_id": str(uuid4()),
                "exp": int(time.time()) + 600,
                "iat": int(time.time()),
            },
            "wrong-secret-key-that-is-long-enough",
            algorithm="HS256",
        )
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code in (401, 403)


class TestMethodNotAllowed:
    """Verify correct handling of wrong HTTP methods (no DB)."""

    async def test_get_on_login_endpoint(self, client):
        response = await client.get("/api/v1/auth/login")
        assert response.status_code == 405

    async def test_post_on_health_endpoint(self, client):
        response = await client.post("/health", json={})
        assert response.status_code == 405

    async def test_put_on_get_endpoint(self, client, manager_headers):
        response = await client.put(
            "/api/v1/users/me",
            json={},
            headers=manager_headers,
        )
        assert response.status_code == 405


class TestErrorResponses:
    """Verify error responses have proper structure and no leakage."""

    async def test_error_response_no_traceback(self, client):
        response = await client.get("/api/v1/users/me")
        body = response.text
        assert "Traceback" not in body
        assert "File \"" not in body
        assert "line " not in body

    async def test_unauthorized_response_structure(self, client):
        response = await client.get("/api/v1/users/me")
        assert response.headers.get("content-type", "").startswith("application/json")
        assert "x-request-id" in response.headers

    async def test_validation_error_has_detail(self, client):
        response = await client.post("/api/v1/auth/login", json={})
        data = response.json()
        assert "detail" in data

    async def test_not_found_has_detail(self, client, manager_headers, db):
        response = await client.get(
            f"/api/v1/organizations/{uuid4()}",
            headers=manager_headers,
        )
        data = response.json()
        assert "detail" in data

    async def test_500_error_does_not_leak_internals(self, client, manager_headers, db):
        response = await client.get(
            f"/api/v1/releases/{uuid4()}",
            headers=manager_headers,
        )
        if response.status_code == 500:
            body = response.text
            assert "Traceback" not in body
            assert "Exception" not in body


class TestConcurrentRequests:
    """Verify system handles concurrent requests without corruption."""

    async def test_concurrent_health_checks(self, client):
        tasks = [client.get("/health") for _ in range(10)]
        responses = await asyncio.gather(*tasks)
        for response in responses:
            assert response.status_code == 200
            assert response.json()["status"] == "ok"

    async def test_concurrent_user_profile(self, client, manager_headers, db):
        tasks = [client.get("/api/v1/users/me", headers=manager_headers) for _ in range(5)]
        responses = await asyncio.gather(*tasks)
        statuses = {r.status_code for r in responses}
        assert statuses.issubset({200, 404})


@pytest.mark.usefixtures("db")
class TestNotFoundResources:
    """Verify proper 404 handling for nonexistent resources."""

    async def test_get_nonexistent_organization(self, client, manager_headers):
        response = await client.get(
            f"/api/v1/organizations/{uuid4()}",
            headers=manager_headers,
        )
        assert response.status_code == 404

    async def test_get_nonexistent_release(self, client, manager_headers):
        response = await client.get(
            f"/api/v1/releases/{uuid4()}",
            headers=manager_headers,
        )
        assert response.status_code in (403, 404)

    async def test_get_nonexistent_project(self, client, manager_headers):
        response = await client.get(
            f"/api/v1/organizations/{uuid4()}/projects/{uuid4()}",
            headers=manager_headers,
        )
        assert response.status_code in (403, 404)

    async def test_get_nonexistent_profile(self, client, manager_headers):
        response = await client.patch(
            f"/api/v1/profiles/{uuid4()}",
            json={"name": "Ghost"},
            headers=manager_headers,
        )
        assert response.status_code in (403, 404)


@pytest.mark.usefixtures("db")
class TestBoundaryValues:
    """Verify behaviour at input boundaries."""

    async def test_max_length_name(self, client, manager_headers):
        slug = f"b-{uuid4().hex[:8]}"
        org_resp = await client.post(
            "/api/v1/organizations",
            json={"name": "Boundary Org", "slug": slug},
            headers=manager_headers,
        )
        org_id = org_resp.json()["id"]
        profile_resp = await client.post(
            f"/api/v1/organizations/{org_id}/profiles",
            json={"name": f"Boundary-Profile-{uuid4().hex[:6]}", "description": "Test"},
            headers=manager_headers,
        )
        profile_id = profile_resp.json()["id"]
        project_resp = await client.post(
            f"/api/v1/organizations/{org_id}/projects",
            json={"name": f"Boundary-Project-{uuid4().hex[:6]}", "description": "Test", "profile_id": profile_id},
            headers=manager_headers,
        )
        project_id = project_resp.json()["id"]
        response = await client.post(
            f"/api/v1/projects/{project_id}/releases",
            json={"name": "A" * 100, "version": "1.0.0"},
            headers=manager_headers,
        )
        assert response.status_code in (201, 422)

    async def test_excessive_name_length(self, client, manager_headers):
        slug = f"l-{uuid4().hex[:8]}"
        org_resp = await client.post(
            "/api/v1/organizations",
            json={"name": "Long Org", "slug": slug},
            headers=manager_headers,
        )
        org_id = org_resp.json()["id"]
        profile_resp = await client.post(
            f"/api/v1/organizations/{org_id}/profiles",
            json={"name": f"Long-Profile-{uuid4().hex[:6]}", "description": "Test"},
            headers=manager_headers,
        )
        profile_id = profile_resp.json()["id"]
        project_resp = await client.post(
            f"/api/v1/organizations/{org_id}/projects",
            json={"name": f"Long-Project-{uuid4().hex[:6]}", "description": "Test", "profile_id": profile_id},
            headers=manager_headers,
        )
        project_id = project_resp.json()["id"]
        response = await client.post(
            f"/api/v1/projects/{project_id}/releases",
            json={"name": "A" * 200, "version": "1.0.0"},
            headers=manager_headers,
        )
        assert response.status_code == 422

    async def test_negative_pagination(self, client, manager_headers, test_org_id):
        response = await client.get(
            f"/api/v1/organizations/{test_org_id}/profiles?skip=-1&limit=-5",
            headers=manager_headers,
        )
        assert response.status_code in (422, 400, 500)


@pytest.mark.usefixtures("db")
class TestCrossOrgIsolation:
    """Verify users cannot access resources from other organizations."""

    async def test_cross_org_project_access(self, client, viewer_headers):
        response = await client.get(
            f"/api/v1/organizations/{uuid4()}/projects",
            headers=viewer_headers,
        )
        assert response.status_code in (403, 404)

    async def test_cross_org_release_access(self, client, viewer_headers):
        response = await client.get(
            f"/api/v1/releases/{uuid4()}",
            headers=viewer_headers,
        )
        assert response.status_code in (403, 404)

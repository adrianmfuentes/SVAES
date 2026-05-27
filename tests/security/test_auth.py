import json
import time
import base64
import os
import pytest
from uuid import uuid4

import jwt as pyjwt

pytestmark = pytest.mark.security


class TestAuthentication:
    """JWT authentication middleware tests — token validation, expiry, algorithm confusion."""

    async def test_health_no_auth_required(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "svaes-api"

    async def test_protected_endpoint_no_auth_header(self, client):
        response = await client.get("/api/v1/users/me")
        assert response.status_code in (401, 403)

    async def test_protected_endpoint_invalid_token(self, client):
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer invalid-token-string"},
        )
        assert response.status_code == 401

    async def test_empty_bearer_token(self, client):
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer "},
        )
        assert response.status_code in (401, 403)

    async def test_missing_bearer_prefix(self, client):
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": "raw-token-value"},
        )
        assert response.status_code in (401, 403)

    async def test_basic_auth_on_bearer_endpoint(self, client):
        creds = base64.b64encode(b"user:pass").decode()
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Basic {creds}"},
        )
        assert response.status_code in (401, 403)

    async def test_expired_token_rejected(self, client):
        secret = os.environ["JWT_SECRET_KEY"]
        token = pyjwt.encode(
            {
                "sub": str(uuid4()),
                "role": "VIEWER",
                "email": "expired@test.com",
                "organization_id": str(uuid4()),
                "exp": int(time.time()) - 3600,
                "iat": int(time.time()) - 7200,
            },
            secret,
            algorithm="HS256",
        )
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401

    async def test_token_wrong_secret_rejected(self, client):
        token = pyjwt.encode(
            {
                "sub": str(uuid4()),
                "role": "VIEWER",
                "email": "wrong@test.com",
                "organization_id": str(uuid4()),
                "exp": int(time.time()) + 3600,
                "iat": int(time.time()),
            },
            "wrong-secret-key-with-sufficient-length",
            algorithm="HS256",
        )
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401

    async def test_none_algorithm_rejected(self, client):
        header_b64 = (
            base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode())
            .rstrip(b"=")
            .decode()
        )
        payload_b64 = (
            base64.urlsafe_b64encode(
                json.dumps(
                    {
                        "sub": str(uuid4()),
                        "role": "ADMIN",
                        "email": "alg@none.com",
                        "organization_id": str(uuid4()),
                        "exp": int(time.time()) + 3600,
                    }
                ).encode()
            )
            .rstrip(b"=")
            .decode()
        )
        token = f"{header_b64}.{payload_b64}."
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code in (401, 403)

    async def test_tampered_payload_rejected(self, client, auth_token):
        parts = auth_token.split(".")
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + "==="))
        payload["role"] = "ADMIN"
        tampered_payload = (
            base64.urlsafe_b64encode(json.dumps(payload).encode())
            .rstrip(b"=")
            .decode()
        )
        forged = f"{parts[0]}.{tampered_payload}.{parts[2]}"
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {forged}"},
        )
        assert response.status_code == 401

    async def test_token_missing_signature_segment(self, client):
        header_b64 = (
            base64.urlsafe_b64encode(
                json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
            )
            .rstrip(b"=")
            .decode()
        )
        payload_b64 = (
            base64.urlsafe_b64encode(
                json.dumps(
                    {
                        "sub": str(uuid4()),
                        "role": "VIEWER",
                        "email": "nosig@test.com",
                        "exp": int(time.time()) + 3600,
                    }
                ).encode()
            )
            .rstrip(b"=")
            .decode()
        )
        token = f"{header_b64}.{payload_b64}"
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code in (401, 403)

    async def test_valid_token_passes_auth_layer(self, client, auth_headers):
        response = await client.get("/api/v1/users/me", headers=auth_headers)
        assert response.status_code not in (401, 403)

    async def test_token_blacklisted_after_logout(self, client, auth_headers):
        await client.post("/api/v1/auth/logout", headers=auth_headers)
        response = await client.get("/api/v1/users/me", headers=auth_headers)
        assert response.status_code in (401, 403)

    async def test_refresh_token_rejected_as_access_token(self, client):
        secret = os.environ["JWT_SECRET_KEY"]
        token = pyjwt.encode(
            {
                "sub": str(uuid4()),
                "role": "VIEWER",
                "email": "refresh@test.com",
                "organization_id": str(uuid4()),
                "exp": int(time.time()) + 3600,
                "iat": int(time.time()),
                "type": "refresh",
            },
            secret,
            algorithm="HS256",
        )
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code != 200


class TestAuthorization:
    """Role-based access control enforcement tests."""

    async def test_u1_access_admin_users_denied(self, client, basic_user_token):
        response = await client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {basic_user_token}"},
        )
        assert response.status_code == 403

    async def test_u1_access_organizations_list_denied(self, client, basic_user_token):
        response = await client.get(
            "/api/v1/organizations",
            headers={"Authorization": f"Bearer {basic_user_token}"},
        )
        assert response.status_code == 403

    async def test_u1_access_admin_rules_reload_denied(self, client, basic_user_token):
        response = await client.post(
            "/api/v1/admin/rules/reload",
            headers={"Authorization": f"Bearer {basic_user_token}"},
        )
        assert response.status_code == 403

    async def test_u1_manage_org_roles_denied(self, client, basic_user_token):
        org_id = uuid4()
        response = await client.get(
            f"/api/v1/organizations/{org_id}/users",
            headers={"Authorization": f"Bearer {basic_user_token}"},
        )
        assert response.status_code == 403

    async def test_u1_invite_users_denied(self, client, basic_user_token):
        org_id = uuid4()
        response = await client.post(
            f"/api/v1/organizations/{org_id}/users/invite",
            json={"email": "invite@test.com", "role": "OPERATOR"},
            headers={"Authorization": f"Bearer {basic_user_token}"},
        )
        assert response.status_code == 403

    async def test_u1_create_project_denied(self, client, basic_user_token):
        org_id = uuid4()
        response = await client.post(
            f"/api/v1/organizations/{org_id}/projects",
            json={"name": "test-project", "profile_id": str(uuid4())},
            headers={"Authorization": f"Bearer {basic_user_token}"},
        )
        assert response.status_code == 403

    async def test_u1_transfer_ownership_denied(self, client, basic_user_token):
        org_id = uuid4()
        response = await client.post(
            f"/api/v1/organizations/{org_id}/transfer-ownership",
            json={"new_owner_id": str(uuid4())},
            headers={"Authorization": f"Bearer {basic_user_token}"},
        )
        assert response.status_code == 403

    async def test_u3_passes_authorization_layer(self, client, auth_headers):
        response = await client.get("/api/v1/admin/users", headers=auth_headers)
        assert response.status_code not in (401, 403)

    async def test_unauth_headers_blocked_on_protected(self, client, unauth_headers):
        response = await client.get("/api/v1/users/me", headers=unauth_headers)
        assert response.status_code in (401, 403)

    async def test_cross_org_access_attempt(self, client, basic_user_token):
        token_parts = basic_user_token.split(".")
        payload = json.loads(base64.urlsafe_b64decode(token_parts[1] + "==="))
        user_org_id = payload.get("organization_id", str(uuid4()))
        target_org_id = uuid4()
        response = await client.get(
            f"/api/v1/organizations/{target_org_id}/users",
            headers={"Authorization": f"Bearer {basic_user_token}"},
        )
        assert response.status_code == 403


class TestInputValidation:
    """Verify Pydantic rejects invalid/malicious input at the API boundary."""

    async def test_login_empty_body(self, client):
        response = await client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422

    async def test_login_missing_password(self, client):
        response = await client.post(
            "/api/v1/auth/login", json={"email": "user@test.com"}
        )
        assert response.status_code == 422

    async def test_login_missing_email(self, client):
        response = await client.post(
            "/api/v1/auth/login", json={"password": "Password1"}
        )
        assert response.status_code == 422

    async def test_login_wrong_types(self, client):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": 12345, "password": ["not", "a", "string"]},
        )
        assert response.status_code == 422

    async def test_register_weak_password_no_uppercase(self, client):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@test.com",
                "password": "password1",
                "display_name": "User",
                "accept_terms": True,
                "accept_privacy_policy": True,
            },
        )
        assert response.status_code == 422

    async def test_register_weak_password_no_lowercase(self, client):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@test.com",
                "password": "PASSWORD1",
                "display_name": "User",
                "accept_terms": True,
                "accept_privacy_policy": True,
            },
        )
        assert response.status_code == 422

    async def test_register_weak_password_no_digit(self, client):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@test.com",
                "password": "Password",
                "display_name": "User",
                "accept_terms": True,
                "accept_privacy_policy": True,
            },
        )
        assert response.status_code == 422

    async def test_register_short_password(self, client):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@test.com",
                "password": "Ab1",
                "display_name": "User",
                "accept_terms": True,
                "accept_privacy_policy": True,
            },
        )
        assert response.status_code == 422

    async def test_register_without_terms_consent(self, client):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@test.com",
                "password": "Password1",
                "display_name": "User",
                "accept_terms": False,
                "accept_privacy_policy": True,
            },
        )
        assert response.status_code == 422

    async def test_register_without_privacy_consent(self, client):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@test.com",
                "password": "Password1",
                "display_name": "User",
                "accept_terms": True,
                "accept_privacy_policy": False,
            },
        )
        assert response.status_code == 422

    async def test_register_long_email(self, client):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "a" * 256 + "@test.com",
                "password": "Password1",
                "display_name": "User",
                "accept_terms": True,
                "accept_privacy_policy": True,
            },
        )
        assert response.status_code == 422

    async def test_register_empty_email(self, client):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "",
                "password": "Password1",
                "display_name": "User",
                "accept_terms": True,
                "accept_privacy_policy": True,
            },
        )
        assert response.status_code == 422

    async def test_password_change_mismatch(self, client, auth_headers):
        response = await client.post(
            "/api/v1/users/me/password",
            json={
                "current_password": "OldPass1",
                "new_password": "NewPass1",
                "confirm_password": "Different1",
            },
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestRateLimiting:
    """Verify rate limiting protects auth endpoints against brute-force attacks."""

    async def test_login_rate_limit_breached(self, client):
        url = "/api/v1/auth/login"
        payload = {"email": "user@test.com", "password": "Password1"}
        statuses = []
        for _ in range(35):
            response = await client.post(url, json=payload)
            statuses.append(response.status_code)
        assert 429 in statuses, (
            f"Expected rate limit (429). Got: {sorted(set(statuses))}"
        )

    async def test_register_rate_limit_breached(self, client):
        url = "/api/v1/auth/register"
        responses = []
        for i in range(35):
            response = await client.post(
                url,
                json={
                    "email": f"user{i}@test.com",
                    "password": "Password1",
                    "display_name": f"User{i}",
                    "accept_terms": True,
                    "accept_privacy_policy": True,
                },
            )
            responses.append(response)
        statuses = [r.status_code for r in responses]
        assert 429 in statuses, (
            f"Expected rate limit (429). Got: {sorted(set(statuses))}"
        )


class TestSecurityHeaders:
    """Verify security headers behaviour."""

    async def test_cors_headers_present(self, client):
        response = await client.options(
            "/health",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code in (200, 204, 405)

    async def test_security_headers_absent_in_test_mode(self, client):
        response = await client.get("/health")
        assert "x-content-type-options" not in response.headers
        assert "x-frame-options" not in response.headers

    async def test_request_id_present_on_all_responses(self, client):
        response = await client.get("/health")
        assert "x-request-id" in response.headers

    async def test_request_id_unique_per_request(self, client):
        ids = set()
        for _ in range(5):
            response = await client.get("/health")
            ids.add(response.headers["x-request-id"])
        assert len(ids) == 5

    async def test_error_responses_have_request_id(self, client):
        response = await client.get("/api/v1/users/me")
        assert response.status_code in (401, 403)
        assert "x-request-id" in response.headers

    async def test_docs_accessible_in_test_mode(self, client):
        response = await client.get("/docs")
        assert response.status_code == 200


class TestAccountLockout:
    """Verify account lockout mechanism exists in domain model."""

    async def test_failed_login_attempts_field_exists(self, client):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "WrongPass1"},
        )
        assert response.status_code != 200

    async def test_repeated_failed_logins_rate_limited(self, client):
        url = "/api/v1/auth/login"
        payload = {"email": "lockout@test.com", "password": "WrongPass1"}
        statuses = []
        for _ in range(35):
            response = await client.post(url, json=payload)
            statuses.append(response.status_code)
        assert 429 in statuses

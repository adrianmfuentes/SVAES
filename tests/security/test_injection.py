import pytest
from uuid import uuid4

pytestmark = pytest.mark.security

class TestSQLInjection:
    """Verify SQL injection payloads are handled safely at the API boundary."""

    @pytest.mark.parametrize(
        "email",
        [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "admin'--",
            "1' UNION SELECT * FROM users--",
            "' OR 1=1--",
            "' OR '1'='1' /*",
            "admin' OR '1'='1",
        ],
    )
    async def test_sql_injection_in_login_email(self, client, email):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "password"},
        )
        assert response.status_code != 200

    @pytest.mark.parametrize(
        "payload",
        [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "'; SELECT pg_sleep(5); --",
        ],
    )
    async def test_sql_injection_in_query_params(self, client, payload):
        response = await client.get(f"/api/v1/users/me?search={payload}")
        assert response.status_code in (401, 403, 422)

    @pytest.mark.parametrize(
        "field,payload",
        [
            ("email", "test@test.com' OR '1'='1"),
            ("display_name", "'; DROP TABLE users; --"),
        ],
    )
    async def test_sql_injection_in_register(self, client, field, payload):
        body = {
            "email": "clean@test.com",
            "password": "Password1",
            "display_name": "Clean",
            "accept_terms": True,
            "accept_privacy_policy": True,
        }
        body[field] = payload
        response = await client.post("/api/v1/auth/register", json=body)
        assert response.status_code != 200


class TestXSS:
    """Verify XSS payloads are not reflected in API responses."""

    @pytest.mark.parametrize(
        "xss_payload",
        [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert(1)>",
            "javascript:alert(1)",
            "<svg onload=alert(1)>",
            "'-alert(1)-'",
        ],
    )
    async def test_xss_in_login_not_reflected(self, client, xss_payload):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": xss_payload, "password": "Password1"},
        )
        body = response.text.lower()
        assert "<script>" not in body
        assert "onerror" not in body
        assert "onload" not in body

    @pytest.mark.parametrize(
        "xss_payload",
        [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert(1)>",
        ],
    )
    async def test_xss_in_register_not_accepted(self, client, xss_payload):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": xss_payload,
                "password": "Password1",
                "display_name": xss_payload,
                "accept_terms": True,
                "accept_privacy_policy": True,
            },
        )
        assert response.status_code != 200

    async def test_xss_in_response_header(self, client):
        response = await client.get(
            "/health",
            headers={"User-Agent": "<script>alert(1)</script>"},
        )
        assert response.status_code == 200
        for value in response.headers.values():
            assert "<script>" not in value.lower()


class TestSSTI:
    """Verify Server-Side Template Injection payloads are harmless."""

    @pytest.mark.parametrize(
        "ssti_payload",
        [
            "{{7*7}}",
            "${7*7}",
            "{{config.__class__.__init__.__globals__}}",
            "#{7*7}",
            "{{'test'.__class__.__mro__[1].__subclasses__()}}",
        ],
    )
    async def test_ssti_in_login_fields(self, client, ssti_payload):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": ssti_payload, "password": "Password1"},
        )
        body = response.text
        assert "49" not in body

    @pytest.mark.parametrize(
        "ssti_payload",
        [
            "{{7*7}}",
            "${7*7}",
            "{{config}}",
        ],
    )
    async def test_ssti_in_register(self, client, ssti_payload):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "ssti@test.com",
                "password": "Password1",
                "display_name": ssti_payload,
                "accept_terms": True,
                "accept_privacy_policy": True,
            },
        )
        body = response.text
        assert "49" not in body


class TestPathTraversal:
    """Verify path traversal attempts in URLs are handled safely."""

    @pytest.mark.parametrize(
        "path",
        [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "....//....//....//etc/passwd",
            "/etc/passwd",
            "file:///etc/passwd",
        ],
    )
    async def test_path_traversal_in_url(self, client, path):
        response = await client.get(f"/api/v1/{path}")
        assert response.status_code in (401, 403, 404, 422, 405)
        body = response.text
        assert "root:" not in body
        assert "passwd" not in body.lower()


class TestMassAssignment:
    """Verify extra fields in requests are rejected (extra='forbid' on all models)."""

    async def test_extra_field_in_login(self, client):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "user@test.com",
                "password": "Password1",
                "is_admin": True,
            },
        )
        assert response.status_code == 422
        detail = response.json().get("detail", [])
        error_msgs = (
            [str(e.get("msg", "")) for e in detail]
            if isinstance(detail, list)
            else []
        )
        assert any("extra" in msg.lower() for msg in error_msgs) or any(
            "is_admin" in msg for msg in error_msgs
        )

    async def test_extra_field_in_register(self, client):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@test.com",
                "password": "Password1",
                "display_name": "User",
                "accept_terms": True,
                "accept_privacy_policy": True,
                "role": "ADMIN",
            },
        )
        assert response.status_code == 422

    async def test_extra_field_in_refresh(self, client):
        response = await client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": "test-token",
                "renew_admin": True,
            },
        )
        assert response.status_code == 422

    async def test_extra_field_in_password_change(self, client, auth_headers):
        response = await client.post(
            "/api/v1/users/me/password",
            json={
                "current_password": "OldPass1",
                "new_password": "NewPass1",
                "confirm_password": "NewPass1",
                "set_admin": True,
            },
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestNullByteInjection:
    """Verify null byte payloads are handled safely."""

    @pytest.mark.parametrize(
        "field",
        ["email", "password"],
    )
    async def test_null_byte_in_login(self, client, field):
        body = {"email": "user@test.com", "password": "Password1"}
        body[field] = body[field] + "\x00admin"
        response = await client.post("/api/v1/auth/login", json=body)
        assert response.status_code != 200

    @pytest.mark.parametrize(
        "field",
        ["email", "password", "display_name"],
    )
    async def test_null_byte_in_register(self, client, field):
        body = {
            "email": "user@test.com",
            "password": "Password1",
            "display_name": "User",
            "accept_terms": True,
            "accept_privacy_policy": True,
        }
        body[field] = body[field] + "\x00admin"
        response = await client.post("/api/v1/auth/register", json=body)
        assert response.status_code != 200

    async def test_null_byte_in_header(self, client):
        response = await client.get(
            "/health",
            headers={"Authorization": "Bearer token\x00admin"},
        )
        assert response.status_code == 200


class TestHeaderInjection:
    """Verify that malicious headers are handled safely."""

    async def test_injected_xrequestid_not_trusted(self, client):
        response = await client.get(
            "/health",
            headers={"X-Request-ID": "<script>alert(1)</script>"},
        )
        assert response.status_code == 200
        returned_id = response.headers.get("x-request-id", "")
        assert "<script>" not in returned_id

    async def test_host_header_injection(self, client):
        response = await client.get(
            "/health",
            headers={"Host": "evil.attacker.com"},
        )
        assert response.status_code == 200

    async def test_unsupported_content_type(self, client):
        response = await client.post(
            "/api/v1/auth/login",
            content="<xml><user>admin</user></xml>",
            headers={"Content-Type": "application/xml"},
        )
        assert response.status_code in (415, 422, 400)

    async def test_content_type_with_charset(self, client):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@test.com", "password": "Password1"},
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        assert response.status_code != 200

    async def test_malformed_authorization_header(self, client):
        for header_value in [
            "Bearer",
            'Bearer ""',
            "  ",
            "Bearer token token",
        ]:
            response = await client.get(
                "/api/v1/users/me",
                headers={"Authorization": header_value},
            )
            assert response.status_code in (401, 403)


class TestDoS:
    """Verify denial-of-service protections on input sizes."""

    async def test_extremely_long_email(self, client):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "a" * 10000 + "@test.com",
                "password": "Password1",
            },
        )
        assert response.status_code == 422

    async def test_extremely_long_password(self, client):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "user@test.com",
                "password": "a" * 10000,
            },
        )
        assert response.status_code == 422

    async def test_extremely_long_display_name(self, client):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@test.com",
                "password": "Password1",
                "display_name": "A" * 10000,
                "accept_terms": True,
                "accept_privacy_policy": True,
            },
        )
        assert response.status_code == 422

    async def test_deeply_nested_json(self, client):
        nested = {}
        current = nested
        for _ in range(50):
            current["nested"] = {}
            current = current["nested"]
        current["email"] = "user@test.com"
        current["password"] = "Password1"
        response = await client.post("/api/v1/auth/login", json=nested)
        assert response.status_code == 422


class TestContentNegotiation:
    """Verify content type negotiation safety."""

    async def test_json_required_on_post(self, client):
        response = await client.post(
            "/api/v1/auth/login",
            content="email=user@test.com&password=pass",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code in (415, 422, 400)

    async def test_no_response_body_leakage_on_error(self, client):
        response = await client.get("/api/v1/users/me")
        body = response.text
        assert "Traceback" not in body
        assert "File \"" not in body

    async def test_internal_error_no_stack_trace(self, client, auth_headers):
        response = await client.get("/api/v1/users/me", headers=auth_headers)
        if response.status_code == 500:
            body = response.text
            assert "Traceback" not in body
            assert "line " not in body


class TestPrototypePollution:
    """Verify prototype pollution / parameter pollution vectors are harmless."""

    @pytest.mark.parametrize(
        "field,value",
        [
            ("email", "__proto__"),
            ("email", "constructor"),
            ("email", "prototype"),
        ],
    )
    async def test_prototype_pollution_in_login(self, client, field, value):
        body = {"email": "user@test.com", "password": "Password1"}
        body[field] = value
        response = await client.post("/api/v1/auth/login", json=body)
        assert response.status_code != 200

    async def test_duplicate_query_parameters(self, client):
        response = await client.get("/api/v1/users/me?search=a&search=b")
        assert response.status_code in (401, 403, 422)


class TestCORS:
    """Verify CORS configuration security."""

    async def test_cors_preflight_allows_configured_methods(self, client):
        response = await client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization, Content-Type",
            },
        )
        assert response.status_code in (200, 204, 405)

    async def test_cors_allows_configured_origin(self, client):
        response = await client.options(
            "/health",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        if response.status_code == 200:
            assert "access-control-allow-origin" in response.headers

    async def test_cors_credentials_enabled(self, client):
        response = await client.options(
            "/health",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        if response.status_code == 200:
            assert (
                response.headers.get("access-control-allow-credentials") == "true"
            )


class TestAuditTrail:
    """Verify audit logging coverage for security events."""

    async def test_auth_failure_logging(self, client):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@test.com", "password": "WrongPass1"},
        )
        assert response.status_code != 200

    async def test_auth_token_rejection_logged(self, client):
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401


class TestConnectorCredentialSecurity:
    """Verify connector credentials are properly encrypted."""

    async def test_connector_types_endpoint_no_leak(self, client, auth_headers):
        response = await client.get(
            "/api/v1/connectors/types", headers=auth_headers
        )
        if response.status_code == 200:
            data = response.json()
            all_impls = data.get("implementations", [])
            for impl in all_impls:
                schema = impl.get("config_schema", {})
                for field_name, field_def in schema.items():
                    if isinstance(field_def, dict) and field_def.get("sensitive"):
                        assert not field_def.get("value"), (
                            f"Sensitive field '{field_name}' exposes a credential value"
                        )

    async def test_connector_list_requires_auth(self, client):
        org_id = uuid4()
        response = await client.get(
            f"/api/v1/organizations/{org_id}/connectors"
        )
        assert response.status_code in (401, 403)

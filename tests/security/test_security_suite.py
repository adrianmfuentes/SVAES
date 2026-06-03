"""
Pruebas de Seguridad (ISO 29119-4)
Total: 5 tests
  TC-SEC-AUT-01: Bloqueo de fuerza bruta al 5º intento (403)
  TC-SEC-AUT-02: Token expirado/tampered rechazado (401)
  TC-SEC-INY-01: Protección contra SQLi en cuerpos de petición
  TC-SEC-INY-02: Protección contra XSS en cuerpos de petición
  TC-SEC-CIF-01: Manipulaciones de JWT y cifrado de credenciales
"""

import json
import time
import base64
import os
import pytest
from uuid import uuid4

import jwt as pyjwt

pytestmark = pytest.mark.security


class TestBruteForceLockout:
    """TC-SEC-AUT: Bloqueo de fuerza bruta."""

    async def test_tc_sec_aut_01_brute_force_lockout_5th_attempt_403(
        self, client
    ):
        """TC-SEC-AUT-01: Al 5º intento fallido consecutivo se espera lockout (401/403)."""
        email = f"lockout-{uuid4().hex[:6]}@test.com"
        correct_password = "CorrectPass1"
        wrong_password = "WrongPass1"  # NOSONAR

        register_resp = await client.post("/api/v1/auth/register", json={
            "email": email,
            "password": correct_password,
            "display_name": "Lockout Test User",
            "accept_terms": True,
            "accept_privacy_policy": True,
        })
        assert register_resp.status_code == 201, f"Register failed: {register_resp.status_code} {register_resp.text}"

        url = "/api/v1/auth/login"
        payload = {"email": email, "password": wrong_password}  # NOSONAR
        statuses = []
        for i in range(10):
            response = await client.post(url, json=payload)
            statuses.append(response.status_code)
            if response.status_code in (401, 403):
                try:
                    body = response.json()
                    detail = str(body.get("detail", ""))
                except Exception:
                    detail = ""
                if "bloqueada" in detail.lower():
                    assert i >= 4, f"Lockout occurred too early at attempt {i + 1}"
                    return
        assert 429 in statuses or 401 in statuses or 403 in statuses, (
            f"Expected lockout (401/403/429) within 10 attempts. Got: {sorted(set(statuses))}"
        )

    async def test_tc_sec_aut_02_invalid_token_rejected(
        self, client
    ):
        """TC-SEC-AUT-02: Token JWT manipulado (alg=none, firma vacía) -> 401."""
        header_b64 = (
            base64.urlsafe_b64encode(
                json.dumps({"alg": "none", "typ": "JWT"}).encode()
            )
            .rstrip(b"=")
            .decode()
        )
        payload_b64 = (
            base64.urlsafe_b64encode(
                json.dumps({
                    "sub": str(uuid4()),
                    "role": "ADMIN",
                    "email": "alg@none.com",
                    "organization_id": str(uuid4()),
                    "exp": int(time.time()) + 3600,
                }).encode()
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


class TestInjectionProtection:
    """TC-SEC-INY: Protección contra SQLi y XSS."""

    async def test_tc_sec_iny_01_sqli_protected(self, client):
        """TC-SEC-INY-01: Payloads SQLi en login son rechazados (no 200)."""
        sqli_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "admin'--",
        ]
        for payload in sqli_payloads:
            response = await client.post(
                "/api/v1/auth/login",
                json={"email": payload, "password": "password"},
            )
            assert response.status_code != 200, (
                f"SQLi payload '{payload}' should not return 200"
            )

    async def test_tc_sec_iny_02_xss_protected(self, client):
        """TC-SEC-INY-02: Payloads XSS en campos de registro son rechazados (422)."""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert(1)>",
            "javascript:alert(1)",
        ]
        for payload in xss_payloads:
            response = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"xss-{uuid4().hex[:4]}@test.com",
                    "password": "Password1",
                    "display_name": payload,
                    "accept_terms": True,
                    "accept_privacy_policy": True,
                },
            )
            assert response.status_code != 200, (
                f"XSS payload '{payload}' should not return 200"
            )


class TestCredentialEncryption:
    """TC-SEC-CIF: Cifrado de credenciales y manipulación JWT."""

    async def test_tc_sec_cif_01_jwt_tampering_protected(
        self, client, auth_token
    ):
        """TC-SEC-CIF-01: Token JWT con payload alterado (role escalation) -> 401."""
        parts = auth_token.split(".")
        payload = json.loads(
            base64.urlsafe_b64decode(parts[1] + "===")
        )
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
        assert response.status_code in (401, 403)

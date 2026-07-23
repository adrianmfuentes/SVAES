# Security Tests — Plan de Pruebas

> **TFG terminado** (30/06/2026) — All 5 security tests passing.

Validates protection against common attack vectors: brute force, JWT manipulation, SQL injection, XSS, and credential encryption. Runs against the real app with a test database.

## Structure

```
security/
├── conftest.py                # Real JWTs, malicious payloads, ASGI client, test DB
└── test_security_suite.py     # TC-SEC-AUT, TC-SEC-INY, TC-SEC-CIF (5 tests)
```

## Test Case Catalog

### test_security_suite.py — 5 cases

| ID | Class | Category | Description |
|---|---|---|---|
| TC-SEC-AUT-01 | `TestBruteForceLockout` | Auth | Brute force lockout at 5th failed attempt → 401/403 |
| TC-SEC-AUT-02 | `TestBruteForceLockout` | Auth | Expired/tampered JWT (alg=none) → 401 |
| TC-SEC-INY-01 | `TestInjectionProtection` | Injection | SQLi payloads in login (`' OR '1'='1`, `DROP TABLE`, `admin'--`) rejected |
| TC-SEC-INY-02 | `TestInjectionProtection` | Injection | XSS payloads in registration (`<script>`, `<img onerror>`, `javascript:`) rejected |
| TC-SEC-CIF-01 | `TestCredentialEncryption` | Encryption | JWT role escalation tampering → 401 |

## Attack vectors (malicious_payloads in conftest.py)

| Payload | Attack type |
|---|---|
| `' OR '1'='1` | SQL Injection |
| `<script>alert('xss')</script>` | XSS |
| `'; DROP TABLE users; --` | SQL Injection (destructive) |
| `${7*7}` | SSTI |
| `../etc/passwd` | Path Traversal |
| `__proto__` | Prototype Pollution |
| `constructor` | Constructor access |
| `{{7*7}}` | Template Injection (Jinja2) |

## Fixtures (conftest.py)

| Fixture | Description |
|---|---|
| `_test_db` | Creates/drops tables; returns `True` if DB is available |
| `client` | `httpx.AsyncClient` with ASGI transport (with or without real DB) |
| `auth_token` | Real signed JWT with ADMIN role |
| `basic_user_token` | Real signed JWT with OPERATOR role |
| `auth_headers` | `Authorization: Bearer {auth_token}` |
| `unauth_headers` | `Authorization: Bearer invalid-token` |
| `malicious_payloads` | List of 8 attack strings |

## Run

```bash
# All security tests
pytest tests/security/ -v -m security

# Specific test
pytest tests/security/test_security_suite.py -v
```

## Design notes

- JWTs are real (not mocked) — generated via `JwtHandler` with a test secret key.
- If the DB is unavailable, the `client` still works with a patched connection that raises `ConnectionRefusedError`.
- Malicious payloads are injected in both query params and JSON body fields.

## Total: 5 security test cases

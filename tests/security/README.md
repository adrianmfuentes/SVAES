# Security Tests

Validates protection against common attack vectors: authentication, authorization, injection, and HTTP hardening. Runs against the real app with a test database.

## Structure

```
security/
├── conftest.py          # Real JWTs, malicious payloads, ASGI client, test DB
├── test_auth.py         # Authentication, authorization, rate limiting, security headers, lockout
└── test_injection.py    # SQLi, XSS, SSTI, path traversal, mass assignment, DoS, CORS, audit
```

## Attack vectors (malicious_payloads)

| Payload | Attack type |
|---------|-------------|
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
|---------|-------------|
| `_test_db` | Creates/drops tables; returns `True` if DB is available |
| `client` | `httpx.AsyncClient` with ASGI transport (with or without real DB) |
| `auth_token` | Real signed JWT with U3 (admin) role |
| `basic_user_token` | Real signed JWT with U1 (basic) role |
| `auth_headers` | `Authorization: Bearer {auth_token}` |
| `unauth_headers` | `Authorization: Bearer invalid-token` |
| `malicious_payloads` | List of 8 attack strings |

## Test classes

### test_auth.py
- `TestAuthentication` — JWT validation, expired tokens, algorithm confusion, tampered payloads
- `TestAuthorization` — protected endpoints, role checks, cross-org access
- `TestInputValidation` — required fields, lengths, formats (email, UUID)
- `TestRateLimiting` — `X-RateLimit-*` headers, block after exceeding limit
- `TestSecurityHeaders` — `X-Request-ID`, `X-Content-Type-Options`, CORS
- `TestAccountLockout` — lockout after consecutive failed attempts

### test_injection.py
- `TestSQLInjection` — SQLi payloads in query params and request body
- `TestXSS` — XSS payloads in text fields and HTML responses
- `TestSSTI` — Template injection in input fields
- `TestPathTraversal` — Directory traversal in path parameters
- `TestMassAssignment` — Mass assignment of restricted fields
- `TestNullByteInjection` — Null byte injection in inputs
- `TestHeaderInjection` — HTTP header injection
- `TestDenialOfService` — Large payloads and malformed requests
- `TestContentNegotiation` — Malicious content negotiation
- `TestCORS` — CORS origin and credentials config
- `TestAuditTrail` — Security event logging

## Run

```bash
pytest tests/security/ -v -m security
pytest tests/security/test_auth.py -v
pytest tests/security/test_injection.py -v
```

## Design notes

- JWTs are real (not mocked) — generated via `JwtHandler` with a test secret key.
- If the DB is unavailable, the `client` still works with a patched `asyncpg.connect` that raises `ConnectionRefusedError`.
- Malicious payloads are injected in both query params and JSON body fields.

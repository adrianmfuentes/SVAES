# Integration Tests

Validates interactions between real components using a test PostgreSQL database. The FastAPI app is served via `ASGITransport` — no running HTTP server required.

## Structure

```
integration/
├── conftest.py                   # Test DB, httpx async client, auth headers
├── engine/
│   └── http_pipeline.rs          # 8 HTTP tests against the verification engine
├── test_flow.py                  # STUB — full verification flow
├── test_release_lifecycle.py     # STUB — release lifecycle
├── test_resilience.py            # STUB — fault tolerance
└── test_rate_limit.py            # STUB — rate limiting
```

## Fixtures (conftest.py)

| Fixture | Scope | Description |
|---------|-------|-------------|
| `_test_env` | session | Env vars for `svaes_test` DB |
| `_test_db` | session | Creates/drops all tables per session |
| `client` | function | `httpx.AsyncClient` with ASGI transport |
| `test_user_id` | function | UUID4 user ID |
| `test_org_id` | function | UUID4 org ID |
| `auth_headers` | function | `Authorization: Bearer test-token` |

## Rust tests (engine/http_pipeline.rs)

| ID | Test |
|----|------|
| `tc_int_http_01` | Health endpoint returns 200 |
| `tc_int_http_02` | Valid payload returns verification results |
| `tc_int_http_03` | Invalid payload returns 400 |
| `tc_int_http_04` | Excluded rules are ignored |
| `tc_int_http_05` | Unknown rules return error |
| `tc_int_http_06` | Response structure contains required fields |
| `tc_int_http_07` | Empty artifacts handled without error |
| `tc_int_http_08` | Optional severity does not break processing |

## Run

```bash
# Python (requires PostgreSQL with svaes_test DB)
pytest tests/integration/ -v -m integration

# Rust
cargo test --test http_pipeline
```

## Prerequisites

1. PostgreSQL running with `svaes_test` database: `CREATE DATABASE svaes_test;`
2. Redis running (for JWT blacklist)
3. Tables are created/dropped automatically per test session — no manual setup needed

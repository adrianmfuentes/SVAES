# Integration Tests — Plan de Pruebas

> **TFG terminado** (30/06/2026) — All 27 integration tests passing.

Validates interactions between real components using ephemeral PostgreSQL + Redis containers. The FastAPI app is served via `ASGITransport` — no running HTTP server required.

## Structure

```
integration/
├── conftest.py                   # Test DB, httpx async client, role-based auth tokens (OPERATOR/MANAGER/ADMIN)
├── test_flow_resilience.py       # TC-INT-FLW, TC-INT-LIM, TC-INT-RES, TC-INT-MIG (8 tests)
├── test_release_lifecycle.py     # TC-INT-EST-01…08 (State Transitions)
└── test_api_key_auth.py          # TC-API-AUTH-01…11 (API key authentication)
```

## Test Case Catalog

### test_flow_resilience.py — 8 cases

| ID | Class | Description |
|---|---|---|
| TC-INT-FLW-01 | `TestFullFlow` | Full flow org→profile→project→release→artifact→verify with active connectors |
| TC-INT-FLW-02 | `TestFullFlow` | Full flow without artifacts (simulates inactive connectors) |
| TC-INT-LIM-01 | `TestExactRateLimit` | 100 requests to health endpoint → 200 |
| TC-INT-LIM-02 | `TestExactRateLimit` | 101st request to login → 429 |
| TC-INT-RES-01 | `TestResilience` | Worker crash recovery: 10 concurrent health checks → all 200 |
| TC-INT-RES-02 | `TestResilience` | Redis unavailable: degraded endpoints still respond (not 500) |
| TC-INT-MIG-01 | `TestMigration` | Release profile migration via PATCH → name updated |
| TC-INT-MIG-02 | `TestMigration` | Cross-project release access → 404 |

### test_release_lifecycle.py — 8 cases (State Transitions)

| ID | Class | Description |
|---|---|---|
| TC-INT-EST-01 | `TestReleaseStateTransitions` | BORRADOR → release created in initial state |
| TC-INT-EST-02 | `TestReleaseStateTransitions` | EN_VERIFICACION → state transitions to VALIDA/NO_VALIDA/CON_ADVERTENCIAS |
| TC-INT-EST-03 | `TestReleaseStateTransitions` | EN_VERIFICACION → CON_ADVERTENCIAS (202 accepted) |
| TC-INT-EST-04 | `TestReleaseStateTransitions` | EN_VERIFICACION → NO_VALIDA (verification rejects) |
| TC-INT-EST-05 | `TestReleaseStateTransitions` | Any final state → ARCHIVADA (200 OK) |
| TC-INT-EST-06 | `TestReleaseStateTransitions` | BORRADOR → ARCHIVADA (skip intermediate, 200) |
| TC-INT-EST-07 | `TestReleaseStateTransitions` | ARCHIVADA → modification rejected (409/422) |
| TC-INT-EST-08 | `TestReleaseStateTransitions` | ARCHIVADA → restore by admin (200) |

### test_api_key_auth.py — 11 cases

| ID | Description |
|---|---|
| TC-API-AUTH-01 | Valid key on protected endpoint → success |
| TC-API-AUTH-02 | Missing key header → 401 |
| TC-API-AUTH-03 | Malformed key → 401 |
| TC-API-AUTH-04 | Revoked key → 401 |
| TC-API-AUTH-05 | Expired key → 401 |
| TC-API-AUTH-06 | 6th active key for a user → 429 (max 5) |
| TC-API-AUTH-07 | Full key value only ever returned at creation |
| TC-API-AUTH-08 | DB stores the key hash, never plaintext |
| TC-API-AUTH-09 | Rate limit on key-authenticated requests → 429 |
| TC-API-AUTH-10 | Low-privilege key rejected on a write endpoint |
| TC-API-AUTH-11 | Key scoped to one organization can't access another's data |

Engine-side rule logic is covered by the inline Rust unit tests in `engine/src/` (see [engine/README.md](../../engine/README.md#tests-del-motor)) — there's no separate HTTP-level integration suite for the engine.

## Fixtures (conftest.py)

| Fixture | Scope | Description |
|---|---|---|
| `_test_env` | session | Sets env vars for `svaes_test` DB, JWT secret, encryption key, Redis, engine URL |
| `_test_db` | session | Creates/drops all tables per session |
| `client` | function | `httpx.AsyncClient` with ASGI transport against the FastAPI app |
| `db` | function | Marker to ensure test DB is available |
| `test_user_id` | function | UUID4 user ID |
| `test_org_id` | function | UUID4 org ID |
| `admin_token` / `admin_headers` | function | JWT with ADMIN role |
| `manager_token` / `manager_headers` | function | JWT with MANAGER role |
| `operator_token` / `operator_headers` | function | JWT with OPERATOR role |
| `auth_headers` | function | Alias for `admin_headers` |

## Run

### Recommended: One-command script

```powershell
# Windows (PowerShell 7+)
.\scripts\run_integration_tests.ps1
```

The script automatically:
1. Spins up ephemeral PostgreSQL (port 5433) and Redis (port 6380) via `docker-compose.test.yml`
2. Runs all Python integration tests with `pytest tests/integration/ -v --tb=short`
3. Tears down containers on completion (always, even on failure)

### Manual

```bash
# Start test infrastructure
docker compose -f docker-compose.test.yml up -d --wait

# Python integration tests
pytest tests/integration/ -v -m integration

# Tear down
docker compose -f docker-compose.test.yml down --volumes
```

## Prerequisites

- **Docker Desktop** (or Docker Engine + Docker Compose)
- **Python 3.11+** with project dependencies installed
- The `run_integration_tests.ps1` script handles all infrastructure automatically — no manual DB setup needed

## Total: 27 Python integration test cases

# Integration Tests

Validates interactions between real components using ephemeral PostgreSQL + Redis containers. The FastAPI app is served via `ASGITransport` — no running HTTP server required.

## Structure

```
integration/
├── conftest.py                   # Test DB, httpx async client, role-based auth tokens
├── engine/
│   └── http_pipeline.rs          # 8 HTTP tests against the verification engine (Rust)
├── test_flow.py                  # Full verification flow (17 classes, ~35 tests)
├── test_release_lifecycle.py     # Release lifecycle (6 classes, ~20 tests)
├── test_resilience.py            # Fault tolerance & error handling (8 classes, ~28 tests)
└── test_rate_limit.py            # Rate limiting (4 classes, ~8 tests)
```

## Test Files

### test_flow.py — Full Verification Flow

| Class | Description |
|---|---|
| `TestHealthEndpoint` | Health check returns 200, includes request ID, no auth required |
| `TestDocsAccessibility` | `/docs` accessible in test mode |
| `TestOrganizationFlow` | Create, duplicate slug (409), get, list, admin restrictions |
| `TestProfileFlow` | Create and list verification profiles |
| `TestProjectFlow` | Create, list, list accessible, get by ID, archive |
| `TestReleaseFlow` | Create, list from project, list global, get release |
| `TestArtifactFlow` | Add, list, and remove artifacts |
| `TestVerificationFlow` | Launch verification (202/409/500), get results |
| `TestDashboardFlow` | Dashboard metrics (total_releases, valid_releases, pass_rate) |
| `TestAuthIntegration` | Login with invalid creds, register + login + logout + profile flow |
| `TestUserProfileFlow` | Get current user (with/without auth), update display name |
| `TestConnectorTypes` | List available connector implementations |
| `TestAccessRequests` | Submit and list access requests |
| `TestNotifications` | List notification channels and preferences |
| `TestTemplates` | List and create release templates |
| `TestApiKeys` | Create and list API keys |
| `TestAdminEndpoints` | List users (admin/non-admin), reload rules, audit logs |

### test_release_lifecycle.py — Release Lifecycle

| Class | Description |
|---|---|
| `TestReleaseCreation` | Minimal creation, without auth, invalid project, empty name |
| `TestReleaseUpdate` | Update name/description/version, nonexistent, no auth, viewer denied |
| `TestReleaseArchive` | Archive, archive already archived, viewer denied |
| `TestReleaseRestore` | Admin restore, manager denied |
| `TestReleaseDelete` | Delete, delete nonexistent, viewer denied |
| `TestReleaseStateTransitions` | Full lifecycle (draft → update → archive → delete), status persists after update |

### test_resilience.py — Fault Tolerance & Error Handling

| Class | Description |
|---|---|
| `TestMalformedInput` | Malformed JSON, invalid UUID, empty body, extra fields, wrong types |
| `TestAuthErrorRecovery` | Expired token, malformed token, empty token, missing Bearer, wrong secret |
| `TestMethodNotAllowed` | GET on login, POST on health, PUT on GET endpoint |
| `TestErrorResponses` | No traceback leakage, unauthorized structure, validation detail, 404 detail, 500 safety |
| `TestConcurrentRequests` | Concurrent health checks (10x), concurrent user profiles (5x) |
| `TestNotFoundResources` | Nonexistent org/release/project/profile all return 404 |
| `TestBoundaryValues` | Max length name (100 chars), excessive length (200 chars), negative pagination |
| `TestCrossOrgIsolation` | Cross-org project access denied, cross-org release access denied |

### test_rate_limit.py — Rate Limiting

| Class | Description |
|---|---|
| `TestAuthRateLimiting` | Login limit breached (35 requests), register limit, under threshold (5), refresh limit |
| `TestRateLimitHeaders` | Rate limit headers on protected routes, 429 includes Retry-After |
| `TestDefaultRateLimiting` | Health endpoint not rate limited (50 requests), rapid consecutive requests |
| `TestRateLimitReset` | Per-limiter isolation (login vs register) |

## Rust Tests (engine/http_pipeline.rs)

| ID | Test |
|----|------|
| `tc_int_http_01` | Health endpoint returns `healthy` with service/version |
| `tc_int_http_02` | Valid payload (7 artifacts + 10 rules) returns `Valida` verdict |
| `tc_int_http_03` | Error payload returns `NoValida` with at least one `Error` result |
| `tc_int_http_04` | Rules with `EXCLUIDA` severity are skipped and marked `NoEvaluada` |
| `tc_int_http_05` | Unknown rule ID (`RV-99`) returns `NoEvaluada` with error message |
| `tc_int_http_06` | Response structure validation (verdict, rule_results, summary, status enums) |
| `tc_int_http_07` | Empty artifacts with mandatory rules produces `NoValida` |
| `tc_int_http_08` | Optional severity rules without matching artifacts still yields `Valida` |

## Fixtures (conftest.py)

| Fixture | Scope | Description |
|---------|-------|-------------|
| `_test_env` | session | Sets env vars for `svaes_test` DB, JWT secret, encryption key, Redis, engine URL |
| `_test_db` | session | Creates/drops all tables per session |
| `client` | function | `httpx.AsyncClient` with ASGI transport against the FastAPI app |
| `test_user_id` | function | UUID4 user ID |
| `test_org_id` | function | UUID4 org ID |
| `admin_token` / `admin_headers` | function | JWT with U4 (Admin) role |
| `manager_token` / `manager_headers` | function | JWT with U3 (Manager) role |
| `operator_token` / `operator_headers` | function | JWT with U2 (Operator) role |
| `viewer_token` / `viewer_headers` | function | JWT with U1 (Viewer) role |
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
pytest tests/integration/ -v

# Rust HTTP pipeline tests (from engine/)
cargo test --test http_pipeline

# Tear down
docker compose -f docker-compose.test.yml down --volumes
```

## Prerequisites

- **Docker Desktop** (or Docker Engine + Docker Compose)
- **Python 3.11+** with project dependencies installed (`pip install -r api/requirements.txt`)
- **Rust toolchain** (only for Rust tests: `cargo test --test http_pipeline`)
- The `run_integration_tests.ps1` script handles all infrastructure automatically — no manual DB setup needed

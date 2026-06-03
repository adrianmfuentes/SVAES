# SVAES Testing Guide — Plan de Pruebas

Overview of the test infrastructure, conventions, and execution procedures for the SVAES project. All tests follow the **Plan de Pruebas** structured according to **ISO 29119-4** with unique test case identifiers (TC-*).

---

## Test Suite Structure

```
tests/
├── conftest.py
├── unit/                                   # Unit tests (150+ cases, isolated, mocked)
│   ├── conftest.py                         # Env vars, async engine mock, Python path
│   ├── test_connectors_optimized.py        # TC-UNI-CON-01…06 (CE+VL: Connector credentials, network, timeout)
│   ├── test_releases_endpoint.py           # TC-UNI-API-00…07 (Base Choice: POST /releases endpoint)
│   ├── test_services.py                    # Service layer branch coverage (30+ cases)
│   ├── test_more_services.py               # Auxiliary services, routers (20+ cases)
│   ├── test_routers_extended.py            # Router endpoints with dependency overrides (15+ cases)
│   ├── test_enums_exceptions.py            # Domain enums + exception classes (9 cases)
│   ├── test_bootstrap.py                   # Admin user seeding (4 cases)
│   ├── test_export_service.py              # PDF/CSV export logic (10 cases)
│   ├── test_dependencies_factories.py      # DI container factory functions (22 cases)
│   ├── test_profile_service_wrappers.py    # ProfileService auditing wrappers (10 cases)
│   └── test_coverage_gaps.py               # Remaining structural gaps (32 cases)
├── integration/                            # Integration tests (16 test cases, real DB + Redis)
│   ├── conftest.py                         # Test DB, httpx ASGI client, role-based auth tokens
│   ├── test_flow_resilience.py             # TC-INT-FLW, TC-INT-LIM, TC-INT-RES, TC-INT-MIG (8 tests)
│   └── test_release_lifecycle.py           # TC-INT-EST-01…08 (State Transitions: release lifecycle)
├── security/                               # Security tests (5 test cases)
│   ├── conftest.py                         # Real JWTs, malicious payloads, ASGI client
│   └── test_security_suite.py              # TC-SEC-AUT, TC-SEC-INY, TC-SEC-CIF
├── performance/                            # Performance tests (4 test cases + 3 Rust benchmarks)
│   ├── conftest.py                         # API base URL, auth token
│   └── locustfile.py                       # TC-PER-VL, TC-PER-CE (Locust load tests)
└── acceptance/                             # E2E acceptance tests (10 test cases)
    ├── cypress.config.js                   # Cypress configuration
    └── cypress/e2e/
        └── acceptance_suite.cy.js          # TC-ACP-CU, TC-ACP-UI, TC-ACP-FRM, TC-USA
```

### Engine Tests (Rust)

Engine unit tests are inline within each source file under `#[cfg(test)]`:

```
engine/src/
├── aggregator.rs       # 7 verdict aggregation tests
├── rules/rv01.rs       # Artifact existence tests
├── rules/rv02.rs       # Traceability tests
├── rules/rv03.rs       # State validation tests
├── rules/rv04.rs       # Numeric field integrity tests
├── rules/rv05.rs       # Document accessibility tests
├── rules/rv06.rs       # Attribute coherence tests
├── rules/rv07.rs       # External registration tests
├── rules/rv08.rs       # List alignment tests
├── rules/rv09.rs       # Reference validation tests
└── rules/rv10.rs       # Final approval tests
```

---

## Test Case Catalog (Plan de Pruebas)

All test cases are identified following **ISO 29119-4** with the format `TC-{NIVEL}-{CATEGORIA}-{NUM}`.

### Unit Tests (150+ cases)

#### Catalogued cases (14 cases)

| ID | File | Technique | Description |
|---|---|---|---|
| TC-UNI-CON-01 | `test_connectors_optimized.py` | CE+VL | Valid credentials → connection success (GitLab) |
| TC-UNI-CON-02 | `test_connectors_optimized.py` | CE+VL | Invalid credentials → connection failure (Jira) |
| TC-UNI-CON-03 | `test_connectors_optimized.py` | CE+VL | Network accessible → 200 OK (GitLab) |
| TC-UNI-CON-04 | `test_connectors_optimized.py` | CE+VL | Network unreachable → ConnectError (Jira) |
| TC-UNI-CON-05 | `test_connectors_optimized.py` | CE+VL | Timeout boundary OK (within threshold) |
| TC-UNI-CON-06 | `test_connectors_optimized.py` | CE+VL | Timeout exceeded → TimeoutException (Jira) |
| TC-UNI-API-00 | `test_releases_endpoint.py` | Base Choice | Base case: operator + valid token → 201 |
| TC-UNI-API-01 | `test_releases_endpoint.py` | Base Choice | Variation: admin bypasses checks → 201 |
| TC-UNI-API-02 | `test_releases_endpoint.py` | Base Choice | Variation: viewer cross-org → 403 |
| TC-UNI-API-03 | `test_releases_endpoint.py` | Base Choice | Variation: no token → 401 |
| TC-UNI-API-04 | `test_releases_endpoint.py` | Base Choice | Variation: missing name → 422 |
| TC-UNI-API-05 | `test_releases_endpoint.py` | Base Choice | Variation: nonexistent project → 404 |
| TC-UNI-API-06 | `test_releases_endpoint.py` | Base Choice | Variation: invalid SemVer → 422 |
| TC-UNI-API-07 | `test_releases_endpoint.py` | Base Choice | Variation: cross-org access → 403 |

#### Branch-coverage service & structural tests (135+ cases across 10 files)

| File | Approx. Cases | Focus |
|---|---|---|
| `test_services.py` | 30+ | Branch coverage: AuthService, UserService, ReleaseService, OrganizationService, NotificationService, ManageApiKeys, ConnectorService, TemplateService, DashboardMetrics, RulesService, ManageProfile, AuditLogger, EmailService, Logger |
| `test_more_services.py` | 20+ | CustomRoleService, VerificationService, ArtifactService, ConnectorRegistry, BaseHttpConnector, ConnectorImplementations, AuthRouter, ReleasesRouter, JwtHandler, PasswordHasher |
| `test_routers_extended.py` | 15+ | FastAPI routers (Organizations, Users, Dashboard, ApiKeys, Notifications, Connectors, Templates, Profiles, Audit, CustomRoles, Health) with dependency overrides |
| `test_enums_exceptions.py` | 9 | Domain enums (severity_to_rule_severity branches, rule_severity_to_string), domain exceptions (ReleaseInvalidStateError, EntityNotFoundError, DuplicateEntityError) |
| `test_bootstrap.py` | 4 | `seed_admin_user`: existing admin (no org_id / with org_id), email taken, successful seed |
| `test_export_service.py` | 10 | ExportService: PDF generation (with/without release, with/without summary, with/without rule_results, verdict fallback), CSV export (empty, populated, no project, no releases, executed_at=None) |
| `test_dependencies_factories.py` | 22 | DI container: repository factories (9), service factories (13) |
| `test_profile_service_wrappers.py` | 10 | ProfileService: create_profile (with/without default), update_profile, duplicate_profile, delete_profile (found/not found), add_rule, update_rule, delete_rule |
| `test_coverage_gaps.py` | 32 | Structural gaps: rate_limit, password_hasher.needs_rehash, manage_profile remaining branches, organization_service simple methods, task_service, template_service, release_service remaining, user_service remaining, connector_service remaining (list/get/delete/test_connection), verification_service, manage_api_keys, audit logger |

### Integration Tests (16 cases)

| ID | File | Technique | Description |
|---|---|---|---|
| TC-INT-FLW-01 | `test_flow_resilience.py` | Flow | Full flow with active connectors |
| TC-INT-FLW-02 | `test_flow_resilience.py` | Flow | Full flow with inactive connectors |
| TC-INT-LIM-01 | `test_flow_resilience.py` | Limit | 100 requests → HTTP 200 |
| TC-INT-LIM-02 | `test_flow_resilience.py` | Limit | 101st request → HTTP 429 |
| TC-INT-RES-01 | `test_flow_resilience.py` | Resilience | Worker crash recovery (health still OK) |
| TC-INT-RES-02 | `test_flow_resilience.py` | Resilience | Redis unavailable → degraded but responding |
| TC-INT-MIG-01 | `test_flow_resilience.py` | Migration | Release profile migration (patch + verify) |
| TC-INT-MIG-02 | `test_flow_resilience.py` | Migration | Release cross-project transfer (404 expected) |
| TC-INT-EST-01 | `test_release_lifecycle.py` | State Transition | BORRADOR → initial state verified |
| TC-INT-EST-02 | `test_release_lifecycle.py` | State Transition | EN_VERIFICACION → VALIDA |
| TC-INT-EST-03 | `test_release_lifecycle.py` | State Transition | EN_VERIFICACION → CON_ADVERTENCIAS |
| TC-INT-EST-04 | `test_release_lifecycle.py` | State Transition | EN_VERIFICACION → NO_VALIDA |
| TC-INT-EST-05 | `test_release_lifecycle.py` | State Transition | Any final state → ARCHIVADA |
| TC-INT-EST-06 | `test_release_lifecycle.py` | State Transition | BORRADOR → ARCHIVADA (skip validation) |
| TC-INT-EST-07 | `test_release_lifecycle.py` | State Transition | ARCHIVADA → modification rejected (409/422) |
| TC-INT-EST-08 | `test_release_lifecycle.py` | State Transition | ARCHIVADA → restore (admin) |

### Security Tests (5 cases)

| ID | File | Category | Description |
|---|---|---|---|
| TC-SEC-AUT-01 | `test_security_suite.py` | Auth | Brute force lockout at 5th attempt (403) |
| TC-SEC-AUT-02 | `test_security_suite.py` | Auth | Expired/tampered JWT rejected (401) |
| TC-SEC-INY-01 | `test_security_suite.py` | Injection | SQLi payloads in login rejected |
| TC-SEC-INY-02 | `test_security_suite.py` | Injection | XSS payloads in registration rejected |
| TC-SEC-CIF-01 | `test_security_suite.py` | Encryption | JWT role tampering → 401 |

### Performance Tests (4 cases + 3 Rust benchmarks)

| ID | File | Description |
|---|---|---|
| TC-PER-VL-01 | `locustfile.py` | E2E p95 ≤ 5s (end-to-end flow) |
| TC-PER-VL-02 | `locustfile.py` | Rust engine < 500ms (p95) |
| TC-PER-CE-01 | `locustfile.py` | 50 concurrent requests without timeout |
| TC-PER-CE-02 | `locustfile.py` | Sustained load on releases list |
| tc_per_pf_01 | `engine/tests/performance.rs` | Single request 10 rules < 500ms |
| tc_per_pf_02 | `engine/tests/performance.rs` | 100 iterations, avg < 500ms |
| tc_per_pf_03 | `engine/tests/performance.rs` | Large payload (102 artifacts), no errors |

### Acceptance Tests (10 cases)

| ID | File | Category | Description |
|---|---|---|---|
| TC-ACP-CU-01 | `acceptance_suite.cy.js` | Visual | Traffic light green for VALIDA release |
| TC-ACP-CU-02 | `acceptance_suite.cy.js` | Visual | Traffic light red for NO_VALIDA release |
| TC-ACP-UI-01 | `acceptance_suite.cy.js` | Multi-Res | Layout at 1920x1080 (Full HD) |
| TC-ACP-UI-02 | `acceptance_suite.cy.js` | Multi-Res | Layout at 1366x768 (HD Ready) |
| TC-ACP-UI-03 | `acceptance_suite.cy.js` | Multi-Res | Layout at 375x667 (iPhone SE) |
| TC-ACP-FRM-01 | `acceptance_suite.cy.js` | Forms | Name required validation |
| TC-ACP-FRM-02 | `acceptance_suite.cy.js` | Forms | SemVer version validation |
| TC-USA-01 | `acceptance_suite.cy.js` | Usability | No console errors on load |
| TC-USA-02 | `acceptance_suite.cy.js` | Usability | Error messages visible with contrast |
| TC-USA-03 | `acceptance_suite.cy.js` | Usability | Full navigation without layout break |

### Engine HTTP Integration Tests (8 cases)

| ID | Description |
|---|---|
| tc_int_http_01 | Health endpoint returns `healthy` with service/version |
| tc_int_http_02 | Valid payload (7 artifacts + 10 rules) → `Valida` |
| tc_int_http_03 | Error payload → `NoValida` with at least one `Error` |
| tc_int_http_04 | Rules with `EXCLUIDA` severity → skipped, marked `NoEvaluada` |
| tc_int_http_05 | Unknown rule ID (`RV-99`) → `NoEvaluada` with error message |
| tc_int_http_06 | Response structure validation (verdict, rule_results, summary, enums) |
| tc_int_http_07 | Empty artifacts with mandatory rules → `NoValida` |
| tc_int_http_08 | Optional rules without matching artifacts → `Valida` |

---

## Running Tests

### Python Unit Tests

```bash
# All unit tests
pytest tests/unit/ -v -m unit

# Specific module
pytest tests/unit/test_releases_endpoint.py -v

# With coverage
pytest tests/unit/ --cov=api/src --cov-report=term --cov-report=xml
```

### Python Integration Tests

```powershell
# Recommended: one-command script (Windows PowerShell 7+)
.\scripts\run_integration_tests.ps1
```

The script automatically:
1. Spins up ephemeral PostgreSQL (port 5433) and Redis (port 6380) via `docker-compose.test.yml`
2. Runs all Python integration tests with `pytest tests/integration/ -v --tb=short`
3. Tears down containers on completion (always, even on failure)

Manual alternative:

```bash
# Start test infrastructure
docker compose -f docker-compose.test.yml up -d --wait

# Run tests
pytest tests/integration/ -v -m integration

# Tear down
docker compose -f docker-compose.test.yml down --volumes
```

### Security Tests

```bash
pytest tests/security/ -v -m security
```

### Performance Tests

```bash
# Locust (API server must be running)
locust -f tests/performance/locustfile.py --host=http://localhost:8000

# Rust benchmarks (from engine/)
cargo test --test performance --release
```

### Acceptance Tests (E2E)

```bash
# Headless
npx cypress run --config-file tests/acceptance/cypress.config.js

# Interactive
npx cypress open --config-file tests/acceptance/cypress.config.js
```

### Rust Tests

```bash
cd engine

# All unit tests
cargo test

# HTTP integration tests
cargo test --test http_pipeline

# Performance benchmarks
cargo test --test performance

# With log output
cargo test -- --nocapture
```

### All Tests (Full Suite)

```bash
# Python
cd api && pytest

# Rust
cd engine && cargo test
```

---

## Conventions

### Python (pytest)

- **Markers:** `unit`, `integration`, `security`, `performance` — declared in `pytest.ini`
- **File naming:** `test_<module_name>.py`
- **Class naming:** `class Test<UnitName>`
- **Method naming:** `test_tc_<level>_<cat>_<num>_<description>` following ISO 29119-4 test case IDs
- **Fixtures:** Defined in `conftest.py`, shared across test modules
- **Mocking:** Domain entities and application commands are **never** mocked. Only infrastructure adapters (repositories, connectors, queue) are mocked.
- **Async tests:** `pytest-asyncio` with `asyncio_mode = auto` in `pytest.ini`

### Rust

- Unit tests inline in each source file: `#[cfg(test)] mod tests { ... }`
- Integration tests in `engine/tests/`
- No external test runners — all via `cargo test`

---

## Coverage Targets

| Layer | Target | Current |
|---|---|---|
| `api/src/` (total) | >= 70% | **70%** |
| `api/src/domain/` | >= 80% | ~96% |
| `api/src/application/` | >= 80% | ~90% |
| `api/src/infrastructure/` | Best effort | ~47% |
| `engine/src/` | >= 80% | Inline tested |

Coverage reports are generated in `coverage.xml` (Python) and consumed by SonarCloud via the CI pipeline.

### Coverage exclusions

Files excluded from coverage (entry points, config, auto-generated, pure re-exports):

```
api/src/main.py                                    # ASGI entry point
api/src/infrastructure/secondary/queue/celery_app.py  # Celery worker entry point
api/src/core/config.py                             # Pydantic Settings
api/src/infrastructure/config/*                     # Infrastructure config
api/src/infrastructure/settings*                    # Settings files
*/alembic/versions/*                                # Migration versions
*/alembic/env.py                                    # Alembic bootstrap
*/migrations/*                                      # Django-style migrations
api/src/svaes_api.egg-info/*                        # Auto-generated metadata
api/src/**/__init__.py (pure re-exports)            # 10 __init__.py files
```

For the Rust engine: `cargo llvm-cov --ignore-filename-regex "main\.rs$"` (script: `scripts/run_rust_coverage.ps1`).

---

## CI Integration

Tests run automatically via GitHub Actions:

| Workflow | Trigger | What Runs |
|---|---|---|
| `sonar.yml` | push/PR on main | pytest with coverage -> SonarCloud Quality Gate |
| `codeql.yml` | push/PR on main, cron weekly | CodeQL security analysis (Python) |

---

## Adding New Tests

1. Create `test_<name>.py` (Python) or add `#[cfg(test)]` module (Rust).
2. Assign an ISO 29119-4 test case ID: `TC-{NIVEL}-{CATEGORIA}-{NUM}`.
3. Follow the naming conventions above.
4. Use existing fixtures from `conftest.py` or create new ones.
5. Mock external dependencies (DB, connectors, queue) — never mock domain entities.
6. Add the test case to the catalog table in this document.
7. Run `pytest` or `cargo test` locally before committing.

---

*Last updated: June 2026 — Adrian Martinez Fuentes*

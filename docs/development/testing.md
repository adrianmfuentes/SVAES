# SVAES Testing Guide

Overview of the test infrastructure, conventions, and execution procedures for the SVAES project.

---

## Test Suite Structure

```
tests/
├── conftest.py                     # Python path, DATABASE_URL dummy
├── unit/                           # Unit tests (59 files, isolated, mocked)
│   ├── core/                       # Credential encryptor, pseudonymizer
│   │   ├── test_credential_encryptor.py
│   │   └── test_pseudonymizer.py
│   ├── connectors/                 # 8 connector implementations (GitLab, Jira, Trello, etc.)
│   │   ├── conftest.py
│   │   ├── test_gitlab.py
│   │   ├── test_jira.py
│   │   ├── test_trello.py
│   │   ├── test_plane.py
│   │   ├── test_linear.py
│   │   ├── test_jira_sm.py
│   │   ├── test_redmine.py
│   │   ├── test_gitea.py
│   │   └── test_wikijs.py
│   ├── api/                        # Use cases, services, routers, workers (34 files)
│   │   ├── conftest.py             # 14 mock repos, task queue, connector registry
│   │   ├── test_authenticate_user.py
│   │   ├── test_auth_service.py
│   │   ├── test_releases.py
│   │   ├── test_releases_router.py
│   │   ├── test_user_service.py
│   │   ├── test_users_router.py
│   │   ├── test_organization_service.py
│   │   ├── test_organizations_router.py
│   │   ├── test_connector_service.py
│   │   ├── test_profile_service.py
│   │   ├── test_verification_service.py
│   │   ├── test_verification_worker.py
│   │   ├── ...                     # (+21 more files)
│   └── repositories/               # 15 SQL repository tests (in-memory SQLite)
│       ├── conftest.py
│       ├── test_base_sql_repository.py
│       ├── test_user_repository.py
│       ├── test_release_repository.py
│       ├── test_project_repository.py
│       ├── test_organization_repository.py
│       ├── test_connector_repository.py
│       ├── test_profile_repository.py
│       ├── test_rule_repository.py
│       ├── test_artifact_repository.py
│       ├── test_verification_result_repository.py
│       ├── test_template_repository.py
│       ├── test_api_key_repository.py
│       ├── test_notification_repository.py
│       ├── test_custom_role_repository.py
│       └── test_verification_engine_interface.py
├── integration/                    # Integration tests (real DB + Redis)
│   ├── conftest.py                 # Test DB, httpx client, role-based auth tokens
│   ├── engine/
│   │   └── http_pipeline.rs        # 8 HTTP tests against the Rust engine
│   ├── test_flow.py                # Full verification flow (17 classes, ~35 tests)
│   ├── test_release_lifecycle.py   # Release lifecycle (6 classes, ~20 tests)
│   ├── test_resilience.py          # Fault tolerance & error handling (8 classes, ~28 tests)
│   └── test_rate_limit.py          # Rate limiting (4 classes, ~8 tests)
├── performance/                    # Performance benchmarks
├── security/                       # Security vulnerability tests
│   ├── test_auth.py
│   └── test_injection.py
└── acceptance/                     # E2E / acceptance tests
```

### Engine Tests (Rust)

Engine unit tests are inline within each source file under `#[cfg(test)]`:

```
engine/src/
├── aggregator.rs       # 7 verdict aggregation tests
├── rules/rv01.rs       # 3 artifact existence tests
├── rules/rv02.rs       # Traceability tests
├── rules/rv03.rs       # State validation tests
├── ...
└── rules/rv10.rs       # Approval tests
```

---

## Running Tests

### Python Unit Tests

```bash
# All unit tests
pytest tests/unit/

# Specific module
pytest tests/unit/api/test_releases.py

# With coverage
pytest tests/unit/ --cov=api/src --cov-report=term --cov-report=xml

# Verbose output
pytest tests/unit/ -v
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
pytest tests/integration/ -v

# Tear down
docker compose -f docker-compose.test.yml down --volumes
```

### Security Tests

```bash
pytest tests/security/
```

### Performance Tests

```bash
pytest tests/performance/
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

- **File naming:** `test_<module_name>.py`
- **Class naming:** `class Test<UnitName>`
- **Method naming:** `test_<condition>_<expected_result>`
- **Fixtures:** Defined in `conftest.py`, shared across test modules
- **Mocking:** Domain entities and application commands are **never** mocked. Only infrastructure adapters (repositories, connectors, queue) are mocked.
- **Async tests:** `pytest-asyncio` with `asyncio_mode = auto` in `pytest.ini`

### Rust

- Unit tests inline in each source file: `#[cfg(test)] mod tests { ... }`
- Integration tests in `engine/tests/`
- No external test runners — all via `cargo test`

---

## Coverage Targets

| Layer | Target |
|---|---|
| `api/src/domain/` | >= 80% |
| `api/src/application/` | >= 80% |
| `api/src/infrastructure/` | Best effort |
| `engine/src/` | >= 80% |

Coverage reports are generated in `coverage.xml` (Python) and consumed by SonarCloud via the CI pipeline.

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
2. Follow the naming conventions above.
3. Use existing fixtures from `conftest.py` or create new ones.
4. Mock external dependencies (DB, connectors, queue) — never mock domain entities.
5. Run `pytest` or `cargo test` locally before committing.

---

*Last updated: June 2026 — Adrian Martinez Fuentes*

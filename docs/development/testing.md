# SVAES Testing Guide

Overview of the test infrastructure, conventions, and execution procedures for the SVAES project.

---

## Test Suite Structure

```
tests/
├── conftest.py                     # Python path, DATABASE_URL dummy
├── unit/                           # Unit tests (API + engine)
│   ├── core/                       # Config, DI, audit
│   ├── connectors/                 # Connector implementations
│   ├── api/                        # HTTP router tests
│   │   └── test_routers.py
│   ├── application/use_cases/      # Use case tests
│   │   ├── test_auth_use_cases.py
│   │   ├── test_configure_connector.py
│   │   ├── test_create_release.py
│   │   ├── test_get_verification_history.py
│   │   ├── test_launch_verification.py
│   │   ├── test_manage_profile.py
│   │   ├── test_organization_use_cases.py
│   │   └── test_project_use_cases.py
│   ├── domain/                     # Entity and enum tests
│   │   ├── test_entities.py
│   │   └── test_ports.py
│   └── infrastructure/             # Adapter tests (mocked)
│       ├── test_repositories.py
│       └── test_security.py
├── integration/                    # Integration tests
│   ├── conftest.py
│   ├── test_testclient.py
│   └── test_complete.py
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
pytest tests/unit/application/use_cases/test_create_release.py

# With coverage
pytest tests/unit/ --cov=api/src --cov-report=term --cov-report=xml

# Verbose output
pytest tests/unit/ -v
```

### Python Integration Tests

```bash
# Requires a running database
docker compose up postgres -d
pytest tests/integration/
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
| `api/src/domain/` | ≥ 80% |
| `api/src/application/` | ≥ 80% |
| `api/src/infrastructure/` | Best effort |
| `engine/src/` | ≥ 80% |

Coverage reports are generated in `coverage.xml` (Python) and consumed by SonarCloud via the CI pipeline.

---

## CI Integration

Tests run automatically via GitHub Actions:

| Workflow | Trigger | What Runs |
|---|---|---|
| `sonar.yml` | push/PR on main | pytest with coverage → SonarCloud Quality Gate |
| `codeql.yml` | push/PR on main, cron weekly | CodeQL security analysis (Python) |

---

## Adding New Tests

1. Create `test_<name>.py` (Python) or add `#[cfg(test)]` module (Rust).
2. Follow the naming conventions above.
3. Use existing fixtures from `conftest.py` or create new ones.
4. Mock external dependencies (DB, connectors, queue) — never mock domain entities.
5. Run `pytest` or `cargo test` locally before committing.

---

*Last updated: May 2026 — Adrian Martinez Fuentes*

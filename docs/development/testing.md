# SVAES Testing Guide — Plan de Pruebas

> **TFG terminado** (30/06/2026) — All test suites passing as of final delivery.

Overview of the test infrastructure, conventions, and execution procedures for the SVAES project. All tests follow the **Plan de Pruebas** structured according to **ISO 29119-4** with unique test case identifiers (`TC-*`) where a case traces to a formal requirement.

The full, maintained test-case catalog for each suite lives next to its tests — this page covers conventions and execution, not a duplicate catalog:

| Suite | Cases | Catalog |
|---|---|---|
| Unit | 1,238 | [tests/unit/README.md](../../tests/unit/README.md) |
| Integration | 27 | [tests/integration/README.md](../../tests/integration/README.md) |
| Security | 5 | [tests/security/README.md](../../tests/security/README.md) |
| Performance | 47 pytest + 4 Locust classes | [tests/performance/README.md](../../tests/performance/README.md) |
| Acceptance | 12 pytest + 43 Cypress | [tests/acceptance/README.md](../../tests/acceptance/README.md) |
| Engine (Rust) | 86 | inline `#[cfg(test)]` in `engine/src/rules/business_rules.rs`, `rules/custom_field_check.rs`, `aggregator.rs` |

---

## Running everything

```bash
# Python — all suites with coverage
pytest tests/unit/ tests/integration/ tests/security/ tests/performance/ --cov=api/src --cov-report=term --cov-report=xml

# Rust
cd engine && cargo test

# Acceptance (Cypress, frontend + API must be running)
npx cypress run --config-file tests/acceptance/cypress.config.js
```

Integration tests need ephemeral PostgreSQL + Redis — use the one-command script rather than running `pytest tests/integration/` directly:

```powershell
.\scripts\run_integration_tests.ps1
```

## Conventions

### Python (pytest)

- **Markers:** `unit`, `integration`, `security`, `performance` — declared in `pytest.ini`
- **File naming:** `test_<module_name>.py`
- **Class naming:** `class Test<UnitName>`
- Where a test traces to a formal case: `test_tc_<level>_<cat>_<num>_<description>` (ISO 29119-4 ID)
- **Fixtures:** Defined in `conftest.py`, shared across test modules
- **Mocking:** Domain entities and application commands are **never** mocked. Only infrastructure adapters (repositories, connectors, queue) are mocked.
- **Async tests:** `pytest-asyncio` with `asyncio_mode = auto` in `pytest.ini`

### Rust

- Unit tests inline in each source file: `#[cfg(test)] mod tests { ... }`
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
*/alembic/versions/*                                # Migration versions
*/alembic/env.py                                    # Alembic bootstrap
api/src/**/__init__.py (pure re-exports)
```

For the Rust engine: `cargo llvm-cov --ignore-filename-regex "main\.rs$"` (script: `scripts/run_rust_coverage.ps1`).

---

## CI Integration

| Workflow | Trigger | What Runs |
|---|---|---|
| `sonar.yml` | push/PR on main | pytest with coverage → SonarCloud Quality Gate |
| `codeql.yml` | push/PR on main, cron weekly | CodeQL security analysis (Python) |

---

## Adding New Tests

1. Create `test_<name>.py` (Python) or add `#[cfg(test)]` module (Rust).
2. If it traces to a formal requirement, assign an ISO 29119-4 case ID: `TC-{NIVEL}-{CATEGORIA}-{NUM}`.
3. Use existing fixtures from `conftest.py` or create new ones.
4. Mock external dependencies (DB, connectors, queue) — never mock domain entities.
5. Update the relevant suite's `README.md` if you added a new file or a formally-traced case.
6. Run `pytest` or `cargo test` locally before committing.

---

*Last updated: 30 June 2026 — Adrián Martínez Fuentes*

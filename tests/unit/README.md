# Unit Tests — Plan de Pruebas

> **TFG terminado** (30/06/2026) — 1,238 unit tests across 12 files, all passing.

Isolated component tests. All dependencies (repos, HTTP, task queue) are mocked via `unittest.mock.AsyncMock`. No database or external services needed.

Coverage target: **>= 70%** of `api/src/` (total). Domain and application layers target **>= 80%** individually.

## Structure

| File | Tests | Covers |
|---|---|---|
| `test_connectors.py` | 235 | All 20 connector implementations (credentials, network, timeouts) — CE+VL technique, IDs `TC-UNI-CON-*` |
| `test_routers.py` | 248 | FastAPI endpoints across all routers, incl. `TC-UNI-API-*` (Base Choice on `POST /releases`) |
| `test_services.py` | 280 | Application service layer: `AuthService`, `UserService`, `ReleaseService`, `OrganizationService`, `NotificationService`, `ManageApiKeys`, `ConnectorService`, ... |
| `test_repositories.py` | 196 | SQLAlchemy repository implementations (release, user, notification, access request, template, connector, ...) |
| `test_use_cases_core.py` | 78 | Core use cases: authentication, org creation, launch/get verification, update release, toggle connector, ... |
| `test_core.py` | 109 | Admin bootstrap, DI factories, access guards, rate limiting |
| `test_dependencies_factories.py` | 40 | DI container: repository and service factory functions |
| `test_middleware.py` | 12 | Rate limiting, JWT handler, password hasher |
| `test_email.py` | 12 | Feedback, activation, verification-result, and password-reset emails |
| `test_export_service.py` | 11 | PDF/CSV export logic |
| `test_domain.py` | 9 | Domain enums (severity conversion) and exceptions |
| `test_celery_task_queue.py` | 8 | Celery task queue adapter |

`conftest.py` sets env vars (SQLite in-memory, test secrets), a mock async engine, and the Python path.

Rust inline unit tests live under `engine/src/` (RV-01–RV-10 + custom rule + aggregator) with `#[cfg(test)]` — see [engine/README.md](../../engine/README.md#tests-del-motor).

## Naming convention

Where a test traces to a formal Plan de Pruebas case, the method is named `test_tc_<level>_<category>_<num>_<description>` (ISO 29119-4), e.g. `test_tc_uni_con_01_valid_credentials_gitlab_returns_true` in `test_connectors.py`. Most of the suite is ordinary branch-coverage testing without a formal case ID.

## Run

```bash
# All unit tests
pytest tests/unit/ -v -m unit

# Specific module
pytest tests/unit/test_routers.py -v

# With coverage
pytest tests/unit/ --cov=api/src --cov-report=term --cov-report=xml

# Full suite with coverage
pytest tests/unit/ tests/integration/ tests/security/ --cov=api/src --cov-report=term

# Rust inline tests
cargo test --lib
```

See [tests/README.md](../README.md) for coverage exclusions and project-wide configuration.

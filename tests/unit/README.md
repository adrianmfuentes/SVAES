# Unit Tests — Plan de Pruebas

Isolated component tests. All dependencies (repos, HTTP, task queue) are mocked via `unittest.mock.AsyncMock`. No database or external services needed.

Coverage target: **>= 70%** of `api/src/` (total). Domain and application layers target **>= 80%** individually.

## Structure

```
unit/
├── conftest.py                        # Env vars (SQLite in-memory, test secrets), mock async engine, Python path
├── test_connectors_optimized.py       # TC-UNI-CON-01…06: Connector credentials, network, timeout (CE+VL)
├── test_releases_endpoint.py          # TC-UNI-API-00…07: POST /releases endpoint (Base Choice)
├── test_services.py                   # Auth, User, Release, Org, Notification, Connector, Template, Rules, Profile, Dashboard, Audit, Email, Logger services
├── test_more_services.py              # CustomRole, Verification, Artifact, ConnectorRegistry, BaseHttpConnector, ConnectorImplementations, AuthRouter, ReleasesRouter, JwtHandler, PasswordHasher
├── test_routers_extended.py           # Organizations, Users, Dashboard, ApiKeys, Notifications, Connectors, Templates, Profiles, Audit, CustomRoles, Health routers
├── test_enums_exceptions.py           # Domain enums (severity conversion, rule_severity_to_string) and exceptions (ReleaseInvalidStateError, EntityNotFoundError, DuplicateEntityError)
├── test_bootstrap.py                  # seed_admin_user: existing admin (with/without org_id), email taken, successful seed
├── test_export_service.py             # ExportService: PDF generation, CSV export, helper functions (_write_bytes, _write_csv)
├── test_dependencies_factories.py     # DI container: repository factories (9), service factories (13)
├── test_profile_service_wrappers.py   # ProfileService wrapper methods: create/update/duplicate/delete profile, add/update/delete rule
├── test_coverage_gaps.py              # Remaining gaps: rate_limit, password_hasher.needs_rehash, manage_profile branches, organization_service, task_service, template_service, release_service, user_service, connector_service, verification_service, manage_api_keys, audit logger
```

Rust inline unit tests live under `engine/src/` (rules RV-01 to RV-10 + aggregator) with `#[cfg(test)]`.

## Test Case Catalog

### File summary (150+ unit test cases across 12 files)

| File | Approx. Cases | Focus |
|---|---|---|
| `test_connectors_optimized.py` | 6 | Connector credentials, network, timeout (CE+VL) |
| `test_releases_endpoint.py` | 8 | POST /releases endpoint (Base Choice) |
| `test_services.py` | 30+ | Service layer business logic (branch coverage) |
| `test_more_services.py` | 20+ | Auxiliary services, connector registry, HTTP connector, routers |
| `test_routers_extended.py` | 15+ | FastAPI router endpoints (dependency overrides) |
| `test_enums_exceptions.py` | 9 | Domain enums (severity conversion, rule_severity_to_string) + exception classes |
| `test_bootstrap.py` | 4 | Admin user seeding (all branches) |
| `test_export_service.py` | 10 | PDF generation, CSV export, helper functions |
| `test_dependencies_factories.py` | 22 | DI container factory functions |
| `test_profile_service_wrappers.py` | 10 | ProfileService auditing wrappers |
| `test_coverage_gaps.py` | 32 | Structural gaps: rate_limit, password_hasher, manage_profile, org_service, connector_service, release_service, user_service, templates, tasks, verification, api_keys, audit |

### test_connectors_optimized.py — 6 cases (CE+VL)

| ID | Class | Description |
|---|---|---|
| TC-UNI-CON-01 | `TestConnectorCredentials` | Valid credentials (GitLab) -> `test_connection` returns `True` |
| TC-UNI-CON-02 | `TestConnectorCredentials` | Invalid credentials (Jira, 401) -> `test_connection` returns `False` |
| TC-UNI-CON-03 | `TestConnectorNetwork` | Network accessible (GitLab) -> health returns 200 |
| TC-UNI-CON-04 | `TestConnectorNetwork` | Network unreachable (Jira) -> `httpx.ConnectError` |
| TC-UNI-CON-05 | `TestConnectorTimeoutBoundary` | Timeout at boundary (30s) -> response within threshold -> OK |
| TC-UNI-CON-06 | `TestConnectorTimeoutBoundary` | Timeout exceeded -> `httpx.TimeoutException` |

### test_releases_endpoint.py — 8 cases (Base Choice)

| ID | Class | Description |
|---|---|---|
| TC-UNI-API-00 | `TestCreateReleaseEndpoint` | **Base case:** operator + valid token -> 201 |
| TC-UNI-API-01 | `TestCreateReleaseEndpoint` | Admin role bypasses project checks -> 201 |
| TC-UNI-API-02 | `TestCreateReleaseEndpoint` | Viewer cross-org -> 403/404 |
| TC-UNI-API-03 | `TestCreateReleaseEndpoint` | No token -> 401 |
| TC-UNI-API-04 | `TestCreateReleaseEndpoint` | Missing name field -> 422 |
| TC-UNI-API-05 | `TestCreateReleaseEndpoint` | Nonexistent project -> 404 |
| TC-UNI-API-06 | `TestCreateReleaseEndpoint` | Invalid SemVer version -> 422/500 |
| TC-UNI-API-07 | `TestCreateReleaseEndpoint` | Cross-org access -> 403/404 |

## Fixtures (conftest.py)

| Fixture | Scope | Description |
|---|---|---|
| `gitlab_connector` | function | `GitLabConnector` instance for connector tests |
| `jira_connector` | function | `JiraConnector` instance for connector tests |
| `_setup_app` | autouse | Sets up FastAPI `TestClient` with dependency overrides for endpoint tests |

## Run

```bash
# All unit tests
pytest tests/unit/ -v -m unit

# Specific module
pytest tests/unit/test_releases_endpoint.py -v

# With coverage
pytest tests/unit/ --cov=api/src --cov-report=term --cov-report=xml

# Full suite with coverage
pytest tests/unit/ tests/integration/ tests/security/ --cov=api/src --cov-report=term

# Rust inline tests
cargo test --lib
```

## Total: 150+ unit test cases across 12 files

## Cobertura global del proyecto: 70%

Ver `tests/README.md` para detalles sobre exclusiones y configuracion de cobertura.

# AGENTS.md — Guide for AI Agents

> This file describes the project context, repository conventions, and
> operational instructions that AI agents (Copilot, Claude, Cursor,
> etc.) must follow when working on this code.

---

## 1. Project Description

**SVAES** (Automatic Software Delivery Verification System) is a generic
academic platform that automates the validation of software *releases* against a
configurable set of verification rules (RV-01 to RV-10).

The project is the Final Degree Project (TFG) of **Adrian Martinez Fuentes (UO295454)**
in the Software Engineering degree at the University of Oviedo (EII).

**There is no real production environment.** All external connectors (GitLab, Jira, etc.)
are reference connectors implementing the `IConnector` port; they are not mandatory
dependencies of the core.

---

## 2. Technology Stack

| Layer | Technology | Minimum Version |
|---|---|---|
| API backend | FastAPI (Python) | 0.136 |
| Domain logic | Python | 3.11 |
| Database | PostgreSQL | 16 |
| ORM / migrations | SQLAlchemy + Alembic | 2.x / 1.x |
| Verification engine | Rust (Actix-web + Rayon) | 1.77 (Implemented — full engine with parallel rule evaluation) |
| Task queue | Celery + Redis | 5.x / 7.x (worker implemented) |
| Frontend | Angular + TypeScript | Angular 21 (implemented) |
| Containers | Docker + Docker Compose | 25 / 2.x |

---

## 3. Repository Structure

```
svaes/
├── api/                       # FastAPI — full code
│   ├── src/
│   │   ├── domain/            # Entities, ports (no external dependencies)
│   │   ├── application/       # Use cases
│   │   │   ├── ports/input/   # Service interfaces (IReleaseService, etc.)
│   │   │   └── ports/output/  # Repository and external service interfaces
│   │   ├── infrastructure/    # Adapters (DB, security, workers, routers)
│   │   └── main.py
│   ├── alembic/              # DB migrations
│   ├── tests/                # API-specific tests
│   └── pyproject.toml
├── engine/                    # Rust verification engine (full with parallel evaluator and 10 rules)
│   └── src/
├── web/                       # Angular SPA (implemented)
│   ├── src/app/features/      # auth, dashboard, releases, connectors, admin, profile, logs, …
│   ├── src/app/core/          # services, guards, interceptors, i18n
│   └── src/assets/i18n/       # en.json, es.json
├── docs/
│   ├── api/                   # API documentation
│   ├── engine/                # Engine documentation
│   ├── development/           # Developer specifications & guidelines
│   └── security/              # Security audit documentation
├── scripts/                   # Auxiliary scripts
├── docker-compose.yml         # Services: api, postgres, redis
└── tests/                     # Full test suite
    ├── unit/                  # Implemented — 59 files (core, connectors, api, repositories)
    ├── integration/           # Implemented — ~90 tests (flow, lifecycle, resilience, rate limit)
    ├── performance/           # Implemented — Rust benchmarks + Locust stub
    ├── security/              # Implemented — auth, injection, OWASP vectors
    └── acceptance/            # Pending — Cypress E2E
```

**Current status:**
- FastAPI backend complete in `api/src/`
- Celery worker implemented (`api/src/infrastructure/workers/verification_worker.py`)
- Rust verification engine complete (`engine/src/` — evaluator, aggregator, 10 rules RV-01 to RV-10)
- Angular frontend implemented (`web/`) — features: auth (login + 2FA + activate), dashboard, releases, connectors, profiles, admin, logs, profile, landing, legal, access-request, system
- i18n: ES/EN via `TranslationService` + `TranslatePipe`; JSON files in `web/src/assets/i18n/`
- TOTP 2FA: pyotp + segno; migration `m1n2o3p4q5r6`; two-step login flow in frontend
- GDPR compliance: audit_log table, consent fields, pseudonymiser in verification worker
- Routers registered: auth, organizations, releases, connectors, profiles, tasks, users, custom_roles, dashboard, api_keys, templates, notifications, admin

---

## 4. Design Principles — rules the agent MUST follow

1. **Dependency rule (Clean Architecture):** code dependencies can only
   point inward. `domain/` imports nothing from `application/` or
   `infrastructure/`. Any change violating this rule must be rejected.

2. **Mandatory genericity:** the system core cannot be coupled to any
   specific external tool. All integration is done by implementing `IConnector`.

3. **Verification engine:** the Rust engine resides in `engine/` and communicates with the
   backend via HTTP (configurable via `ENGINE_URL`). The engine is fully implemented
   with a parallel evaluator (Rayon) and the 10 rules RV-01…RV-10. No DB access or connector logic
   should be added inside the engine.

4. **Multi-tenancy:** all repositories and use cases must mandatorily filter
   by `organization_id`. An agent must not generate code that accesses data from another
   organization.

5. **RBAC:** roles are `U1 < U2 < U3 < U4`. The agent must respect the corresponding guards
   on every new endpoint.

6. **No references to Indra, Multideployment, or Flask:** these contexts are obsolete.
   If they appear in any existing file, they must be removed or generalized.

---

## 5. Code Conventions

### Python (backend — api/src/)
- Formatting: **Black** + **isort**. Maximum line length: 88.
- Types: all functions must be annotated. **Pydantic v2** is used for models.
- Tests: **pytest**. Minimum target coverage: 80% in `domain/` and `application/`.
- Alembic migrations: one file per schema change, with a descriptive message.
- Internal structure of `src/`:
  ```
  src/
  ├── domain/           # entities/, enums.py, exceptions.py, ports/
  ├── application/      # use_cases/main/, use_cases/others/, ports/
  ├── infrastructure/   # primary/, secondary/
  ├── core/             # audit.py, config.py, dependencies.py, logger.py, rate_limit.py
  └── main.py
  ```

### TypeScript (frontend — web/)
- Formatting: **Prettier** + **ESLint** (angular-eslint).
- Standalone components (Angular 17+).

### Rust (engine — engine/)
- Formatting: **rustfmt** (default configuration).
- No `unsafe` unless documentedly justified.
- Unit tests within the same module (`#[cfg(test)]`).

### Git
- Branches: `main` (stable), `dev` (integration), `feat/<name>`, `fix/<name>`.
- Commits in **English**, Conventional Commits format:
  `feat(api): add RV-07 traceability rule`.
- No direct push to `main`.

---

## 6. Tasks the agent can perform without confirmation

- Read and analyze any file in the repository.
- Propose or generate new code that respects the principles in section 4.
- Write or update unit tests.
- Generate Alembic migrations from SQLAlchemy model changes.
- Update the OpenAPI specification when endpoints are added.
- Update this file or `specifications.md` / `api/reference.md` to reflect approved changes.

## 7. Tasks requiring explicit developer confirmation

- Modify the database schema (tables, columns, enum types).
- Change the HTTP interface between backend and engine.
- Add new dependencies (`pyproject.toml`, `Cargo.toml`, `package.json`).
- Remove or rename ports (`IConnector`, `IReleaseRepository`, etc.).
- Any change to the verdict aggregation logic (section 4 of `SPECS.md`).

---

## 8. What the agent MUST NOT do

- Add network calls inside `domain/`.
- Instantiate concrete connectors inside use cases.
- Hardcode external tool names (Jira, GitLab, Confluence…) outside of
  `infrastructure/adapters/`.
- Generate code that omits the `organization_id` filter.
- Modify `verification_result` to be mutable after creation.

---

## 9. Testing Conventions

### Unit tests (`tests/unit/`)

```
tests/unit/
├── core/                           # Credential encryptor, pseudonymizer
│   ├── test_credential_encryptor.py
│   └── test_pseudonymizer.py
├── connectors/                     # 8 connector implementations
│   ├── conftest.py
│   ├── test_gitlab.py
│   ├── test_jira.py
│   ├── test_trello.py
│   ├── test_plane.py
│   ├── test_linear.py
│   ├── test_jira_sm.py
│   ├── test_redmine.py
│   ├── test_gitea.py
│   └── test_wikijs.py
├── api/                            # Use cases, services, routers (34 files)
│   ├── conftest.py                 # 14 mock repos, task queue, connector registry
│   ├── test_authenticate_user.py
│   ├── test_auth_service.py
│   ├── test_releases.py
│   ├── test_releases_router.py
│   ├── test_user_service.py
│   ├── test_verification_service.py
│   ├── test_verification_worker.py
│   └── ...                         # (+26 more files)
└── repositories/                   # 15 SQL repository tests (in-memory SQLite)
    ├── conftest.py
    ├── test_user_repository.py
    ├── test_release_repository.py
    ├── test_project_repository.py
    ├── test_organization_repository.py
    └── ...                         # (+10 more files)
```

- One file per module: `test_<module_name>.py`
- One class per unit: `class Test<UnitName>`
- Methods: `test_<condition>_<expected_result>`
- Domain entities and application commands are **never** mocked.

### Integration tests (`tests/integration/`)

4 Python test files (~90 tests) + 8 Rust HTTP pipeline tests. Real PostgreSQL + Redis via ephemeral Docker containers.

```powershell
# One-command script (spins up infra, runs tests, tears down)
.\scripts\run_integration_tests.ps1
```

### Rust tests

Unit tests are inline under `#[cfg(test)]`. Integration and performance tests live in `engine/tests/`.

```bash
cargo test                              # All unit tests
cargo test --test http_pipeline          # HTTP integration tests
cargo test --test performance            # Performance benchmarks
```

---

## 10. Routers Registered in main.py

The following routers are connected in `api/src/main.py`:

| Router | File | Description |
|--------|------|-------------|
| auth_router | v1/auth | Authentication (login, refresh) |
| organizations_router | v1/organizations | Organization management |
| releases_router | v1/releases | Release and artifact management |
| connectors_router | v1/connectors | Connector management |
| profiles_router | v1/profiles | Verification profile management |
| tasks_router | v1/tasks | Async task status query |
| users_router | v1/users | User management |
| custom_roles_router | v1/custom_roles | Custom roles |
| dashboard_router | v1/dashboard | Dashboard metrics |
| api_keys_router | v1/api_keys | API key management |
| templates_router | v1/templates | Release templates |
| notifications_router | v1/notifications | Notification configuration |
| admin_router | v1/admin | Administration operations |

---

*Last updated: June 2026 — Adrian Martinez Fuentes (UO295454)*

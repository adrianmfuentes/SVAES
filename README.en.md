[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=adrianmfuentes_SVAES&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=adrianmfuentes_SVAES)
[![Status](https://img.shields.io/badge/Thesis-Completed-success)](https://github.com/adrianmfuentes/SVAES)
[![Deploy](https://img.shields.io/badge/Deploy-Production-blue)](https://github.com/adrianmfuentes/SVAES)

**[Español](README.md)** · **[Français](README.fr.md)**

# SVAES

## Automatic Software Delivery Verification System

Final Degree Project — Completed
Bachelor's Degree in Software Engineering
University of Oviedo

Author: Adrián Martínez Fuentes
Academic Year: 2025/2026

---

# 1. Introduction

The Automatic Software Delivery Verification System (SVAES) is a platform designed to automate the validation of software deliveries within modern development processes based on continuous integration.

The system acts as a Quality Gate mechanism, automatically evaluating the consistency, integrity, and completeness of artifacts associated with a release through integration with multiple external systems.

The main objective is to eliminate manual validation processes, reduce human errors, and guarantee full traceability of the delivery lifecycle.

---

# 2. System objectives

## 2.1 General objective

Design and implement an extensible, decoupled system capable of automatically verifying software deliveries in multi-tool environments.

## 2.2 Specific objectives

- Automate release validation
- Guarantee complete traceability of verifications
- Integrate with external tools without tight coupling
- Provide metrics and observability for the quality process
- Enable use as a Quality Gate in CI/CD pipelines

---

# 3. Project status

| Component        | Status         |
| ---------------- | -------------- |
| FastAPI Backend  | Full REST API with 101 endpoints, 16 routers, 178 Python files |
| Angular Frontend | SPA with auth, dashboard, releases, connectors, profile, admin, i18n ES/EN/FR, 2FA, responsive design, WCAG 2.1 AA accessibility, account deletion with automatic ownership transfer, Feedback modal |
| Rust Engine      | Complete engine in engine/, parallel evaluator + 19 rules |
| Celery Worker    | Real worker in verification_worker.py                     |
| Connectors       | 20 connectors in 5 functional categories                  |
| Deployment       | Deployed to production with Docker Compose + Oracle Cloud |
| Tests           | ~2,107 total tests (Python 1,240 / Rust 103 / Vitest 721 / Cypress 43) |

---

# 4. Functional scope

The system covers the following capabilities:

- Organisation management (multi-tenant)
- Project and release management
- **External connector configuration (20 implementations)**
- Verification profile definition
- Automatic verification execution
- Result recording and audit
- REST API exposure for integration

Out of scope:

- CI/CD pipeline execution
- Modification of external systems
- Predictive analysis or artificial intelligence

---

# 5. System architecture

## 5.1 Architectural approach

The system adopts a hybrid architecture based on:

- Hexagonal architecture (Ports & Adapters)
- Clean Architecture

Key principle:

> Dependencies can only point toward the domain.

## 5.2 Container decomposition

The system is divided into the following components:

- Frontend (Angular SPA)
- Backend (FastAPI)
- Verification engine (Rust)
- Task queue (Celery + Redis)
- Database (PostgreSQL)
- External connectors

## 5.3 Backend structure

```
api/src/
├── domain/                    # Entities, enums, exceptions
│   ├── entities/              # User, Organization, Project, Release, Artifact, ConnectorInstance
│   └── enums.py               # UserRole, ConnectorType, ConnectorImplementation, etc.
│
├── application/               # Use cases (business logic)
│   ├── ports/
│   │   ├── input/             # IReleaseService, IConnectorService, etc.
│   │   └── output/            # IUserRepository, IConnectorRegistry, IConnector
│   └── use_cases/             # Use case implementations
│
├── infrastructure/            # Adapters
│   ├── primary/
│   │   ├── routers/           # FastAPI endpoints (v1)
│   │   └── middleware/         # JWT, rate limiting, password hasher
│   └── secondary/
│       ├── database/          # SQLAlchemy models + repositories
│       ├── queue/             # Celery + Redis
│       └── connectors/         # Connector implementations
│           ├── task_management/   # Jira, Linear, Trello, Asana
│           ├── source_control/    # GitHub, GitLab, Bitbucket, Gitea
│           ├── documentation/       # Confluence, Notion, Wiki.js, BookStack
│           ├── planning/           # ClickUp, Taiga, Plane, Miro
│           └── change_management/  # Jira SM, GLPI, Zammad, Redmine
│
└── core/                      # Config, dependencies, rate limiting
```

---

# 6. Connector system

## 6.1 Two-level architecture

The connector system follows a **two-level design**:

| Concept                     | Description             | Examples                                             |
| --------------------------- | ----------------------- | ---------------------------------------------------- |
| **ConnectorType**           | Generic functional type | `GESTOR_TAREAS`, `REPO_CODIGO`, `SISTEMA_DOCUMENTAL` |
| **ConnectorImplementation** | Concrete implementation | `JIRA`, `GITHUB`, `CONFLUENCE`, `LINEAR`             |

A manager configures in their organisation which concrete implementations they want to use for each functional type.

## 6.2 Available functional types

| Type                        | Description                                                      |
| --------------------------- | ---------------------------------------------------------------- |
| `GESTOR_TAREAS`             | Tools that track daily work, user stories and bugs               |
| `REPO_CODIGO`               | Source of truth for branches, commits and version tags           |
| `SISTEMA_DOCUMENTAL`        | Test reports, technical manuals and delivery plans               |
| `HERRAMIENTA_PLANIFICACION` | Long-term roadmap, epics and release plans                       |
| `GESTION_CAMBIOS`           | ITSM systems for formal approvals, CABs and production incidents |

---

# 7. Domain model

Main entities:

- **Organisation** — Main tenant with owner
- **User** — User with role and organisation
- **Project** — Belongs to an org, has verification profile
- **Release** — Software version with status and artifacts
- **Artifact** — External reference linked to a release
- **ConnectorInstance** — Connector configuration in an org
- **VerificationProfile** — Set of rules for a project
- **VerificationRule** — Template with severity and parameters
- **VerificationResult** — Verification result with verdict

---

# 8. Release lifecycle

```text
BORRADOR → PENDIENTE → EN_VERIFICACION → VALIDA
    │           │              │
    │           └──────────────┴──→ NO_VALIDA
    │                               │
    └───────────────────────────────┴──→ CON_ADVERTENCIAS
    │
    └──────────────────────────────────→ ARCHIVADA
```

| State              | Description                                                             |
| ------------------ | ----------------------------------------------------------------------- |
| `BORRADOR`         | Release created, still editable and not yet submitted for verification. |
| `PENDIENTE`        | Release ready to be verified.                                           |
| `EN_VERIFICACION`  | Verification in progress by the worker.                                 |
| `VALIDA`           | Release successfully verified.                                          |
| `NO_VALIDA`        | Release rejected for failing mandatory rules.                           |
| `CON_ADVERTENCIAS` | Release acceptable, but with non-blocking issues.                       |

---

# 9. Persistence

PostgreSQL database:

- UUID as identifiers
- JSONB for dynamic data
- Referential integrity
- Audit trail

---

# 10. Security

| Layer                  | Mechanism                    | Detail                                               |
| ---------------------- | ---------------------------- | ---------------------------------------------------- |
| Authentication         | JWT (HS256)                  | Signed tokens. Claims: `sub`, `role`, `iat`, `exp`   |
| Two-factor auth (2FA)  | TOTP (pyotp + segno)         | Optional per-user two-step authentication            |
| Passwords              | bcrypt (passlib)             | Cost factor 12. Constant-time comparison             |
| Connector credentials  | Fernet (AES-128-CBC)         | Authenticated encryption                             |
| Protected endpoints    | Bearer token                 | `Authorization: Bearer <jwt>` required               |
| Multi-tenant isolation | Filter by `organization_id`  | 403 on cross-org access                              |
| Rate limiting          | slowapi                      | 30 req/min on auth, 100 req/min reads, 20 req/min writes |
| Brute force            | Account lockout              | 5 failed attempts → 15 min block                     |
| GDPR audit             | audit_log (PostgreSQL)       | Full traceability; pseudonymisation in verifications |

---

# 11. Technologies

| Layer               | Technology               |
| ------------------- | ------------------------ |
| API Backend         | FastAPI (Python 3.11+)   |
| Database            | PostgreSQL 16            |
| ORM                 | SQLAlchemy 2.x           |
| Migrations          | Alembic                  |
| Authentication      | JWT (PyJWT)              |
| HTTP Client         | httpx (async)            |
| Frontend            | Angular 21               |
| Verification engine | Rust (Actix-web + Rayon) |
| Task queue          | Celery + Redis           |
| Containers          | Docker + Docker Compose  |

---

# 12. Environment variables

| Variable             | Description                                   | Required |
| -------------------- | --------------------------------------------- | -------- |
| `DATABASE_URL`       | `postgresql+asyncpg://user:pass@host:5432/db` | Yes      |
| `JWT_SECRET_KEY`     | JWT token signing key                         | Yes      |
| `JWT_ALGORITHM`      | JWT algorithm (default: `HS256`)              | No       |
| `JWT_EXPIRE_MINUTES` | Token expiration in minutes (default: `60`)   | No       |
| `ENCRYPTION_KEY`     | Fernet key for credential encryption          | Yes      |
| `ENVIRONMENT`        | `development` or `production`                 | No       |
| `ALLOWED_ORIGINS`    | CORS origins separated by comma               | No       |
| `FEEDBACK_SYNC_KEY`  | Shared secret used by the feedback-sync GitHub Action to read `/api/v1/feedback/public` | No |

Generate `ENCRYPTION_KEY`:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

# 13. API — Main endpoints

Base URL: `http://localhost:8000/api/v1`
Interactive documentation: `http://localhost:8000/docs`

### Authentication

| Method | Path                   | Auth | Description                            |
| ------ | ---------------------- | ---- | -------------------------------------- |
| `POST` | `/auth/login`          | No   | Login → returns JWT (step 1 if 2FA on) |
| `POST` | `/auth/2fa/verify`     | No   | Verify TOTP code (step 2)              |
| `POST` | `/auth/refresh`        | No   | Refresh token                          |
| `POST` | `/auth/register`       | No   | Register with terms acceptance         |

### Organisations

| Method | Path                                 | Auth     | Description        |
| ------ | ------------------------------------ | -------- | ------------------ |
| `GET`  | `/organizations`                     | ADMIN    | List all           |
| `POST` | `/organizations`                     | ADMIN    | Create             |
| `GET`  | `/organizations/{org_id}/connectors` | MANAGER+ | List connectors    |
| `POST` | `/organizations/{org_id}/connectors` | MANAGER+ | Register connector |

### Releases and verifications

| Method | Path                      | Auth      | Description         |
| ------ | ------------------------- | --------- | ------------------- |
| `POST` | `/projects/{id}/releases` | OPERATOR+ | Create release      |
| `POST` | `/releases/{id}/verify`   | OPERATOR+ | Launch verification |
| `GET`  | `/releases/{id}/results`  | OPERATOR+ | Results history     |

### Connectors

| Method | Path                    | Auth     | Description                    |
| ------ | ----------------------- | -------- | ------------------------------ |
| `GET`  | `/connectors/types`     | Any user | List types and implementations |
| `POST` | `/connectors/{id}/test` | MANAGER+ | Test connection                |

### Feedback

| Method | Path                | Auth           | Description                                                       |
| ------ | -------------------- | -------------- | ------------------------------------------------------------------ |
| `POST` | `/feedback`           | No             | Submit feedback from the landing page footer                       |
| `GET`  | `/feedback/public`    | Shared secret  | Public listing (no email) used by the README sync GitHub Action    |

---

# 14. Running the system

## Local development (with Docker)

```bash
git clone https://github.com/adrianmfuentes/svaes.git
cd svaes
docker compose up --build
```

API: `http://localhost:8000` · Swagger: `http://localhost:8000/docs` · PostgreSQL: `localhost:5432`

## Local development (without Docker)

```bash
# Only the database
docker compose up postgres -d

cd api
pip install -e .
uvicorn src.main:app --reload --port 8000
```

## Production

```bash
export DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/svaes"
export JWT_SECRET_KEY="long-random-secure-key"
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

---

# 15. User feedback

Users can submit feedback (a 1-5 rating and a comment) through a form in the landing page footer. Every submission triggers a notification email to the address configured in `ADMIN_EMAIL` and is stored in the database.

A scheduled GitHub Action ([`feedback-sync.yml`](.github/workflows/feedback-sync.yml)) periodically syncs the feedback received (name, rating and comment — never the email) into the section below, as visible proof that the system has real users:

<!-- FEEDBACK:START -->
_No feedback published yet. Be the first to share your opinion from the landing page._
<!-- FEEDBACK:END -->

This section is kept up to date automatically only in the [Spanish README](README.md); this translated copy reflects the structure but is not re-synced on every run.

---

# 16. Conclusion

The project has been completed as a Final Degree Project at the University of Oviedo (2025/2026), pending submission and defense. The system provides a decoupled, extensible, and robust solution for automatic software delivery verification, currently deployed in production.

The system is fully operational with:

- 20 connector implementations across 5 functional types
- Angular frontend with 2FA authentication, dashboard, release and connector management, account deletion with automatic organisation ownership transfer
- ES/EN/FR internationalisation across all frontend modules
- Responsive design: hamburger sidebar ≤1024px, horizontal table scroll, grid collapse at ≤768px
- WCAG 2.1 AA accessibility: skip links, ARIA roles, colour+text status indicators, focus-visible
- Complete multi-tenant isolation with GDPR audit trail
- RBAC with three predefined roles (OPERATOR, MANAGER, ADMIN)
- Comprehensive test suite: 200+ unit tests, 16 integration tests, 5 security tests, 4 performance tests, 12 acceptance tests

---

_Last updated: June 30, 2026 — Adrián Martínez Fuentes (UO295454)_


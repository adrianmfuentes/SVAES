[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=adrianmfuentes_SVAES&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=adrianmfuentes_SVAES)

**[Español](README.md)** · **[Français](README.fr.md)**

# SVAES

## Automatic Software Delivery Verification System

Final Degree Project
Bachelor's Degree in Software Engineering
University of Oviedo

Author: Adrián Martínez
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

| Component        | Status         | Description                                               |
| ---------------- | -------------- | --------------------------------------------------------- |
| FastAPI Backend  | ✅ Complete    | Full REST API with all endpoints                          |
| Angular Frontend | ⏳ Pending     | Empty SPA, pending implementation                         |
| Rust Engine      | ✅ Implemented | Complete engine in engine/, parallel evaluator + 10 rules |
| Celery Worker    | ✅ Implemented | real worker in verification_worker.py                     |
| Connectors       | ✅ Implemented | 20 connectors in 5 functional categories                  |

---

# 4. Functional scope

The system covers the following capabilities:

- Organization management (multi-tenant)
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

- Frontend (Angular SPA) — ⏳ Pending
- Backend (FastAPI) — ✅ Complete
- Verification engine (Rust) — ✅ Implemented (complete)
- Task queue (Celery + Redis) — ✅ Implemented
- Database (PostgreSQL) — ✅ Operational
- External connectors — ✅ 20 implementations

## 5.3 Backend structure

```
api/src/
├── domain/                    # Entities, enums, exceptions
│   ├── entities/              # User, Organization, Project, Release, Artifact, ConnectorInstance
│   └── enums.py                # UserRole, ConnectorType, ConnectorImplementation, etc.
│
├── application/                # Use cases (business logic)
│   ├── ports/
│   │   ├── input/             # IReleaseService, IConnectorService, etc.
│   │   └── output/            # IUserRepository, IConnectorRegistry, IConnector
│   └── use_cases/             # Use case implementations
│
├── infrastructure/             # Adapters
│   ├── primary/
│   │   ├── routers/           # FastAPI endpoints (v1)
│   │   └── middleware/         # JWT, rate limiting, password hasher
│   └── secondary/
│       ├── database/          # SQLAlchemy models + repositories
│       ├── queue/             # Celery + Redis
│       └── connectors/        # Connector implementations
│           ├── task_management/    # Jira, Linear, Trello, Asana
│           ├── source_control/    # GitHub, GitLab, Bitbucket, Gitea
│           ├── documentation/        # Confluence, Notion, Wiki.js, BookStack
│           ├── planning/           # ClickUp, Taiga, Plane, Miro
│           └── change_management/ # Jira SM, GLPI, Zammad, Redmine
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

A manager configures in their organization which concrete implementations they want to use for each functional type.

## 6.2 Available functional types

| Type                        | Description                                                      |
| --------------------------- | ---------------------------------------------------------------- |
| `GESTOR_TAREAS`             | Tools that track daily work, user stories and bugs               |
| `REPO_CODIGO`               | Source of truth for branches, commits and version tags           |
| `SISTEMA_DOCUMENTAL`        | Test reports, technical manuals and delivery plans               |
| `HERRAMIENTA_PLANIFICACION` | Long-term roadmap, epics and release plans                       |
| `GESTION_CAMBIOS`           | ITSM systems for formal approvals, CABs and production incidents |

## 6.3 Available implementations

### GESTOR_TAREAS

| Implementation | API        | Free plan       |
| -------------- | ---------- | --------------- |
| Jira           | REST v2/v3 | 10 users        |
| Linear         | GraphQL    | Solid           |
| Trello         | REST       | Very permissive |
| Asana          | REST       | 15 users        |

### REPO_CODIGO

| Implementation | API     | Free plan                |
| -------------- | ------- | ------------------------ |
| GitLab         | REST v4 | Unlimited                |
| GitHub         | REST    | Unlimited                |
| Bitbucket      | REST    | 5 users                  |
| Gitea          | REST    | Self-hosted, open source |

### SISTEMA_DOCUMENTAL

| Implementation | API     | Free plan                |
| -------------- | ------- | ------------------------ |
| Confluence     | REST    | 10 users                 |
| Notion         | REST    | Very complete            |
| Wiki.js        | GraphQL | Self-hosted, open source |
| BookStack      | REST    | Self-hosted, open source |

### HERRAMIENTA_PLANIFICACION

| Implementation | API  | Free plan                |
| -------------- | ---- | ------------------------ |
| ClickUp        | REST | Very complete            |
| Taiga          | REST | Cloud or self-hosted     |
| Plane          | REST | Self-hosted, open source |
| Miro           | REST | 3 boards                 |

### GESTION_CAMBIOS

| Implementation          | API      | Free plan                |
| ----------------------- | -------- | ------------------------ |
| Jira Service Management | REST     | 3 agents                 |
| GLPI                    | REST     | Self-hosted, open source |
| Zammad                  | REST     | Self-hosted, open source |
| Redmine                 | REST/XML | Self-hosted, open source |

## 6.4 IConnector port

```python
class IConnector(Protocol):
    @property
    def connector_type(self) -> str: ...

    @property
    def connector_implementation(self) -> str: ...

    async def test_connection(self, config: Dict[str, Any]) -> bool: ...

    async def fetch_artifact(self, ref: str, config: Dict[str, Any]) -> Dict[str, Any]: ...

    async def list_artifacts(self, filter_params: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]: ...

    def get_metadata(self) -> Dict[str, Any]: ...
```

## 6.5 UI configuration flow

1. UI calls `GET /api/v1/connectors/types` to see available implementations
2. UI renders form using `config_schema` from each implementation
3. Manager fills form and sends `POST /api/v1/organizations/{org_id}/connectors`
4. System stores `connector_type`, `connector_implementation` and encrypted credentials
5. During verification, `connector_implementation` is used to instantiate the correct connector

---

# 7. Domain model

Main entities:

- **Organization** — Main tenant with owner
- **User** — User with role and organization
- **Project** — Belongs to an org, has verification profile
- **Release** — Software version with status and artifacts
- **Artifact** — External reference linked to a release
- **ConnectorInstance** — Connector configuration in an org
- **VerificationProfile** — Set of rules for a project
- **VerificationRule** — Template with severity and parameters
- **VerificationResult** — Verification result with verdict

Each verification stores a complete snapshot of the evaluated state.

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

| Layer                  | Mechanism                | Detail                                             |
| ---------------------- | ------------------------ | -------------------------------------------------- |
| Authentication         | JWT (HS256)              | Signed tokens. Claims: `sub`, `role`, `iat`, `exp` |
| Passwords              | bcrypt (passlib)         | Cost factor 12. Constant-time comparison           |
| Connector credentials  | Fernet (AES-128-CBC)     | Authenticated encryption                           |
| Protected endpoints    | Bearer token             | `Authorization: Bearer <jwt>` required             |
| Multi-tenant isolation | `organization_id` filter | 403 on cross-org access                            |
| Rate limiting          | slowapi                  | 100 req/min reads, 20 req/min writes               |
| Brute force            | Account lockout          | 5 failed attempts → 15 min block                   |

---

# 11. Technologies

| Layer               | Technology               | Status                      |
| ------------------- | ------------------------ | --------------------------- |
| API Backend         | FastAPI (Python 3.11+)   | ✅ Complete                 |
| Database            | PostgreSQL 16            | ✅ Operational              |
| ORM                 | SQLAlchemy 2.x           | ✅ Operational              |
| Migrations          | Alembic                  | ✅ Operational              |
| Authentication      | JWT (PyJWT)              | ✅ Complete                 |
| HTTP Client         | httpx (async)            | ✅ Integrated in connectors |
| Frontend            | Angular 21               | ⏳ Pending                  |
| Verification engine | Rust (Actix-web + Rayon) | ✅ Implemented              |
| Task queue          | Celery + Redis           | ✅ Implemented              |
| Containers          | Docker + Docker Compose  | ✅ Configured               |

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

Generate `ENCRYPTION_KEY`:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

# 13. API — Main endpoints

Base URL: `http://localhost:8000/api/v1`
Interactive documentation: `http://localhost:8000/docs`

### Authentication

| Method | Path            | Auth | Description         |
| ------ | --------------- | ---- | ------------------- |
| `POST` | `/auth/login`   | No   | Login → returns JWT |
| `POST` | `/auth/refresh` | No   | Refresh token       |

### Organizations

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

# 15. Conclusion

The system provides a decoupled, extensible, and robust solution for automatic software delivery verification.

The FastAPI backend is fully operational with:

- 20 connector implementations across 5 functional types
- UI configuration system for managers
- Complete multi-tenant isolation
- RBAC with predefined and custom roles

Pending: Angular frontend.

---

_Last updated: May 2026 — Adrián Martínez (UO295454)_

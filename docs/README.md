# SVAES — Automatic Software Delivery Verification System

> **Final Degree Project** — Software Engineering Degree, University of Oviedo (2025/2026)
> Author: Adrian Martinez

SVAES is an extensible, decoupled **Quality Gate platform** that automates the validation of software releases within modern CI/CD workflows. By integrating with multiple external tools across five functional categories, it verifies the consistency, integrity, and completeness of artifacts linked to a release — eliminating manual checks and guaranteeing full traceability.

---

## How It Works

1.  A release is created in a project and linked to external artifacts (tasks, commits, documents, etc.).
2.  A verification profile defines which rules to apply and their severity.
3.  Verification is triggered — the Rust engine fetches artifact data from configured connectors and evaluates all rules in parallel.
4.  Results are aggregated into a **global verdict**: Valid, Invalid, or With Warnings.
5.  Teams can act on recommendations, export reports (PDF/CSV), and use the API directly in CI/CD pipelines.

---

## Architecture at a Glance

| Component               | Technology               | Role                                              |
| ----------------------- | ------------------------ | ------------------------------------------------- |
| **API Backend**         | FastAPI (Python 3.11+)   | REST API, business logic, multi-tenant management |
| **Verification Engine** | Rust (Actix-web + Rayon) | Parallel rule evaluation and verdict computation  |
| **Task Queue**          | Celery + Redis           | Async dispatch of verification jobs               |
| **Database**            | PostgreSQL 16            | Persistent storage with UUIDs and JSONB support   |
| **Frontend**            | Angular 21               | Full-featured SPA: auth, dashboard, releases, connectors, profiles, admin, i18n, 2FA |
| **Infrastructure**      | Docker + Docker Compose  | Containerized multi-service deployment            |

The system follows a **Hexagonal (Ports & Adapters)** and **Clean Architecture** approach, ensuring the domain core has zero external dependencies.

```
api/src/
├── domain/                  # Entities, enums, exceptions
├── application/
│   ├── ports/               # Input/output interfaces (contracts)
│   └── use_cases/           # Business logic implementations
├── infrastructure/
│   ├── primary/             # FastAPI routers, middleware
│   └── secondary/           # Repositories, connectors, task queue
└── core/                    # Config, DI, rate limiting, encryption
```

---

## Connector System (Two-Level Design)

The integration layer has a **two-level abstraction** that decouples functional intent from implementation:

| Level                       | Concept                     | Examples                                                    |
| --------------------------- | --------------------------- | ----------------------------------------------------------- |
| **ConnectorType**           | Generic functional category | `TASK_MANAGEMENT`, `SOURCE_CONTROL`, `DOCUMENTATION_SYSTEM` |
| **ConnectorImplementation** | Concrete integration        | `JIRA`, `GITHUB`, `CONFLUENCE`, `LINEAR`                    |

### Available Connectors (20 total)

| Category              | Implementations                                |
| --------------------- | ---------------------------------------------- |
| **Task Management**   | Jira, Linear, Trello, Asana                    |
| **Source Control**    | GitHub, GitLab, Bitbucket, Gitea               |
| **Documentation**     | Confluence, Notion, Wiki.js, BookStack         |
| **Change Management** | Jira Service Management, GLPI, Zammad, Redmine |
| **Planning**          | ClickUp, Taiga, Plane, Miro                    |

All connectors implement the `IConnector` interface (`fetch_artifact`, `list_artifacts`, `test_connection`, `get_metadata`) and store credentials encrypted with **Fernet (AES-128-CBC)**.

---

## Verification Rules (RV-01 → RV-10)

| Rule  | Name                    | Description                                                             |
| ----- | ----------------------- | ----------------------------------------------------------------------- |
| RV-01 | Artifact Existence      | Validates that referenced artifacts actually exist in external systems  |
| RV-02 | Artifact Traceability   | Checks bidirectional links between tasks, commits, and documents        |
| RV-03 | Artifact State          | Verifies artifacts are in a valid/completed state                       |
| RV-04 | Numeric Field Integrity | Ensures numeric fields (story points, estimates) are positive and valid |
| RV-05 | Document Accessibility  | Confirms linked documents are publicly accessible or reachable          |
| RV-06 | Attribute Coherence     | Ensures title fields, descriptions, and labels are populated            |
| RV-07 | External Registration   | Validates records exist in external registration/CHG systems            |
| RV-08 | List Alignment          | Checks that artifact lists match expected counts or content             |
| RV-09 | Reference Validation    | Validates cross-references between artifacts are consistent             |
| RV-10 | Final Approval          | Verifies final sign-off or approval artifacts are present               |

Each rule returns a `PASS`, `FAIL`, or `WARNING` status with a severity level (`BLOCKING`, `NON_BLOCKING`, `INFORMATIONAL`).

---

## Release Lifecycle

```
DRAFT → PENDING → IN_VERIFICATION → VALID
  │         │            │
  │         └────────────┴──→ INVALID
  │                            │
  └────────────────────────────┴──→ WITH_WARNINGS
  │
  └───────────────────────────────→ ARCHIVED
```

---

## Security

| Layer                 | Mechanism                   | Details                                               |
| --------------------- | --------------------------- | ----------------------------------------------------- |
| Authentication        | JWT (HS256)                 | Signed tokens with `sub`, `role`, `iat`, `exp` claims |
| Two-Factor Auth (2FA) | TOTP (pyotp + segno)        | Optional per-user; QR code provisioning in profile    |
| Passwords             | bcrypt (cost 12)            | Constant-time comparison via passlib                  |
| Connector Credentials | Fernet (AES-128-CBC)        | Authenticated encryption at rest                      |
| Multi-tenancy         | `organization_id` filtering | 403 on cross-tenant access                            |
| Rate Limiting         | slowapi                     | 30 req/min on auth, 100 req/min reads, 20 req/min writes |
| Brute Force           | Account lockout             | 5 failed attempts → 15 min block                      |
| GDPR Audit Trail      | `audit_log` table           | All sensitive operations persisted with timestamps    |
| Pseudonymisation      | SHA-256 PII hashing         | Applied to artifact metadata before engine dispatch   |
| API Keys              | Up to 5 per user            | Programmatic CI/CD access                             |

---

## Quick Start

### Docker (all services)

```bash
git clone https://github.com/adrianmfuentes/svaes.git
cd svaes

# Copy .env.example to .env and fill in required secrets:
#   JWT_SECRET_KEY, ENCRYPTION_KEY

docker compose up --build
```

Access points: API at `http://localhost:8000`, Swagger docs at `http://localhost:8000/docs`, PostgreSQL at `localhost:5432`.

### Local Development (API only)

```bash
docker compose up postgres -d
cd api
pip install -e .
uvicorn src.main:app --reload --port 8000
```

### Production

```bash
export DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/svaes"
export JWT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export ENCRYPTION_KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

---

## Key Endpoints (API v1)

Base: `http://localhost:8000/api/v1`

### Auth

| Method | Path            | Description               |
| ------ | --------------- | ------------------------- |
| `POST` | `/auth/login`   | Authenticate, returns JWT |
| `POST` | `/auth/refresh` | Refresh access token      |

### Releases & Verification

| Method | Path                      | Description              |
| ------ | ------------------------- | ------------------------ |
| `POST` | `/projects/{id}/releases` | Create a release         |
| `POST` | `/releases/{id}/verify`   | Trigger verification     |
| `GET`  | `/releases/{id}/results`  | Get verification results |

### Connectors

| Method | Path                                 | Description                                        |
| ------ | ------------------------------------ | -------------------------------------------------- |
| `GET`  | `/connectors/types`                  | List available connector types and implementations |
| `POST` | `/connectors/{id}/test`              | Test connector connection                          |
| `GET`  | `/organizations/{org_id}/connectors` | List configured connectors                         |
| `POST` | `/organizations/{org_id}/connectors` | Register a new connector                           |

### Organizations & Users

| Method | Path             | Description            |
| ------ | ---------------- | ---------------------- |
| `GET`  | `/organizations` | List all organizations |
| `POST` | `/organizations` | Create organization    |
| `GET`  | `/users`         | List users             |
| `POST` | `/users`         | Create user            |

---

## Project Structure

```
SVAES/
├── api/                         # Backend (FastAPI)
│   ├── src/
│   │   ├── domain/              # Domain layer
│   │   ├── application/         # Use cases & ports
│   │   ├── infrastructure/      # Adapters (DB, connectors, queue)
│   │   ├── workers/             # Celery verification worker
│   │   └── core/                # Config, DI, encryption, audit
│   ├── alembic/                 # Database migrations
│   └── Dockerfile
├── engine/                      # Verification engine (Rust)
│   ├── src/                     # Main, models, evaluator, rules
│   └── Dockerfile
├── web/                         # Frontend (Angular — implemented)
│   ├── src/app/
│   │   ├── features/            # auth, dashboard, releases, connectors, admin, profile, logs, …
│   │   └── core/                # services, guards, interceptors, i18n
│   ├── src/assets/i18n/         # en.json, es.json
│   └── Dockerfile
├── tests/                       # Unit (150+ cases), integration (16), performance (4+3), acceptance (10) — 70% coverage
├── docs/                        # Project documentation
│   ├── api/
│   │   ├── reference.md         # Full API endpoint & domain reference
│   │   └── postman/             # Postman collection & environment
│   ├── engine/
│   │   └── reference.md         # Engine technical reference
│   ├── development/
│   │   ├── guidelines.md        # AI agent & contributor conventions
│   │   ├── specifications.md    # Functional specification (SRS summary)
│   │   └── testing.md           # Test suite guide
│   ├── security/
│   │   └── audit.md             # Security & compliance audit
│   └── deployment.md            # Production deployment guide
├── scripts/                     # Utility scripts
├── docker-compose.yml           # Base compose (6 services)
├── docker-compose.dev.yml       # Dev overrides
└── docker-compose.prod.yml      # Production overrides
```

---

## RBAC Roles

| Role         | Permissions                                               |
| ------------ | --------------------------------------------------------- |
| **Viewer**   | Read-only access to releases, results, dashboards         |
| **Operator** | Create releases, trigger verifications, manage artifacts  |
| **Manager**  | Configure connectors, profiles, projects; view audit logs |
| **Admin**    | Manage users, organizations, system configuration         |

Custom roles with granular permissions are also supported.

---

## Tech Stack

| Layer       | Technology                           | Status      |
| ----------- | ------------------------------------ | ----------- |
| API Backend | FastAPI (Python 3.11+)               | Complete    |
| Database    | PostgreSQL 16                        | Operational |
| ORM         | SQLAlchemy 2.x (async)               | Operational |
| Migrations  | Alembic                              | Operational |
| Auth        | PyJWT + bcrypt                       | Complete    |
| HTTP Client | httpx (async)                        | Integrated  |
| Task Queue  | Celery + Redis 7                     | Implemented |
| Engine      | Rust (Actix-web + Rayon)             | Implemented |
| Frontend    | Angular 21                           | Implemented    |
| Containers  | Docker + Docker Compose              | Configured  |
| CI          | GitHub Actions, SonarCloud, CodeQL   | Active      |
| Testing     | pytest + pytest-asyncio + pytest-cov | Configured  |

---

## Environment Variables

| Variable             | Required | Description                                                 |
| -------------------- | -------- | ----------------------------------------------------------- |
| `DATABASE_URL`       | Yes      | `postgresql+asyncpg://user:pass@host:5432/svaes`            |
| `JWT_SECRET_KEY`     | Yes      | JWT signing key (generate with `secrets.token_urlsafe(32)`) |
| `ENCRYPTION_KEY`     | Yes      | Fernet key for connector credential encryption              |
| `JWT_ALGORITHM`      | No       | Algorithm (default: `HS256`)                                |
| `JWT_EXPIRE_MINUTES` | No       | Token expiry in minutes (default: `60`)                     |
| `ENVIRONMENT`        | No       | `development` or `production`                               |
| `ALLOWED_ORIGINS`    | No       | Comma-separated CORS origins                                |
| `POSTGRES_USER`      | Yes      | Database user                                               |
| `POSTGRES_PASSWORD`  | Yes      | Database password                                           |
| `REDIS_PASSWORD`     | No       | Redis authentication password                               |
| `ENGINE_API_KEY`     | Yes      | Internal API key for engine communication                   |

---

## Further Reading

- [API Reference & Domain Model](api/reference.md)
- [Postman Collection & Testing Guide](api/postman/)
- [Verification Engine Technical Reference](engine/reference.md)
- [Functional Specifications](development/specifications.md)
- [Developer Guidelines](development/guidelines.md)
- [Testing Guide](development/testing.md)
- [Production Deployment](deployment.md)
- [Security & Compliance Audit](security/audit.md)

---

*Last updated: June 2026 — Adrian Martinez*

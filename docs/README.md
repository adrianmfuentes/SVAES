# SVAES — Automatic Software Delivery Verification System

> **Final Degree Project — Completed** (30/06/2026) — Software Engineering Degree, University of Oviedo (2025/2026)
> Author: Adrian Martinez Fuentes
> Status: **Deployed in production**

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

## Verification Rules

10 built-in business rules (RV-01 → RV-10), plus `custom_field_check` for organization-defined conditions with no Rust required. Full rule table: [Engine Reference](engine/reference.md#verification-rules).

Each rule returns `PASS`, `FAIL`, or `WARNING` with a severity (`BLOCKING`, `NON_BLOCKING`, `INFORMATIONAL`).

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

## API

Base URL `http://localhost:8000/api/v1`; interactive Swagger UI at `http://localhost:8000/docs`. Full endpoint-by-endpoint reference: [docs/api/reference.md](api/reference.md).

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
│   ├── DEPLOY.md                # Production deploy workflow (GitHub Actions + Oracle Cloud)
│   ├── MULTI_ORG.md             # Multi-organisation membership model
│   └── WALKTHROUGH.md           # End-to-end usage walkthrough
├── scripts/                     # Utility scripts
├── docker-compose.yml           # Base compose (6 services)
├── docker-compose.dev.yml       # Dev overrides
└── docker-compose.prod.yml      # Production overrides
```

---

## RBAC Roles

| Role         | Permissions                                               |
| ------------ | --------------------------------------------------------- |
| **Operator** | Create releases, trigger verifications, manage artifacts  |
| **Manager**  | Configure connectors, profiles, projects; view audit logs |
| **Admin**    | Manage users, organisations, system configuration         |

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
| `FEEDBACK_SYNC_KEY`  | No       | Shared secret the feedback-sync GitHub Action uses to read `/api/v1/feedback/public` |

Deploy-time secrets (SSH keys, SMTP, initial admin) are separate — see [DEPLOY.md](DEPLOY.md).

---

## Further Reading

- [API Reference & Domain Model](api/reference.md)
- [Postman Collection & Testing Guide](api/postman/)
- [Verification Engine Technical Reference](engine/reference.md)
- [Functional Specifications](development/specifications.md)
- [Developer Guidelines](development/guidelines.md)
- [Testing Guide](development/testing.md)
- [Deploy Workflow Guide](DEPLOY.md)
- [Multi-Organisation Model](MULTI_ORG.md)
- [End-to-End Walkthrough](WALKTHROUGH.md)
- [Security & Compliance Audit](security/audit.md)

---

*Last updated: 30 June 2026 — Adrián Martínez Fuentes*

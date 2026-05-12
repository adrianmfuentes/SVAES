[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=adrianmfuentes_SVAES&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=adrianmfuentes_SVAES)

**[Español](README.md)** · **[Français](README.fr.md)**

# SVAES
## Automatic Software Delivery Verification System

Final Degree Project
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

# 3. Functional scope

The system covers the following capabilities:

- Organization management (multi-tenant)
- Project and release management
- External connector configuration
- Verification profile definition
- Automatic verification execution
- Result recording and audit
- REST API exposure for integration

Out of scope:

- CI/CD pipeline execution
- Modification of external systems
- Predictive analysis or artificial intelligence

---

# 4. System architecture

## 4.1 Architectural approach

The system adopts a hybrid architecture based on:

- Hexagonal architecture (Ports & Adapters)
- Clean Architecture

Key principle:

Dependencies can only point toward the domain.

## 4.2 Container decomposition

The system is divided into the following components:

- Frontend (Angular SPA)
- Backend (FastAPI)
- Verification engine (Rust)
- Task queue (Celery + Redis)
- Database (PostgreSQL)
- External connectors

## 4.3 Execution flow

1. User launches a verification
2. Backend validates the release state
3. A task is enqueued
4. A worker processes the task
5. Data is fetched via connectors
6. The engine executes
7. The result is saved
8. The frontend queries the state

---

# 5. Domain model

Main entities:

- Organization
- Project
- Release
- Artifact
- VerificationProfile
- VerificationRule
- VerificationResult
- ConnectorInstance

Each verification stores a complete snapshot of the evaluated state.

---

# 6. Release lifecycle

The release lifecycle defines the states a delivery passes through from creation to the final verification result.

```text
BORRADOR
   |
   v
PENDIENTE
   |
   v
EN_VERIFICACION
   |
   +--> VALIDA
   +--> NO_VALIDA
   +--> CON_ADVERTENCIAS
```

| State | Description |
| --- | --- |
| `BORRADOR` | Release created, still editable and not yet submitted for verification. |
| `PENDIENTE` | Release ready to be verified. |
| `EN_VERIFICACION` | Verification in progress by the worker. |
| `VALIDA` | Release successfully verified. |
| `NO_VALIDA` | Release rejected for failing mandatory rules. |
| `CON_ADVERTENCIAS` | Release acceptable, but with non-blocking issues. |

Final states: `VALIDA`, `NO_VALIDA`, and `CON_ADVERTENCIAS`.

---

# 7. Verification engine (Rust)

Processes the JSON payload from the worker and returns the verification result.

Characteristics:
- Parallel execution (Rayon)
- No network calls (all in memory)
- Deterministic and reproducible

Pipeline: Validation → Rule evaluation → Aggregation → Verdict

```
engine/src/
├── main.rs          # Entry point (Actix-web)
├── pipeline.rs      # Verification pipeline
├── models.rs        # Data models
└── rules/           # RV-01 to RV-10
```

---

# 8. Connectors

Main port:

IConnector

Allows integrating external systems without modifying the core.

---

# 9. Persistence

PostgreSQL database:

- UUID as identifiers
- JSONB for dynamic data
- Referential integrity
- Audit

---

# 10. Security

| Layer | Mechanism | Detail |
| --- | --- | --- |
| Authentication | JWT (HS256) | Tokens signed with `PyJWT`. Claims: `sub`, `role`, `iat`, `exp` |
| Passwords | bcrypt (passlib) | Cost factor 12. Constant-time comparison |
| Connector credentials | Fernet (AES-128-CBC) | Authenticated encryption — fails if the ciphertext is modified |
| Protected endpoints | Bearer token | `Authorization: Bearer <jwt>` required on all business endpoints |
| Transactions | SQLAlchemy `session.begin()` | Automatic COMMIT on success, automatic ROLLBACK on exception |

### Authentication flow

```
POST /api/v1/auth/login
  body: { "email": "...", "password": "..." }
  → verifies bcrypt against hash in DB
  → returns JWT

Protected requests:
  header: Authorization: Bearer <JWT>
  → get_current_user validates signature + expiration
  → injects User entity to the endpoint
  → 401 if token invalid or expired
```

---

# 11. Technologies

- Angular
- FastAPI
- Rust
- PostgreSQL
- Celery
- Redis
- Docker

---

# 12. Project structure

```
svaes/
├── apps/
│   ├── api/               # FastAPI Backend (Python)
│   │   ├── alembic/       # Database migrations
│   │   ├── src/
│   │   │   ├── main.py         # Entry point + lifespan
│   │   │   ├── domain/         # Entities and ports (no external dependencies)
│   │   │   │   ├── entities/   # User, Organization, Project, Release, Artifact...
│   │   │   │   └── ports/      # Interfaces: IUserRepository, ITaskQueue, IConnector...
│   │   │   ├── application/    # Use cases
│   │   │   │   └── use_cases/  # auth, users, organizations, projects, releases...
│   │   │   ├── infrastructure/ # Implementations (DB, security, queue)
│   │   │   │   ├── database/   # SQLAlchemy models + repositories
│   │   │   │   ├── queue/      # Celery + Redis
│   │   │   │   ├── workers/    # verification_worker
│   │   │   │   ├── security/   # JWT, bcrypt, Fernet
│   │   │   │   └── adapters/   # connector_registry
│   │   │   └── api/       # HTTP routers and schemas
│   │   ├── tests/         # API tests
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   └── web/               # Angular Frontend
├── packages/              # Shared internal packages
├── tests/                 # Complete test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   ├── e2e/               # End-to-end tests
│   ├── performance/       # Performance tests
│   └── security/           # Security tests
├── scripts/              # Helper scripts
├── docs/                  # Technical documentation
├── docker-compose.yml    # Services: api, postgres, redis
└── README.md
```

---

# 13. Environment variables

Copy `.env.example` as reference. Variables consumed by the Python API:

| Variable | Description | Required in prod |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+psycopg://user:pass@host:5432/db` | Yes |
| `JWT_SECRET_KEY` | JWT token signing key | Yes |
| `JWT_ALGORITHM` | JWT algorithm (default: `HS256`) | No |
| `JWT_EXPIRE_MINUTES` | Token expiration in minutes (default: `60`) | No |
| `ENCRYPTION_KEY` | Fernet key for credential encryption | Yes |

Generate `ENCRYPTION_KEY`:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

# 14. API — Main endpoints

Base URL: `http://localhost:8000/api/v1`
Interactive documentation: `http://localhost:8000/docs`

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| `POST` | `/auth/login` | No | Login → returns JWT |
| `POST` | `/organizations` | Yes | Create organization |
| `GET` | `/organizations` | Yes | List organizations |
| `POST` | `/projects` | Yes | Create project |
| `POST` | `/profiles` | Yes | Create verification profile |
| `POST` | `/releases` | Yes | Create release |
| `POST` | `/releases/{id}/verify` | Yes | Launch verification |
| `GET` | `/releases/{id}/results` | Yes | Get results |
| `POST` | `/organizations/{id}/connectors` | Yes | Register connector |
| `GET` | `/health` | No | Health check |

---

# 15. Running the system

## Local development (with Docker)

```bash
git clone https://github.com/adrianmfuentes/svaes.git
cd svaes
docker compose up --build
```

Docker Compose starts: API at `http://localhost:8000`, Swagger at `http://localhost:8000/docs`, PostgreSQL at `localhost:5432`.

## Local development (without Docker)

```bash
# Only the database
docker compose up postgres -d

cd apps/api
uv sync
uv run uvicorn src.main:app --reload --port 8000
```

## Production

```bash
export DATABASE_URL="postgresql+psycopg://user:pass@host:5432/svaes"
export JWT_SECRET_KEY="long-random-secure-key"
export ENCRYPTION_KEY="$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")"
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

---

# 16. Conclusion

The system provides a decoupled, extensible, and robust solution for automatic software delivery verification.

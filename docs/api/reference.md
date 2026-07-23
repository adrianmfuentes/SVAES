# Backend API Reference

Domain model, endpoints, and cross-cutting concerns for the FastAPI backend (`api/`).

For live, always-accurate request/response schemas, use the interactive Swagger UI at `http://localhost:8000/docs` — the tables below are a map, not a replacement for it.

## Contents
1. [Architecture](#1-architecture)
2. [Domain Entities](#2-domain-entities)
3. [Enums](#3-enums)
4. [Endpoints by Router](#4-endpoints-by-router)
5. [Authentication & Authorization](#5-authentication--authorization)
6. [Multi-Tenancy](#6-multi-tenancy)
7. [Rate Limiting](#7-rate-limiting)
8. [Audit Logging](#8-audit-logging)

---

## 1. Architecture

Hexagonal (Ports & Adapters) + Clean Architecture — dependencies only point inward, toward the domain.

```
api/src/
├── domain/            # Entities, enums, exceptions — no external dependencies
├── application/
│   ├── ports/
│   │   ├── input/      # Service interfaces (use case contracts)
│   │   └── output/     # Repository & external service interfaces
│   └── use_cases/      # Business logic implementations
├── infrastructure/
│   ├── primary/
│   │   ├── middleware/  # JWT handler, password hasher
│   │   └── routers/     # FastAPI route handlers (v1)
│   └── secondary/
│       ├── database/    # SQLAlchemy models + repositories
│       ├── connectors/  # External system connectors
│       └── queue/       # Celery task queue
└── main.py             # FastAPI entry point
```

Persistence is PostgreSQL: UUID primary keys throughout, `JSONB` for dynamic fields (`params`, `metadata`, `rule_results`, ...). Every table below maps 1:1 to its entity — same fields, no separate schema to track.

---

## 2. Domain Entities

### User
```python
id: UUID
email: str (unique, indexed)
hashed_password: str
display_name: str
role: UserRole
is_active: bool = True
failed_login_attempts: int = 0
locked_until: Optional[datetime] = None
created_at: datetime
updated_at: datetime
```

### UserMembership (N:M — user ↔ organization, unique on the pair)
```python
id: UUID
user_id: UUID (FK → user.id)
organization_id: UUID (FK → organization.id)
role: UserRole
joined_at: datetime
```

### Organization
```python
id: UUID
name: str
slug: str (unique, indexed)
owner_id: Optional[UUID] (FK → user.id)
is_active: bool = True
created_at: datetime
updated_at: datetime
```

### Project
```python
id: UUID
organization_id: UUID (FK → organization.id)
name: str
description: str
profile_id: UUID (FK → verification_profile.id)
is_archived: bool = False
created_at: datetime
updated_at: datetime
```

### Release (unique on `project_id` + `version`)
```python
id: UUID
project_id: UUID (FK → project.id)
profile_id: UUID (FK → verification_profile.id)
version: str (SemVer 2.0.0)
created_by: UUID (FK → user.id)
description: str = ""
status: ReleaseStatus = ReleaseStatus.BORRADOR
artifacts: list = []
created_at: datetime
updated_at: datetime
```

### ConnectorInstance
```python
id: UUID
organization_id: UUID (FK → organization.id)
connector_type: ConnectorType
connector_implementation: ConnectorImplementation
name: str
encrypted_credentials: bytes (Fernet AES-128-CBC)
status: ConnectorStatus = ConnectorStatus.INACTIVO
created_at: datetime
updated_at: datetime
last_tested_at: Optional[datetime] = None
```

### VerificationProfile
```python
id: UUID
organization_id: UUID (FK → organization.id)
name: str
description: str = ""
is_default: bool = False
created_at: datetime
updated_at: datetime
```

Rules relate to a profile 1:N via the `VerificationRule` table below — not embedded as JSON on the profile.

### VerificationRule
```python
id: UUID
profile_id: UUID (FK → verification_profile.id)
rule_template: str
severity: SeverityType = SeverityType.HIGH
params: dict = {}
connector_instance_id: Optional[UUID] (FK → connector_instance.id)
display_order: int = 0
is_active: bool = True
created_at: datetime
```

### VerificationResult
```python
id: UUID
release_id: UUID (FK → release.id)
verdict: VerdictType
rule_results: list = []
summary: dict = {}
profile_snapshot: dict = {}
duration_ms: int = 0
executed_at: datetime
```

### Artifact
```python
id: UUID
release_id: UUID (FK → release.id)
connector_instance_id: UUID (FK → connector_instance.id)
connector_implementation: str
artifact_type: ArtifactType
external_ref: str
metadata: dict = {}
created_at: datetime
```

### APIKey
Programmatic access for CI/CD and scripts — up to 5 active per user. Format `svk_<32 random chars>`; only the SHA-256 hash and a 12-char prefix are stored, the full key is shown once at creation, and it can be revoked instantly.
```python
id: UUID
user_id: UUID (FK → user.id)
organization_id: UUID (FK → organization.id)
name: str
key_hash: str (SHA-256, unique)
prefix: str
is_active: bool = True
created_at: datetime
expires_at: Optional[datetime] = None
last_used_at: Optional[datetime] = None
```

### CustomRole
```python
id: UUID
organization_id: UUID (FK → organization.id)
name: str
permissions: List[Permission]
is_active: bool = True
created_at: datetime
updated_at: datetime
```

### Relationships
```
Organization ──< UserMembership >── User
     ├──< Project ──< Release ──< Artifact
     │                       └──< VerificationResult
     ├──< ConnectorInstance
     ├──< VerificationProfile ──< VerificationRule
     ├──< APIKey (owned by User, scoped to Organization)
     └──< CustomRole
```

---

## 3. Enums

| Enum | Values |
|---|---|
| `UserRole` | `U2` Standard User · `U3` Global Admin · `U4` Org Manager |
| `ReleaseStatus` | `BORRADOR → PENDIENTE → EN_VERIFICACION → {VALIDA, NO_VALIDA, CON_ADVERTENCIAS} → ARCHIVADA` (any terminal state can go back to `PENDIENTE` to re-verify) |
| `ConnectorStatus` | `ACTIVO` · `INACTIVO` · `ERROR` |
| `ConnectorType` | `GESTOR_TAREAS` · `REPO_CODIGO` · `SISTEMA_DOCUMENTAL` · `HERRAMIENTA_PLANIFICACION` · `GESTION_CAMBIOS` |
| `ConnectorImplementation` | see table in [§4.5 Connectors](#45-connectors--apiv1organizationsorg_idconnectors) |
| `ArtifactType` | `TAREA` · `CODIGO` · `DOCUMENTO` |
| `VerdictType` | `VALID` · `VALID_WITH_WARNINGS` · `INVALID` |
| `SeverityType` | `INFO` · `LOW` · `MEDIUM` · `HIGH` · `CRITICAL` |
| `TaskStatus` (Celery) | `PENDING` · `STARTED` · `SUCCESS` · `FAILURE` · `RETRY` · `REVOKED` |

`Permission` is a flat string enum (`VIEW_DASHBOARD`, `CREATE_RELEASE`, `MANAGE_CONNECTORS`, `MANAGE_ROLES`, ...) — see [§5 Authorization](#5-authentication--authorization) for how roles map to permissions.

---

## 4. Endpoints by Router

Base URL: `/api/v1`. "Permission" is a named `Permission` from §3; "Org access" means the caller must belong to the target organization; U3 bypasses all org-scoped checks.

### 4.1 Auth (`/auth`)
| Method | Route | Auth |
|---|---|---|
| POST | `/auth/login` | No (30/min) |
| POST | `/auth/refresh` | No (30/min) |

### 4.2 Users (`/users`, `/organizations/{org_id}/users`, `/admin/users`)
| Method | Route | Permission |
|---|---|---|
| GET | `/users/me` | Yes |
| PATCH | `/users/me` | Yes |
| POST | `/users/me/password` | Yes |
| GET | `/organizations/{org_id}/users` | MANAGE_ROLES |
| POST | `/organizations/{org_id}/users/invite` | INVITE_USERS |
| PATCH | `/organizations/{org_id}/users/{user_id}/role` | MANAGE_ROLES |
| DELETE | `/organizations/{org_id}/users/{user_id}` | MANAGE_ROLES |
| POST / GET | `/admin/users` | U3 |
| PATCH | `/admin/users/{user_id}/activate`, `/deactivate`, `/role` | U3 |

### 4.3 Organizations (`/organizations`)
| Method | Route | Permission |
|---|---|---|
| GET / POST | `/organizations` | U3 |
| GET | `/organizations/{org_id}` | Org access |
| GET | `/projects` | Yes (filtered by access) |
| POST | `/organizations/{org_id}/projects` | CREATE_PROJECT |
| POST | `/organizations/{org_id}/projects/{project_id}/archive` | ARCHIVE_PROJECT |
| POST | `/organizations/{org_id}/transfer-ownership` | TRANSFER_OWNERSHIP |
| POST | `/organizations/{org_id}/restore` | U3 |

Archived projects (and their releases) become read-only; there is no hard delete.

### 4.4 Projects & Releases (`/projects`, `/releases`)
| Method | Route | Permission |
|---|---|---|
| GET / PATCH | `/projects/{project_id}` | VIEW_ORG_PROJECTS / UPDATE_PROJECT |
| POST | `/projects/{project_id}/releases` | CREATE_RELEASE |
| GET | `/projects/{project_id}/releases` | VIEW_ORG_PROJECTS |
| GET / PATCH | `/releases/{release_id}` | VIEW_ORG_PROJECTS / UPDATE_OWN_RELEASES |
| DELETE | `/releases/{release_id}` (only in `BORRADOR`/`PENDIENTE`, no verifications yet) | UPDATE_OWN_RELEASES |
| POST | `/releases/{release_id}/archive` | ARCHIVE_RELEASE |
| POST | `/releases/{release_id}/restore` | U3 (reserved) |
| GET / POST | `/releases/{release_id}/artifacts` | VIEW_ORG_PROJECTS / UPDATE_OWN_RELEASES |
| DELETE | `/releases/{release_id}/artifacts/{artifact_id}` | UPDATE_OWN_RELEASES |
| POST | `/releases/{release_id}/artifacts/import` | UPDATE_OWN_RELEASES |
| POST | `/releases/{release_id}/verify` (async, dispatches to Celery) | EXECUTE_VERIFICATION |
| GET | `/releases/{release_id}/results`, `/results/{result_id}` | VIEW_OWN_HISTORY |
| GET | `/releases/{release_id}/results/{result_id}/export?format=pdf` | VIEW_OWN_HISTORY |
| GET | `/projects/{project_id}/results/export?format=csv` | VIEW_ORG_PROJECTS |

### 4.5 Connectors (`/organizations/{org_id}/connectors`)
| Method | Route | Permission |
|---|---|---|
| GET | `/connectors/types` | Yes |
| GET | `/organizations/{org_id}/connectors` | Org access |
| POST / PATCH / DELETE | `/organizations/{org_id}/connectors/{connector_id}` | MANAGE_CONNECTORS |
| POST | `/organizations/{org_id}/connectors/{connector_id}/test` | MANAGE_CONNECTORS |

20 implementations across 5 types:

| Type | Implementations |
|---|---|
| GESTOR_TAREAS | Jira, Linear, Trello, Asana, ClickUp, Taiga, Plane |
| REPO_CODIGO | GitLab, GitHub, Bitbucket, Gitea |
| SISTEMA_DOCUMENTAL | Confluence, Notion, Wiki.js, BookStack |
| HERRAMIENTA_PLANIFICACION | Miro |
| GESTION_CAMBIOS | Jira Service Management, GLPI, Zammad, Redmine |

### 4.6 Profiles & Rules (`/profiles`, `/rules`)
| Method | Route | Permission |
|---|---|---|
| GET / POST | `/organizations/{org_id}/profiles` | Org access |
| PATCH / DELETE | `/profiles/{profile_id}` | MANAGE_PROFILES |
| POST | `/profiles/{profile_id}/rules` | MANAGE_RULES |
| PATCH / DELETE | `/rules/{rule_id}` | MANAGE_RULES |

### 4.7 Other routers
| Router | Base path | Notes |
|---|---|---|
| Tasks | `/tasks/{task_id}` | Poll Celery job status |
| Custom Roles | `/organizations/{org_id}/roles`, `/roles/{role_id}` | MANAGE_ROLES |
| Dashboard | `/dashboard/metrics?org_id=` | Aggregate release/verification counts |
| API Keys | `/users/{user_id}/api-keys` | Own-user only, max 5 active |
| Templates | `/templates` | Release templates; create/update/archive/clone need MANAGE_PROFILES |
| Notifications | `/notifications/channels`, `/preferences`, `/subscriptions` | EMAIL/SLACK/MS_TEAMS channels |
| Admin | `/admin/rules/reload` | U3 only — hot-reloads custom rules |

---

## 5. Authentication & Authorization

**Login flow:** `POST /auth/login` validates credentials with bcrypt and returns an access token (15 min) and refresh token (30 days). JWT claims: `sub` (user id), `role`, `email`, `organization_id`, `iat`, `exp`. Protected endpoints require `Authorization: Bearer <token>`.

**Lockout:** 5 failed logins locks the account for 15 minutes (HTTP 429), tracked via `failed_login_attempts` / `locked_until`.

**RBAC:**

| Role | Permissions |
|---|---|
| U2 Standard | VIEW_DASHBOARD, VIEW_ORG_PROJECTS, CREATE_RELEASE, UPDATE_OWN_RELEASES, ARCHIVE_RELEASE, EXECUTE_VERIFICATION, VIEW_OWN_HISTORY, MANAGE_OWN_API_KEYS |
| U4 Org Manager | U2 + CREATE_PROJECT, UPDATE_PROJECT, ARCHIVE_PROJECT, MANAGE_CONNECTORS, MANAGE_PROFILES, MANAGE_RULES, VIEW_ORG_DASHBOARD, INVITE_USERS, MANAGE_ROLES |
| U3 Global Admin | All permissions |

There is no `DELETE_PROJECT` permission — projects are archived, never hard-deleted. Custom roles (§4.6/§4.7) grant a chosen subset of `Permission` values per organization.

Production responses also carry standard hardening headers (`X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`, `Referrer-Policy`, `X-XSS-Protection`).

---

## 6. Multi-Tenancy

Users join organizations through `UserMembership` (N:M) and act within the org carried in their JWT `organization_id` claim; U3 users bypass tenant scoping entirely. Every query is filtered by organization membership, and cross-tenant access fails closed. API keys belong to a user (not directly to an org) but are scoped to that user's organization, and each user can only see their own keys.

---

## 7. Rate Limiting

| Endpoint type | Limit |
|---|---|
| Auth (`/auth/*`) | 30 req/min |
| Search endpoints | 30 req/min |
| Default endpoints | 100 req/min |
| Connector test | 100 req/min |

The 30/min auth limit sits comfortably under the 5-attempts-in-10-minutes lockout threshold so the two don't fight each other.

---

## 8. Audit Logging

Every sensitive write (login, connector/profile/rule/role CRUD, release lifecycle transitions, ownership transfers, API key issuance/revocation, ...) is persisted to the `audit_log` table with actor, timestamp, and outcome — 25 distinct event types in total. See [Security & Compliance Audit](../security/audit.md) for the GDPR context behind this.

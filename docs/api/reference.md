# SVAES Backend API Documentation

## Table of Contents
1. [Architecture](#architecture)
2. [Domain Entities](#domain-entities)
3. [Enums](#enums)
4. [Database Models](#database-models)
5. [API Endpoints by Router](#api-endpoints-by-router)
6. [Authentication and Authorization](#authentication-and-authorization)
7. [Multi-Tenancy](#multi-tenancy)
8. [Rate Limiting](#rate-limiting)
9. [Audit Logging](#audit-logging)

---

## 1. Architecture

### Hexagonal Architecture (Ports & Adapters)

```
┌─────────────────────────────────────────────────────────────────────┐
│                       PRIMARY ADAPTERS (API)                        │
│         FastAPI Routers → Use Cases (Input Ports) → DTOs            │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      APPLICATION LAYER                              │
│  Input Ports (Interfaces) → Use Cases (Services)                    │
│     - IReleaseService, IUserService, IAuthService, etc.             │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        DOMAIN LAYER                                 │
│  Entities: User, Organization, Project, Release, Connector, etc.    │
│  Enums: UserRole, ReleaseStatus, ConnectorType, Permission, etc.   │
│  Exceptions: DomainException hierarchy                              │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      SECONDARY ADAPTERS                             │
│  Output Ports (Interfaces) → Repositories, Task Queue, Connectors    │
│     - SQLAlchemy Models, Celery Task Queue, External Connectors     │
└─────────────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
api/src/
├── application/
│   ├── ports/
│   │   ├── input/      # Service interfaces (use case contracts)
│   │   └── output/     # Repository & external service interfaces
│   └── use_cases/
│       ├── main/       # Core business use cases
│       └── others/     # Supporting use cases
├── core/
│   ├── audit.py        # Audit logging
│   ├── config.py       # Configuration management
│   ├── dependencies.py # FastAPI dependency injection
│   ├── rate_limit.py   # Rate limiting configuration
│   └── ...
├── domain/
│   ├── entities/       # Domain models (User, Organization, etc.)
│   ├── enums.py        # Enumerations
│   └── exceptions.py   # Domain exceptions
├── infrastructure/
│   ├── primary/
│   │   ├── middleware/    # JWT handler, password hasher
│   │   └── routers/       # FastAPI route handlers
│   └── secondary/
│       ├── database/
│       │   ├── models/    # SQLAlchemy ORM models
│       │   └── repositories/ # Repository implementations
│       ├── connectors/    # External system connectors
│       └── queue/         # Celery task queue
└── main.py             # FastAPI application entry point
```

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
organization_ids: List[UUID] = []  # User can belong to multiple organizations
```

### UserMembership (N:M Intermediate Table)
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
is_archived: bool = False  # indica si el proyecto está archivado
created_at: datetime
updated_at: datetime
```

### Release
```python
id: UUID
project_id: UUID (FK → projects.id)
profile_id: UUID (FK → verification_profile.id)
version: str (SemVer 2.0.0)
created_by: UUID (FK → user.id)
description: str = ""
status: ReleaseStatus = ReleaseStatus.BORRADOR
artifacts: list = field(default_factory=list)
created_at: datetime
updated_at: datetime

# Unique constraint: (project_id, version)
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

### VerificationRule
```python
id: UUID
profile_id: UUID (FK → verification_profile.id)
rule_template: str
severity: SeverityType = SeverityType.HIGH
params: dict = field(default_factory=dict)
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
rule_results: list = field(default_factory=list)
summary: dict = field(default_factory=dict)
profile_snapshot: dict = field(default_factory=dict)
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
metadata: dict = field(default_factory=dict)
created_at: datetime
```

### APIKey
```python
id: UUID
user_id: UUID (FK → user.id)  # clave foránea al usuario propietario
organization_id: UUID (FK → organization.id)
name: str
key_hash: str (SHA-256, unique)
prefix: str (first 12 chars of raw key, for display)
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

### Entity Relationships

```
Organization (1) ─────< UserMembership >───── User
     │
     ├────< Project
     │         │
     │         └────< Release
     │                   │
     │                   ├────< Artifact
     │                   │
     │                   └────< VerificationResult
     │
     ├────< ConnectorInstance
     │
     ├────< VerificationProfile
     │         │
     │         └────< VerificationRule
     │
     ├────< APIKey (belongs to User, scoped to Organization)
     │
     └────< CustomRole
```

---

## 3. Enums

### UserRole
```python
U2 = "U2"  # Standard User - usuario regular con acceso a proyectos
U3 = "U3"  # Global Administrator - administrador del sistema
U4 = "U4"  # Organization Manager - gerente a nivel de organización
```

### Permission
```python
VIEW_DASHBOARD = "VIEW_DASHBOARD"
VIEW_OWN_PROJECTS = "VIEW_OWN_PROJECTS"
CREATE_RELEASE = "CREATE_RELEASE"
UPDATE_OWN_RELEASES = "UPDATE_OWN_RELEASES"
ARCHIVE_RELEASE = "ARCHIVE_RELEASE"
EXECUTE_VERIFICATION = "EXECUTE_VERIFICATION"
VIEW_OWN_HISTORY = "VIEW_OWN_HISTORY"
MANAGE_OWN_API_KEYS = "MANAGE_OWN_API_KEYS"
VIEW_ORG_PROJECTS = "VIEW_ORG_PROJECTS"
CREATE_PROJECT = "CREATE_PROJECT"
UPDATE_PROJECT = "UPDATE_PROJECT"
ARCHIVE_PROJECT = "ARCHIVE_PROJECT"  # permiso para archivar proyectos
MANAGE_CONNECTORS = "MANAGE_CONNECTORS"
MANAGE_PROFILES = "MANAGE_PROFILES"
MANAGE_RULES = "MANAGE_RULES"
VIEW_ORG_DASHBOARD = "VIEW_ORG_DASHBOARD"
INVITE_USERS = "INVITE_USERS"
MANAGE_ROLES = "MANAGE_ROLES"
TRANSFER_OWNERSHIP = "TRANSFER_OWNERSHIP"
MANAGE_ORGANIZATIONS = "MANAGE_ORGANIZATIONS"
MANAGE_ALL_USERS = "MANAGE_ALL_USERS"
```

### ReleaseStatus (State Machine)
```python
BORRADOR = "BORRADOR"           # Borrador
PENDIENTE = "PENDIENTE"          # Pendiente
EN_VERIFICACION = "EN_VERIFICACION"  # En verificación
VALIDA = "VALIDA"                # Válida
CON_ADVERTENCIAS = "CON_ADVERTENCIAS"  # Válida con advertencias
NO_VALIDA = "NO_VALIDA"          # No válida
ARCHIVADA = "ARCHIVADA"          # Archivada

# Transiciones de estado:
# BORRADOR → PENDIENTE
# PENDIENTE → EN_VERIFICACION
# EN_VERIFICACION → VALIDA | NO_VALIDA | CON_ADVERTENCIAS
# VALIDA | NO_VALIDA | CON_ADVERTENCIAS → ARCHIVADA
# VALIDA | NO_VALIDA | CON_ADVERTENCIAS → PENDIENTE (re-verificar)
```

### ConnectorStatus
```python
ACTIVO = "ACTIVO"
INACTIVO = "INACTIVO"
ERROR = "ERROR"
```

### ConnectorType
```python
GESTOR_TAREAS = "GESTOR_TAREAS"              # Gestor de tareas
REPO_CODIGO = "REPO_CODIGO"                  # Repositorio de código
SISTEMA_DOCUMENTAL = "SISTEMA_DOCUMENTAL"    # Sistema documental
HERRAMIENTA_PLANIFICACION = "HERRAMIENTA_PLANIFICACION"  # Herramienta de planificación
GESTION_CAMBIOS = "GESTION_CAMBIOS"          # Gestión de cambios
```

### ConnectorImplementation
```python
GESTOR_TAREAS: JIRA, LINEAR, TRELLO, ASANA, CLICKUP, TAIGA, PLANE
REPO_CODIGO: GITLAB, GITHUB, BITBUCKET, GITEA
SISTEMA_DOCUMENTAL: CONFLUENCE, NOTION, WIKIJS, BOOKSTACK
HERRAMIENTA_PLANIFICACION: MIRO
GESTION_CAMBIOS: JIRA_SM, GLPI, ZAMMAD, REDMINE
```

### ArtifactType
```python
TAREA = "TAREA"      # Tarea
CODIGO = "CODIGO"    # Código
DOCUMENTO = "DOCUMENTO"  # Documento
```

### VerdictType
```python
VALID = "VALID"
VALID_WITH_WARNINGS = "VALID_WITH_WARNINGS"
INVALID = "INVALID"
```

### SeverityType
```python
INFO = "INFO"
LOW = "LOW"
MEDIUM = "MEDIUM"
HIGH = "HIGH"
CRITICAL = "CRITICAL"
```

### TaskStatus
```python
PENDING = "PENDING"
STARTED = "STARTED"
SUCCESS = "SUCCESS"
FAILURE = "FAILURE"
RETRY = "RETRY"
REVOKED = "REVOKED"
```

---

## 4. Database Models

### Table: user
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default=uuid4 |
| email | VARCHAR(255) | UNIQUE, NOT NULL, INDEX |
| hashed_password | VARCHAR(255) | NOT NULL |
| display_name | VARCHAR(100) | NOT NULL |
| role | VARCHAR(20) | NOT NULL, default=U2 |
| is_active | BOOLEAN | NOT NULL, default=True |
| failed_login_attempts | INTEGER | NOT NULL, default=0 |
| locked_until | TIMESTAMP | NULLABLE |
| created_at | TIMESTAMP | NOT NULL |
| updated_at | TIMESTAMP | NOT NULL |

### Table: user_membership (N:M Intermediate Table)
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default=uuid4 |
| user_id | UUID | FK → user.id, NOT NULL |
| organization_id | UUID | FK → organization.id, NOT NULL |
| role | VARCHAR(20) | NOT NULL, default=U2 |
| joined_at | TIMESTAMP | NOT NULL |

**Unique constraint:** (user_id, organization_id)

### Table: organization
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default=uuid4 |
| name | VARCHAR(100) | NOT NULL |
| slug | VARCHAR(100) | UNIQUE, NOT NULL, INDEX |
| owner_id | UUID | FK → user.id, NULLABLE |
| is_active | BOOLEAN | NOT NULL, default=True |
| created_at | TIMESTAMP | NOT NULL |
| updated_at | TIMESTAMP | NOT NULL |

### Table: project
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default=uuid4 |
| name | VARCHAR(100) | NOT NULL |
| description | TEXT | NULLABLE |
| organization_id | UUID | FK → organization.id, NOT NULL |
| profile_id | UUID | FK → verification_profile.id, NOT NULL |
| is_archived | BOOLEAN | NOT NULL, default=False |
| created_at | TIMESTAMP | NOT NULL |
| updated_at | TIMESTAMP | NOT NULL |

### Table: release
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default=uuid4 |
| project_id | UUID | FK → project.id, NOT NULL |
| profile_id | UUID | FK → verification_profile.id, NULLABLE |
| version | VARCHAR(50) | NOT NULL |
| status | VARCHAR(20) | NOT NULL, default=BORRADOR |
| description | VARCHAR(1000) | NULLABLE |
| name | VARCHAR(100) | NOT NULL |
| created_by | UUID | FK → user.id, NULLABLE |
| created_at | TIMESTAMP | NOT NULL |
| updated_at | TIMESTAMP | NOT NULL |
| **UNIQUE** | (project_id, version) | uq_release_project_version |

### Table: connector_instance
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default=uuid4 |
| organization_id | UUID | FK → organization.id, NOT NULL |
| connector_type | VARCHAR(50) | NOT NULL |
| connector_implementation | VARCHAR(50) | NOT NULL |
| name | VARCHAR(100) | NOT NULL |
| encrypted_credentials | BYTEA | NOT NULL |
| status | VARCHAR(20) | NOT NULL, default=INACTIVO |
| created_at | TIMESTAMP | NOT NULL |
| updated_at | TIMESTAMP | NOT NULL |
| last_tested_at | TIMESTAMP | NULLABLE |

### Table: verification_profile
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default=uuid4 |
| organization_id | UUID | FK → organization.id, NOT NULL |
| name | VARCHAR(100) | NOT NULL |
| description | VARCHAR(500) | NULLABLE |
| is_default | BOOLEAN | NOT NULL, default=False |
| created_at | TIMESTAMP | NOT NULL |
| updated_at | TIMESTAMP | NOT NULL |

**Note:** Verification rules relate to the profile through the `verification_rule` table (1:N relationship), following the TFG's relational design. They are not stored as a JSON column in `verification_profile`.

### Table: verification_rule
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default=uuid4 |
| profile_id | UUID | FK → verification_profile.id, NOT NULL |
| rule_template | VARCHAR(100) | NOT NULL |
| severity | VARCHAR(20) | NOT NULL, default=HIGH |
| params | JSONB | NULLABLE, default=dict |
| connector_instance_id | UUID | FK → connector_instance.id, NULLABLE |
| display_order | INTEGER | NOT NULL, default=0 |
| is_active | BOOLEAN | NOT NULL, default=True |
| created_at | TIMESTAMP | NOT NULL |

### Table: verification_result
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default=uuid4 |
| release_id | UUID | FK → release.id, NOT NULL |
| verdict | VARCHAR(30) | NOT NULL, default=INVALID |
| duration_ms | INTEGER | NOT NULL, default=0 |
| summary | JSONB | NULLABLE, default=dict |
| rule_results | JSONB | NULLABLE, default=list |
| profile_snapshot | JSONB | NULLABLE, default=dict |
| executed_at | TIMESTAMP | NOT NULL |

**Note:** PostgreSQL's native `JSONB` type is used instead of `JSON` to enable GIN indexes and efficient searches over dynamic content, in line with the TFG's architectural decision.

### Table: artifact
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default=uuid4 |
| release_id | UUID | FK → release.id, NOT NULL |
| connector_instance_id | UUID | FK → connector_instance.id, NOT NULL |
| connector_implementation | VARCHAR(50) | NOT NULL |
| artifact_type | VARCHAR(20) | NOT NULL, default=TAREA |
| external_ref | VARCHAR(500) | NOT NULL |
| metadata | JSONB | NULLABLE, default=dict |
| created_at | TIMESTAMP | NOT NULL |

### Table: api_key
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default=uuid4 |
| user_id | UUID | FK → user.id, NOT NULL |
| organization_id | UUID | FK → organization.id, NOT NULL |
| name | VARCHAR(100) | NOT NULL |
| key_hash | VARCHAR(256) | NOT NULL, UNIQUE |
| prefix | VARCHAR(20) | NOT NULL |
| is_active | BOOLEAN | NOT NULL, default=True |
| expires_at | TIMESTAMP | NULLABLE |
| created_at | TIMESTAMP | NOT NULL |
| last_used_at | TIMESTAMP | NULLABLE |

### Table: custom_role
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default=uuid4 |
| organization_id | UUID | FK → organization.id, NOT NULL |
| name | VARCHAR(100) | NOT NULL |
| permissions | ARRAY(VARCHAR) | NOT NULL |
| is_active | BOOLEAN | NOT NULL, default=True |
| created_at | TIMESTAMP | NOT NULL |
| updated_at | TIMESTAMP | NOT NULL |

---

## 5. API Endpoints by Router

### 5.1 Auth Router (`/api/v1/auth`)

| Method | Route | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/v1/auth/login` | Authenticate user with email/password | No (Rate: 30/min) |
| POST | `/api/v1/auth/refresh` | Refresh access token | No (Rate: 30/min) |

**Login Request:**
```json
{
  "email": "string (1-255)",
  "password": "string (1-255)"
}
```

**Login Response:**
```json
{
  "access_token": "string (JWT, 15 min lifetime)",
  "refresh_token": "string (JWT, 30 days lifetime)",
  "token_type": "Bearer",
  "user_id": "uuid",
  "role": "U1|U2|U3|U4"
}
```

---

### 5.2 Users Router (`/api/v1/users`, `/api/v1/organizations/{org_id}/users`)

| Method | Route | Description | Permission |
|--------|------|-------------|---------|
| GET | `/api/v1/users/me` | Get current user profile | Yes |
| PATCH | `/api/v1/users/me` | Update current user display name | Yes |
| POST | `/api/v1/users/me/password` | Change current user password | Yes |
| GET | `/api/v1/organizations/{org_id}/users` | List organization users | MANAGE_ROLES |
| POST | `/api/v1/organizations/{org_id}/users/invite` | Invite user to organization | INVITE_USERS |
| PATCH | `/api/v1/organizations/{org_id}/users/{user_id}/role` | Update user role in org | MANAGE_ROLES |
| DELETE | `/api/v1/organizations/{org_id}/users/{user_id}` | Remove user from organization | MANAGE_ROLES |
| POST | `/api/v1/admin/users` | Create user globally (U3 only) | U3 |
| GET | `/api/v1/admin/users` | List all users with filters (U3 only) | U3 |
| PATCH | `/api/v1/admin/users/{user_id}/activate` | Activate user account (U3 only) | U3 |
| PATCH | `/api/v1/admin/users/{user_id}/deactivate` | Deactivate user account (U3 only) | U3 |
| PATCH | `/api/v1/admin/users/{user_id}/role` | Update user global role (U3 only) | U3 |

**UserUpdateRequest:**
```json
{
  "display_name": "string (1-100 chars)"
}
```

**PasswordChangeRequest:**
```json
{
  "current_password": "string (1-255 chars)",
  "new_password": "string (8-255 chars)",
  "confirm_password": "string (8-255 chars)"
}
```

**UserInviteRequest:**
```json
{
  "email": "string (1-255 chars, email format)",
  "role": "U1|U2|U4"
}
```

**RoleUpdateRequest:**
```json
{
  "role": "U1|U2|U4"
}
```

**AdminCreateUserRequest:**
```json
{
  "email": "string (1-255 chars, email format)",
  "password": "string (8-255 chars)",
  "display_name": "string (1-100 chars)",
  "role": "U1|U2|U3|U4"
}
```

---

### 5.3 Organizations Router (`/api/v1/organizations`)

| Method | Route | Description | Permission |
|--------|------|-------------|---------|
| GET | `/api/v1/organizations` | List all organizations | U3 |
| POST | `/api/v1/organizations` | Create new organization | U3 |
| GET | `/api/v1/organizations/{org_id}` | Get organization details | Org access |
| GET | `/api/v1/projects` | List accessible projects (global, filtered by user access) | Yes |
| POST | `/api/v1/organizations/{org_id}/projects` | Create project in organization | CREATE_PROJECT |
| POST | `/api/v1/organizations/{org_id}/projects/{project_id}/archive` | Archive project | ARCHIVE_PROJECT |
| POST | `/api/v1/organizations/{org_id}/transfer-ownership` | Transfer org ownership | TRANSFER_OWNERSHIP |
| POST | `/api/v1/organizations/{org_id}/restore` | Restore (unarchive) organization | U3 |

**Note:** Archived projects become read-only (their releases too).

**OrganizationCreateRequest:**
```json
{
  "name": "string (1-100 chars)",
  "slug": "string (1-100 chars, URL-safe)"
}
```

**OrganizationResponse:**
```json
{
  "id": "uuid",
  "name": "string",
  "slug": "string",
  "owner_id": "uuid|null",
  "is_active": "boolean",
  "created_at": "datetime (ISO 8601)",
  "updated_at": "datetime (ISO 8601)"
}
```

**Query Parameters (GET `/api/v1/projects`):**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number (GR2.2) |
| `size` | integer | 25 | Items per page, max 100 (GR2.2) |
| `status` | string | --- | Filter by status (ACTIVO, ARCHIVADO) |
| `search` | string | --- | Search by name |
| `org_id` | uuid | --- | Filter by organization |

---

### 5.4 Projects Router (`/api/v1/projects/{project_id}`)

| Method | Route | Description | Permission |
|--------|------|-------------|---------|
| GET | `/api/v1/projects/{project_id}` | Get project details | VIEW_ORG_PROJECTS |
| PATCH | `/api/v1/projects/{project_id}` | Update project | UPDATE_PROJECT |

**Note:** Physical deletion of projects is not allowed. Use the archive endpoint instead.

**ProjectCreateRequest:**
```json
{
  "name": "string (1-100 chars)",
  "description": "string|null (max 1000 chars)",
  "profile_id": "uuid"
}
```

**ProjectUpdateRequest:**
```json
{
  "name": "string|null (1-100 chars)",
  "description": "string|null (max 1000 chars)",
  "profile_id": "uuid|null"
}
```

---

### 5.5 Releases Router (`/api/v1/projects/{project_id}/releases`, `/api/v1/releases/{release_id}`)

| Method | Route | Description | Permission |
|--------|------|-------------|---------|
| POST | `/api/v1/projects/{project_id}/releases` | Create release in project | CREATE_RELEASE |
| GET | `/api/v1/projects/{project_id}/releases` | List project releases | VIEW_ORG_PROJECTS |
| GET | `/api/v1/releases/{release_id}` | Get release details | VIEW_ORG_PROJECTS |
| PATCH | `/api/v1/releases/{release_id}` | Update release | UPDATE_OWN_RELEASES |
| DELETE | `/api/v1/releases/{release_id}` | Delete release (Only in BORRADOR or PENDIENTE status and without verifications) | UPDATE_OWN_RELEASES |
| POST | `/api/v1/releases/{release_id}/archive` | Archive release | ARCHIVE_RELEASE |
| POST | `/api/v1/releases/{release_id}/restore` | Restore archived release | U3 (reserved) |
| GET | `/api/v1/releases/{release_id}/artifacts` | List release artifacts | VIEW_ORG_PROJECTS |
| POST | `/api/v1/releases/{release_id}/artifacts` | Add artifact to release | UPDATE_OWN_RELEASES |
| DELETE | `/api/v1/releases/{release_id}/artifacts/{artifact_id}` | Delete artifact | UPDATE_OWN_RELEASES |
| POST | `/api/v1/releases/{release_id}/artifacts/import` | Import artifacts (JSON array) | UPDATE_OWN_RELEASES |
| POST | `/api/v1/releases/{release_id}/verify` | Launch verification (async) | EXECUTE_VERIFICATION |
| GET | `/api/v1/releases/{release_id}/results` | Get verification history | VIEW_OWN_HISTORY |
| GET | `/api/v1/releases/{release_id}/results/{result_id}` | Get verification detail | VIEW_OWN_HISTORY |
| GET | `/api/v1/releases/{release_id}/results/{result_id}/export?format=pdf` | Export verification to PDF | VIEW_OWN_HISTORY |
| GET | `/api/v1/projects/{project_id}/results/export?format=csv` | Export project history to CSV | VIEW_ORG_PROJECTS |

**Release State Machine:**
```
BORRADOR → PENDIENTE → EN_VERIFICACION → VALIDA
                           ↓                ↓
                     NO_VALIDA       CON_ADVERTENCIAS
                           ↓                ↓
                          ARCHIVADA ←←←←←←←←←←←←←←←
```

**ReleaseCreateRequest:**
```json
{
  "name": "string (1-100 chars)",
  "version": "string (SemVer 2.0.0)",
  "description": "string|null (max 1000 chars)",
  "profile_id": "uuid|null"
}
```

**ReleaseUpdateRequest:**
```json
{
  "name": "string|null (1-100 chars)",
  "description": "string|null (max 1000 chars)",
  "status": "BORRADOR|PENDIENTE|null"
}
```

**ArtifactCreateRequest:**
```json
{
  "connector_instance_id": "uuid",
  "connector_implementation": "string (50 chars, e.g.: JIRA, GITLAB)",
  "artifact_type": "TAREA|CODIGO|DOCUMENTO",
  "external_ref": "string (max 500 chars)",
  "metadata": "object|null"
}
```

**ArtifactImportRequest:**
```json
{
  "artifacts": [
    {
      "connector_id": "uuid",
      "connector_implementation": "string (e.g.: JIRA, GITLAB, CONFLUENCE)",
      "type": "TAREA|CODIGO|DOCUMENTO",
      "external_ref": "string (max 500 chars)",
      "description": "string|null"
    }
  ]
}
```

**Query Parameters (GET `/api/v1/projects/{project_id}/releases`):**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number (GR2.2) |
| `size` | integer | 25 | Items per page, max 100 (GR2.2) |
| `status` | string | --- | Filter by release status (GR2.4) |
| `search` | string | --- | Search by name or version |
| `sort_by` | string | `created_at` | Sort field |
| `sort_order` | string | `desc` | Sort direction (`asc`, `desc`) |

**Query Parameters (GET `/api/v1/releases/{release_id}/results`):**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number (RH3.3) |
| `size` | integer | 25 | Items per page, max 100 (RH3.3) |
| `verdict` | string | --- | Filter by verdict (VALID, VALID_WITH_WARNINGS, INVALID) |
| `from_date` | datetime | --- | Results from date (ISO 8601) |
| `to_date` | datetime | --- | Results to date (ISO 8601) |

---

### 5.6 Connectors Router (`/api/v1/organizations/{org_id}/connectors`)

| Method | Route | Description | Permission |
|--------|------|-------------|---------|
| GET | `/api/v1/connectors/types` | List all connector types and implementations | Yes |
| GET | `/api/v1/organizations/{org_id}/connectors` | List organization connectors | Org access |
| POST | `/api/v1/organizations/{org_id}/connectors` | Register new connector | MANAGE_CONNECTORS |
| PATCH | `/api/v1/organizations/{org_id}/connectors/{connector_id}` | Update connector configuration | MANAGE_CONNECTORS |
| DELETE | `/api/v1/organizations/{org_id}/connectors/{connector_id}` | Delete connector | MANAGE_CONNECTORS |
| POST | `/api/v1/organizations/{org_id}/connectors/{connector_id}/test` | Test connector connection | MANAGE_CONNECTORS |

**Connector Types and Implementations (20 total):**

| Type | Implementations |
|------|-----------------|
| GESTOR_TAREAS | JIRA, LINEAR, TRELLO, ASANA, CLICKUP, TAIGA, PLANE |
| REPO_CODIGO | GITLAB, GITHUB, BITBUCKET, GITEA |
| SISTEMA_DOCUMENTAL | CONFLUENCE, NOTION, WIKIJS, BOOKSTACK |
| HERRAMIENTA_PLANIFICACION | MIRO |
| GESTION_CAMBIOS | JIRA_SM, GLPI, ZAMMAD, REDMINE |

**ConnectorCreateRequest:**
```json
{
  "connector_type": "GESTOR_TAREAS|REPO_CODIGO|SISTEMA_DOCUMENTAL|HERRAMIENTA_PLANIFICACION|GESTION_CAMBIOS",
  "connector_implementation": "JIRA|LINEAR|TRELLO|ASANA|CLICKUP|TAIGA|PLANE|GITLAB|GITHUB|BITBUCKET|GITEA|CONFLUENCE|NOTION|WIKIJS|BOOKSTACK|MIRO|JIRA_SM|GLPI|ZAMMAD|REDMINE",
  "name": "string (1-100 chars)",
  "credentials": "object (depends on connector type)"
}
```

**ConnectorUpdateRequest:**
```json
{
  "name": "string|null (1-100 chars)",
  "credentials": "object|null"
}
```

**ConnectorTestResponse:**
```json
{
  "success": "boolean",
  "latency_ms": "integer",
  "message": "string"
}
```

---

### 5.7 Profiles Router (`/api/v1/profiles`, `/api/v1/organizations/{org_id}/profiles`, `/api/v1/rules`)

| Method | Route | Description | Permission |
|--------|------|-------------|---------|
| GET | `/api/v1/organizations/{org_id}/profiles` | List organization profiles | Org access |
| POST | `/api/v1/organizations/{org_id}/profiles` | Create verification profile | Org access |
| PATCH | `/api/v1/profiles/{profile_id}` | Update profile | MANAGE_PROFILES |
| DELETE | `/api/v1/profiles/{profile_id}` | Delete profile | MANAGE_PROFILES |
| POST | `/api/v1/profiles/{profile_id}/rules` | Add rule to profile | MANAGE_RULES |
| PATCH | `/api/v1/rules/{rule_id}` | Update rule | MANAGE_RULES |
| DELETE | `/api/v1/rules/{rule_id}` | Delete rule | MANAGE_RULES |

**ProfileCreateRequest:**
```json
{
  "name": "string (1-100 chars)",
  "description": "string|null (max 500 chars)",
  "is_default": "boolean (default: false)"
}
```

**ProfileUpdateRequest:**
```json
{
  "name": "string|null (1-100 chars)",
  "description": "string|null (max 500 chars)",
  "is_default": "boolean|null"
}
```

**RuleCreateRequest:**
```json
{
  "rule_template": "string (RV-01 to RV-10, max 100 chars)",
  "severity": "INFO|LOW|MEDIUM|HIGH|CRITICAL (default: HIGH)",
  "params": "object|null (JSONB, depends on template)",
  "connector_instance_id": "uuid|null",
  "display_order": "integer (default: 0)"
}
```

**RuleUpdateRequest:**
```json
{
  "severity": "INFO|LOW|MEDIUM|HIGH|CRITICAL|null",
  "params": "object|null",
  "connector_instance_id": "uuid|null",
  "display_order": "integer|null",
  "is_active": "boolean|null"
}
```

---

### 5.8 Tasks Router (`/api/v1/tasks/{task_id}`)

| Method | Route | Description | Auth |
|--------|------|-------------|------|
| GET | `/api/v1/tasks/{task_id}` | Get async task status | Yes |

**TaskStatusResponse:**
```json
{
  "task_id": "string",
  "status": "PENDING|STARTED|SUCCESS|FAILURE|RETRY|REVOKED",
  "result": "string|null (contains the task result if completed)"
}
```

---

### 5.9 Custom Roles Router (`/api/v1/organizations/{org_id}/roles`, `/api/v1/roles/{role_id}`)

| Method | Route | Description | Permission |
|--------|------|-------------|---------|
| GET | `/api/v1/organizations/{org_id}/roles` | List org custom roles | MANAGE_ROLES |
| POST | `/api/v1/organizations/{org_id}/roles` | Create custom role | MANAGE_ROLES |
| PATCH | `/api/v1/roles/{role_id}` | Update custom role | MANAGE_ROLES |
| DELETE | `/api/v1/roles/{role_id}` | Delete custom role | MANAGE_ROLES |

**CustomRoleCreateRequest:**
```json
{
  "name": "string (1-100 chars)",
  "permissions": ["array of Permission strings (min: 1)"]
}
```

**CustomRoleUpdateRequest:**
```json
{
  "name": "string|null (1-100 chars)",
  "permissions": "array of Permission strings|null (min: 1)",
  "is_active": "boolean|null"
}
```

**CustomRoleResponse:**
```json
{
  "id": "uuid",
  "organization_id": "uuid",
  "name": "string",
  "permissions": ["array of Permission strings"],
  "is_active": "boolean",
  "created_at": "datetime (ISO 8601)",
  "updated_at": "datetime (ISO 8601)"
}
```

---

### 5.10 Dashboard Router (`/api/v1/dashboard/metrics`)

| Method | Route | Description | Permission |
|--------|------|-------------|---------|
| GET | `/api/v1/dashboard/metrics?org_id={org_id}` | Get dashboard metrics | Yes |

**Query Parameters:**
- `org_id` (optional): Filter by organization ID. If not provided, uses the user's organization.

**DashboardMetricsResponse:**
```json
{
  "total_releases": "integer",
  "valid_releases": "integer",
  "invalid_releases": "integer",
  "pending_releases": "integer",
  "total_verifications": "integer",
  "pass_rate": "float (0.0-1.0)"
}
```

---

### 5.11 API Keys Router (`/api/v1/users/{user_id}/api-keys`)

| Method | Route | Description | Permission |
|--------|------|-------------|---------|
| POST | `/api/v1/users/{user_id}/api-keys` | Create API key for user | Own user |
| GET | `/api/v1/users/{user_id}/api-keys` | List user API keys | Own user |
| DELETE | `/api/v1/users/{user_id}/api-keys/{key_id}` | Revoke API key | Own user |

**Restrictions:**
- Maximum 5 active API keys per user (per SRS requirement AC5)
- Keys optionally expire (configurable in days)
- Full key is only shown at creation time

**CreateAPIKeyRequest:**
```json
{
  "name": "string (1-100 chars)",
  "expires_in_days": "integer|null (min: 1)"
}
```

**APIKeyResponse:**
```json
{
  "id": "string",
  "user_id": "string",
  "organization_id": "string",
  "name": "string",
  "key": "string|null (only returned on creation)",
  "prefix": "string",
  "is_active": "boolean",
  "expires_at": "string|null (datetime ISO)",
  "created_at": "string (datetime ISO)",
  "last_used_at": "string|null (datetime ISO)"
}
```

---

### 5.12 Templates Router (`/api/v1/templates`) - PV4

| Method | Route | Description | Permission |
|--------|------|-------------|---------|
| POST | `/api/v1/templates` | Create release template | MANAGE_PROFILES |
| GET | `/api/v1/templates` | List accessible templates | Yes |
| GET | `/api/v1/templates/{template_id}` | Get template details | Yes |
| PATCH | `/api/v1/templates/{template_id}` | Update template | MANAGE_PROFILES |
| POST | `/api/v1/templates/{template_id}/archive` | Archive template | MANAGE_PROFILES |
| POST | `/api/v1/templates/{template_id}/clone` | Clone template to org | MANAGE_PROFILES |

**TemplateCreateRequest:**
```json
{
  "name": "string (1-100 chars)",
  "description": "string (max 500 chars)",
  "profile_id": "uuid",
  "project_name_template": "string|null"
}
```

---

### 5.13 Notifications Router (`/api/v1/notifications`) - NF1, NF3

| Method | Route | Description | Permission |
|--------|------|-------------|---------|
| GET | `/api/v1/notifications/channels` | List notification channels | Yes |
| POST | `/api/v1/notifications/channels` | Configure new channel | MANAGE_PROFILES |
| PATCH | `/api/v1/notifications/channels/{channel_id}` | Update channel | MANAGE_PROFILES |
| DELETE | `/api/v1/notifications/channels/{channel_id}` | Delete channel | MANAGE_PROFILES |
| GET | `/api/v1/notifications/preferences` | Get user notification preferences | Yes |
| PATCH | `/api/v1/notifications/preferences` | Update user preferences | Yes |
| POST | `/api/v1/notifications/subscriptions` | Subscribe to event type | Yes |
| DELETE | `/api/v1/notifications/subscriptions/{event_type}` | Unsubscribe from event | Yes |

**NotificationChannelConfig:**
```json
{
  "channel_type": "EMAIL|SLACK|MS_TEAMS",
  "enabled": "boolean",
  "config_data": {}
}
```

**UserNotificationPreferences:**
```json
{
  "release_validated": "boolean",
  "release_invalidated": "boolean",
  "release_pending_reminder": "boolean",
  "weekly_digest": "boolean"
}
```

---

### 5.14 Admin Router (`/api/v1/admin`) - U3 Only

| Method | Route | Description | Permission |
|--------|------|-------------|---------|
| POST | `/api/v1/admin/rules/reload` | Hot-reload custom rules (MV6.2.1) | U3 |

**RulesReloadResponse:**
```json
{
  "success": "boolean",
  "rules_loaded": "integer",
  "message": "string"
}
```

---

## 6. Authentication and Authorization

### Authentication Mechanism

**JWT-Based Authentication**

1. **Login Flow:**
   - User sends email/password to `/api/v1/auth/login`
   - Server validates credentials using `BcryptPasswordHasher`
   - On success, server returns access_token (15 minutes) and refresh_token (30 days)
   - JWT payload contains: `sub` (user_id), `role`, `email`, `organization_id`, `iat`, `exp`

2. **Token Structure:**
   ```python
   TokenPayload:
       user_id: UUID
       role: str
       email: str
       organization_id: Optional[UUID]
   ```

3. **Bearer Token Usage:**
   - All protected endpoints require header `Authorization: Bearer <token>`
   - Token is validated via `JwtHandler.decode_token()`

4. **Account Lockout:**
   - After 5 failed login attempts, the account locks for 15 minutes
   - Lockout is tracked via `locked_until` and `failed_login_attempts` fields
   - Once locked, the user receives HTTP 429 before the system authenticates

### Authorization Mechanism

**Role-Based Access Control (RBAC)**

| Role | Permissions |
|------|-------------|
| U2 (Standard) | VIEW_DASHBOARD, VIEW_ORG_PROJECTS, CREATE_RELEASE, UPDATE_OWN_RELEASES, ARCHIVE_RELEASE, EXECUTE_VERIFICATION, VIEW_OWN_HISTORY, MANAGE_OWN_API_KEYS |
| U4 (Org Manager) | U2 + CREATE_PROJECT, UPDATE_PROJECT, ARCHIVE_PROJECT, MANAGE_CONNECTORS, MANAGE_PROFILES, MANAGE_RULES, VIEW_ORG_DASHBOARD, INVITE_USERS, MANAGE_ROLES |
| U3 (Global Admin) | All permissions |

**Note:** The `DELETE_PROJECT` permission has been removed from all roles. The SRS (requirement GR7.2) and implementation notes specify that physical deletion of projects is not allowed, only logical archiving via `ARCHIVE_PROJECT`.

**Dependency Verification Functions:**
- `require_role(min_role)` - Validates role hierarchy
- `require_permission(permission)` - Direct permission check
- `require_org_access()` - Validates user has organization membership
- `require_project_access()` - Validates project belongs to user's organization
- `require_release_access()` - Validates release belongs to user's organization
- `require_connector_access()` - Validates connector belongs to user's organization
- `require_profile_access()` - Validates profile belongs to user's organization
- `require_rule_access()` - Validates rule belongs to user's organization
- `require_custom_role_access()` - Validates custom role belongs to user's organization
- `require_api_key_access()` - Validates API key belongs to user's organization

### Security Headers (production only)
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Referrer-Policy: strict-origin-when-cross-origin
```

---

## 7. Multi-Tenancy

**Organization-Based Isolation with N:M User Membership**

1. **Tenant Identification:**
   - Users can belong to multiple organizations via the `user_membership` table
   - The user's active organization context is determined from the JWT token (`organization_id` claim)
   - U3 users can access all organizations globally

2. **Data Isolation:**
   - All entity queries are scoped by the user's organization memberships
   - Access verification functions validate membership before returning data
   - Cross-tenant access is explicitly blocked

3. **API Key Scope:**
   - API keys belong to the user (not the organization directly)
   - Used for programmatic access within the tenant context
   - A user can only view/manage their own keys

---

## 8. Rate Limiting

**Implementation:** SlowAPI

| Endpoint Type | Limit |
|------------------|--------|
| Auth endpoints (`/auth/*`) | 30 requests/minute |
| Default endpoints | 100 requests/minute |
| Search endpoints | 30 requests/minute |
| Connector test endpoint | 100 requests/minute |

**Note:** The 30/min auth limit prevents conflicts with the failed login lockout policy (AC1.7: lockout after 5 failed attempts in 10 minutes).

---

## 9. Audit Logging

**Audit Events (25 types):**

| Event | Description |
|--------|-------------|
| LOGIN_SUCCESS | User authenticated successfully |
| LOGIN_FAILED | Authentication failed |
| USER_INVITED | User invited to organization |
| USER_ROLE_CHANGED | User role updated |
| USER_REMOVED | User removed from organization |
| ORG_OWNERSHIP_TRANSFERRED | Organization ownership transferred |
| API_KEY_CREATED | New API key generated |
| API_KEY_REVOKED | API key revoked |
| CONNECTOR_CREATED | Connector registered |
| CONNECTOR_UPDATED | Connector configuration updated |
| CONNECTOR_DELETED | Connector deleted |
| CONNECTOR_TESTED | Connector connection tested |
| RELEASE_CREATED | Release created |
| RELEASE_VERIFIED | Verification launched |
| RELEASE_ARCHIVED | Release archived |
| PROJECT_ARCHIVED | Project archived |
| PROFILE_CREATED | Verification profile created |
| PROFILE_UPDATED | Verification profile updated |
| PROFILE_DELETED | Verification profile deleted |
| RULE_CREATED | Verification rule added |
| RULE_UPDATED | Verification rule updated |
| RULE_DELETED | Verification rule deleted |
| CUSTOM_ROLE_CREATED | Custom role created |
| CUSTOM_ROLE_UPDATED | Custom role updated |
| CUSTOM_ROLE_DELETED | Custom role deleted |

---

## Summary

| Component | Count |
|------------|----------|
| Routers | 14 |
| Endpoints | 65+ |
| Domain Entities | 13 (+ 1 intermediate table) |
| Enums | 14 |
| DB Tables | 12 (11 official + user_membership) |
| Implemented Connectors | 20 |
| Audit Event Types | 25 |

---

## API Key Entity Usage

The **APIKey** entity enables programmatic API access without username/password.

**Use Cases:**
1. CI/CD and automation integrations with external systems
2. Scripts interacting with the API
3. Programmatic access for users who prefer not to use credentials

**Features:**
- Generated with `svk_` + 32 random characters format (URL-safe)
- SHA-256 hash stored in DB (raw key never stored in plain text)
- 12-character prefix for identification (e.g.: `svk_abc123defg`)
- Optionally expire (configurable in days)
- Can be revoked instantly
- Full key only shown at creation time
- `last_used_at` enables auditing of last use

**Per-User Restrictions:**
- Maximum 5 active API keys per user
- Each user can only view and manage their own keys
- Keys are associated with an organization for multi-tenant scoping

**Permissions:**
- API keys inherit the permissions of the creating user's role
- Default role is U2 (can be modified by the org's U4)

---

## Implementation Notes

### Archived Project Management

Per SRS requirement GR7.2, when a project is archived:
- The project becomes read-only
- All project releases also become read-only
- Physical deletion of projects is not allowed

### Release Verification Endpoint

To query verification results, use:
- `GET /api/v1/releases/{release_id}/results` - Verification history
- `GET /api/v1/releases/{release_id}/results/{result_id}` - Specific verification detail

### Organization-Scoped Connectors

All connector operations are nested under their organization scope:
- `PATCH /api/v1/organizations/{org_id}/connectors/{connector_id}`
- `DELETE /api/v1/organizations/{org_id}/connectors/{connector_id}`
- `POST /api/v1/organizations/{org_id}/connectors/{connector_id}/test`

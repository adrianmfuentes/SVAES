# Documentación de la API Backend de SVAES

## Tabla de Contenidos
1. [Arquitectura](#arquitectura)
2. [Entidades de Dominio](#entidades-de-dominio)
3. [Enums](#enums)
4. [Modelos de Base de Datos](#modelos-de-base-de-datos)
5. [Endpoints de la API por Router](#endpoints-de-la-api-por-router)
6. [Autenticación y Autorización](#autenticación-y-autorización)
7. [Multi-Tenancy](#multi-tenancy)
8. [Rate Limiting](#rate-limiting)
9. [Audit Logging](#audit-logging)

---

## 1. Arquitectura

### Arquitectura Hexagonal (Ports & Adapters)

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

### Estructura de Directorios

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

## 2. Entidades de Dominio

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

### UserMembership (Tabla Intermedia N:M)
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
plan: str = "default"
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
rules: list[VerificationRule] = field(default_factory=list)
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

### Relaciones entre Entidades

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
     ├────< APIKey (pertenece a User, scoped a Organization)
     │
     └────< CustomRole
```

---

## 3. Enums

### UserRole
```python
U1 = "U1"  # Guest/Viewer - invitado con acceso limitado
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
DELETE_PROJECT = "DELETE_PROJECT"
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

## 4. Modelos de Base de Datos

### Tabla: user
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

### Tabla: user_membership (Tabla Intermedia N:M)
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default=uuid4 |
| user_id | UUID | FK → user.id, NOT NULL |
| organization_id | UUID | FK → organization.id, NOT NULL |
| role | VARCHAR(20) | NOT NULL, default=U2 |
| joined_at | TIMESTAMP | NOT NULL |

**Unique constraint:** (user_id, organization_id)

### Tabla: organization
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default=uuid4 |
| name | VARCHAR(100) | NOT NULL |
| slug | VARCHAR(100) | UNIQUE, NOT NULL, INDEX |
| owner_id | UUID | FK → user.id, NULLABLE |
| is_active | BOOLEAN | NOT NULL, default=True |
| plan | VARCHAR(50) | NOT NULL, default='default' |
| created_at | TIMESTAMP | NOT NULL |
| updated_at | TIMESTAMP | NOT NULL |

### Tabla: project
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

### Tabla: release
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

### Tabla: connector_instance
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

### Tabla: verification_profile
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default=uuid4 |
| organization_id | UUID | FK → organization.id, NOT NULL |
| name | VARCHAR(100) | NOT NULL |
| description | VARCHAR(500) | NULLABLE |
| is_default | BOOLEAN | NOT NULL, default=False |
| rules | JSON | NULLABLE, default=list |
| created_at | TIMESTAMP | NOT NULL |
| updated_at | TIMESTAMP | NOT NULL |

### Tabla: verification_rule
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default=uuid4 |
| profile_id | UUID | FK → verification_profile.id, NOT NULL |
| rule_template | VARCHAR(100) | NOT NULL |
| severity | VARCHAR(20) | NOT NULL, default=HIGH |
| params | JSON | NULLABLE, default=dict |
| connector_instance_id | UUID | FK → connector_instance.id, NULLABLE |
| display_order | INTEGER | NOT NULL, default=0 |
| is_active | BOOLEAN | NOT NULL, default=True |
| created_at | TIMESTAMP | NOT NULL |

### Tabla: verification_result
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default=uuid4 |
| release_id | UUID | FK → release.id, NOT NULL |
| verdict | VARCHAR(30) | NOT NULL, default=INVALID |
| duration_ms | INTEGER | NOT NULL, default=0 |
| summary | JSON | NULLABLE, default=dict |
| rule_results | JSON | NULLABLE, default=list |
| profile_snapshot | JSON | NULLABLE, default=dict |
| executed_at | TIMESTAMP | NOT NULL |

### Tabla: artifact
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default=uuid4 |
| release_id | UUID | FK → release.id, NOT NULL |
| connector_instance_id | UUID | FK → connector_instance.id, NOT NULL |
| connector_implementation | VARCHAR(50) | NOT NULL |
| artifact_type | VARCHAR(20) | NOT NULL, default=TAREA |
| external_ref | VARCHAR(500) | NOT NULL |
| metadata | JSON | NULLABLE, default=dict |
| created_at | TIMESTAMP | NOT NULL |

### Tabla: api_key
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

### Tabla: custom_role
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

## 5. Endpoints de la API por Router

### 5.1 Auth Router (`/api/v1/auth`)

| Método | Ruta | Descripción | Auth |
|--------|------|-------------|------|
| POST | `/api/v1/auth/login` | Autenticar usuario con email/password | No (Rate: 30/min) |
| POST | `/api/v1/auth/refresh` | Refrescar access token | No (Rate: 30/min) |

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

| Método | Ruta | Descripción | Permiso |
|--------|------|-------------|---------|
| GET | `/api/v1/users/me` | Obtener perfil del usuario actual | Sí |
| PATCH | `/api/v1/users/me` | Actualizar nombre del usuario actual | Sí |
| POST | `/api/v1/users/me/password` | Cambiar contraseña del usuario actual | Sí |
| GET | `/api/v1/organizations/{org_id}/users` | Listar usuarios de la organización | MANAGE_ROLES |
| POST | `/api/v1/organizations/{org_id}/users/invite` | Invitar usuario a la organización | INVITE_USERS |
| PATCH | `/api/v1/organizations/{org_id}/users/{user_id}/role` | Actualizar rol del usuario en la org | MANAGE_ROLES |
| DELETE | `/api/v1/organizations/{org_id}/users/{user_id}` | Remover usuario de la organización | MANAGE_ROLES |
| POST | `/api/v1/admin/users` | Crear usuario globalmente (solo U3) | U3 |
| GET | `/api/v1/admin/users` | Listar todos los usuarios con filtros (solo U3) | U3 |
| PATCH | `/api/v1/admin/users/{user_id}/activate` | Activar cuenta de usuario (solo U3) | U3 |
| PATCH | `/api/v1/admin/users/{user_id}/deactivate` | Desactivar cuenta de usuario (solo U3) | U3 |
| PATCH | `/api/v1/admin/users/{user_id}/role` | Actualizar rol global del usuario (solo U3) | U3 |

---

### 5.3 Organizations Router (`/api/v1/organizations`)

| Método | Ruta | Descripción | Permiso |
|--------|------|-------------|---------|
| GET | `/api/v1/organizations` | Listar todas las organizaciones | U3 |
| POST | `/api/v1/organizations` | Crear nueva organización | U3 |
| GET | `/api/v1/organizations/{org_id}` | Obtener detalles de una organización | Acceso a la org |
| GET | `/api/v1/projects` | Listar proyectos accesibles (global, filtrado por acceso del usuario) | Sí |
| POST | `/api/v1/organizations/{org_id}/projects` | Crear proyecto en la organización | CREATE_PROJECT |
| POST | `/api/v1/organizations/{org_id}/projects/{project_id}/archive` | Archivar proyecto | ARCHIVE_PROJECT |
| POST | `/api/v1/organizations/{org_id}/transfer-ownership` | Transferir propiedad de la org | TRANSFER_OWNERSHIP |
| POST | `/api/v1/organizations/{org_id}/restore` | Restaurar (desarchivar) organización | U3 |

**Nota:** Los proyectos archivados pasan a modo solo lectura (sus releases también).

---

### 5.4 Projects Router (`/api/v1/projects/{project_id}`)

| Método | Ruta | Descripción | Permiso |
|--------|------|-------------|---------|
| GET | `/api/v1/projects/{project_id}` | Obtener detalles del proyecto | VIEW_ORG_PROJECTS |
| PATCH | `/api/v1/projects/{project_id}` | Actualizar proyecto | UPDATE_PROJECT |

**Nota:** El borrado físico de proyectos no está permitido. Se debe usar el endpoint de archivado.

---

### 5.5 Releases Router (`/api/v1/projects/{project_id}/releases`, `/api/v1/releases/{id}`)

| Método | Ruta | Descripción | Permiso |
|--------|------|-------------|---------|
| POST | `/api/v1/projects/{project_id}/releases` | Crear release en el proyecto | CREATE_RELEASE |
| GET | `/api/v1/projects/{project_id}/releases` | Listar releases del proyecto | VIEW_ORG_PROJECTS |
| GET | `/api/v1/releases/{id}` | Obtener detalles de la release | VIEW_ORG_PROJECTS |
| PATCH | `/api/v1/releases/{id}` | Actualizar release | UPDATE_OWN_RELEASES |
| DELETE | `/api/v1/releases/{id}` | Eliminar release (Solo en estado BORRADOR o PENDIENTE y sin verificaciones) | UPDATE_OWN_RELEASES |
| POST | `/api/v1/releases/{id}/archive` | Archivar release | ARCHIVE_RELEASE |
| POST | `/api/v1/releases/{id}/restore` | Restaurar release archivada | U3 (reservado) |
| GET | `/api/v1/releases/{id}/artifacts` | Listar artefactos de la release | VIEW_ORG_PROJECTS |
| POST | `/api/v1/releases/{id}/artifacts` | Agregar artefacto a la release | UPDATE_OWN_RELEASES |
| DELETE | `/api/v1/releases/{id}/artifacts/{artifact_id}` | Eliminar artefacto | UPDATE_OWN_RELEASES |
| POST | `/api/v1/releases/{id}/artifacts/import` | Importar artefactos desde CSV | UPDATE_OWN_RELEASES |
| POST | `/api/v1/releases/{id}/verify` | Lanzar verificación (async) | EXECUTE_VERIFICATION |
| GET | `/api/v1/releases/{id}/results` | Obtener historial de verificaciones | VIEW_OWN_HISTORY |
| GET | `/api/v1/releases/{id}/results/{rid}` | Obtener detalle de una verificación | VIEW_OWN_HISTORY |
| GET | `/api/v1/releases/{id}/results/{rid}/export?format=pdf` | Exportar verificación a PDF | VIEW_OWN_HISTORY |
| GET | `/api/v1/projects/{project_id}/results/export?format=csv` | Exportar historial de proyecto a CSV | VIEW_ORG_PROJECTS |

**State Machine de Release:**
```
BORRADOR → PENDIENTE → EN_VERIFICACION → VALIDA
                           ↓                ↓
                     NO_VALIDA       CON_ADVERTENCIAS
                           ↓                ↓
                          ARCHIVADA ←←←←←←←←←←←←
```

---

### 5.6 Connectors Router (`/api/v1/organizations/{org_id}/connectors`)

| Método | Ruta | Descripción | Permiso |
|--------|------|-------------|---------|
| GET | `/api/v1/connectors/types` | Listar todos los tipos e implementaciones de conectores | Sí |
| GET | `/api/v1/organizations/{org_id}/connectors` | Listar conectores de la organización | Acceso a la org |
| POST | `/api/v1/organizations/{org_id}/connectors` | Registrar nuevo conector | MANAGE_CONNECTORS |
| PATCH | `/api/v1/organizations/{org_id}/connectors/{connector_id}` | Actualizar configuración del conector | MANAGE_CONNECTORS |
| DELETE | `/api/v1/organizations/{org_id}/connectors/{connector_id}` | Eliminar conector | MANAGE_CONNECTORS |
| POST | `/api/v1/organizations/{org_id}/connectors/{connector_id}/test` | Probar conexión del conector | MANAGE_CONNECTORS |

**Tipos e Implementaciones de Conectores (20 total):**

| Tipo | Implementaciones |
|------|-----------------|
| GESTOR_TAREAS | JIRA, LINEAR, TRELLO, ASANA, CLICKUP, TAIGA, PLANE |
| REPO_CODIGO | GITLAB, GITHUB, BITBUCKET, GITEA |
| SISTEMA_DOCUMENTAL | CONFLUENCE, NOTION, WIKIJS, BOOKSTACK |
| HERRAMIENTA_PLANIFICACION | MIRO |
| GESTION_CAMBIOS | JIRA_SM, GLPI, ZAMMAD, REDMINE |

---

### 5.7 Profiles Router (`/api/v1/profiles`, `/api/v1/organizations/{org_id}/profiles`, `/api/v1/rules`)

| Método | Ruta | Descripción | Permiso |
|--------|------|-------------|---------|
| GET | `/api/v1/organizations/{org_id}/profiles` | Listar perfiles de la organización | Acceso a la org |
| POST | `/api/v1/organizations/{org_id}/profiles` | Crear perfil de verificación | Acceso a la org |
| PATCH | `/api/v1/profiles/{profile_id}` | Actualizar perfil | MANAGE_PROFILES |
| DELETE | `/api/v1/profiles/{profile_id}` | Eliminar perfil | MANAGE_PROFILES |
| POST | `/api/v1/profiles/{profile_id}/rules` | Agregar regla al perfil | MANAGE_RULES |
| PATCH | `/api/v1/rules/{rule_id}` | Actualizar regla | MANAGE_RULES |
| DELETE | `/api/v1/rules/{rule_id}` | Eliminar regla | MANAGE_RULES |

---

### 5.8 Tasks Router (`/api/v1/tasks/{task_id}`)

| Método | Ruta | Descripción | Auth |
|--------|------|-------------|------|
| GET | `/api/v1/tasks/{task_id}` | Obtener estado de tarea async | Sí |

**TaskStatusResponse:**
```json
{
  "task_id": "string",
  "status": "PENDING|STARTED|SUCCESS|FAILURE|RETRY|REVOKED",
  "result": "string|null"
}
```

---

### 5.9 Custom Roles Router (`/api/v1/organizations/{org_id}/roles`, `/api/v1/roles/{role_id}`)

| Método | Ruta | Descripción | Permiso |
|--------|------|-------------|---------|
| GET | `/api/v1/organizations/{org_id}/roles` | Listar roles personalizados de la org | MANAGE_ROLES |
| POST | `/api/v1/organizations/{org_id}/roles` | Crear rol personalizado | MANAGE_ROLES |
| PATCH | `/api/v1/roles/{role_id}` | Actualizar rol personalizado | MANAGE_ROLES |
| DELETE | `/api/v1/roles/{role_id}` | Eliminar rol personalizado | MANAGE_ROLES |

---

### 5.10 Dashboard Router (`/api/v1/dashboard/metrics`)

| Método | Ruta | Descripción | Permiso |
|--------|------|-------------|---------|
| GET | `/api/v1/dashboard/metrics?org_id={org_id}` | Obtener métricas del dashboard | Sí |

**Query Parameters:**
- `org_id` (opcional): Filtrar por ID de organización. Si no se proporciona, usa la organización del usuario.

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

| Método | Ruta | Descripción | Permiso |
|--------|------|-------------|---------|
| POST | `/api/v1/users/{user_id}/api-keys` | Crear API key para el usuario | El propio usuario |
| GET | `/api/v1/users/{user_id}/api-keys` | Listar API keys del usuario | El propio usuario |
| DELETE | `/api/v1/users/{user_id}/api-keys/{key_id}` | Revocar API key | El propio usuario |

**Restricciones:**
- Máximo 5 claves API activas por usuario (según requisito AC5 del SRS)
- Las claves expiran opcionalmente (configurable en días)
- Solo se muestra la clave completa en el momento de creación

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
  "key": "string|null (solo se retorna al crear)",
  "prefix": "string",
  "is_active": "boolean",
  "expires_at": "string|null (datetime ISO)",
  "created_at": "string (datetime ISO)",
  "last_used_at": "string|null (datetime ISO)"
}
```

---

### 5.12 Templates Router (`/api/v1/templates`) - PV4

| Método | Ruta | Descripción | Permiso |
|--------|------|-------------|---------|
| POST | `/api/v1/templates` | Crear template de release | MANAGE_PROFILES |
| GET | `/api/v1/templates` | Listar templates accesibles | Sí |
| GET | `/api/v1/templates/{template_id}` | Obtener detalles del template | Sí |
| PATCH | `/api/v1/templates/{template_id}` | Actualizar template | MANAGE_PROFILES |
| POST | `/api/v1/templates/{template_id}/archive` | Archivar template | MANAGE_PROFILES |
| POST | `/api/v1/templates/{template_id}/clone` | Clonar template a la org | MANAGE_PROFILES |

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

| Método | Ruta | Descripción | Permiso |
|--------|------|-------------|---------|
| GET | `/api/v1/notifications/channels` | Listar canales de notificación | Sí |
| POST | `/api/v1/notifications/channels` | Configurar nuevo canal | MANAGE_PROFILES |
| PATCH | `/api/v1/notifications/channels/{channel_id}` | Actualizar canal | MANAGE_PROFILES |
| DELETE | `/api/v1/notifications/channels/{channel_id}` | Eliminar canal | MANAGE_PROFILES |
| GET | `/api/v1/notifications/preferences` | Obtener preferencias de notificación del usuario | Sí |
| PATCH | `/api/v1/notifications/preferences` | Actualizar preferencias del usuario | Sí |
| POST | `/api/v1/notifications/subscriptions` | Suscribirse a tipo de evento | Sí |
| DELETE | `/api/v1/notifications/subscriptions/{event_type}` | Desuscribirse de evento | Sí |

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

### 5.14 Admin Router (`/api/v1/admin`) - Solo U3

| Método | Ruta | Descripción | Permiso |
|--------|------|-------------|---------|
| POST | `/api/v1/admin/rules/reload` | Recargar reglas personalizadas en caliente (MV6.2.1) | U3 |

**RulesReloadResponse:**
```json
{
  "success": "boolean",
  "rules_loaded": "integer",
  "message": "string"
}
```

---

## 6. Autenticación y Autorización

### Mecanismo de Autenticación

**Autenticación Basada en JWT**

1. **Flujo de Login:**
   - El usuario envía email/password a `/api/v1/auth/login`
   - El servidor valida las credenciales usando `BcryptPasswordHasher`
   - En éxito, el servidor retorna access_token (15 minutos) y refresh_token (30 días)
   - El payload del JWT contiene: `sub` (user_id), `role`, `email`, `organization_id`, `iat`, `exp`

2. **Estructura del Token:**
   ```python
   TokenPayload:
       user_id: UUID
       role: str
       email: str
       organization_id: Optional[UUID]
   ```

3. **Uso del Bearer Token:**
   - Todos los endpoints protegidos requieren header `Authorization: Bearer <token>`
   - El token se valida vía `JwtHandler.decode_token()`

4. **Bloqueo de Cuenta:**
   - Después de 5 intentos fallidos de login, la cuenta se bloquea por 15 minutos
   - El bloqueo se rastrea vía campos `locked_until` y `failed_login_attempts`
   - Luego de bloqueada la cuenta, el usuario recibe HTTP 429 antes de que el sistema autentique

### Mecanismo de Autorización

**Control de Acceso Basado en Roles (RBAC)**

| Rol | Permisos |
|------|-------------|
| U1 (Invitado) | VIEW_DASHBOARD, VIEW_OWN_PROJECTS |
| U2 (Estándar) | U1 + CREATE_RELEASE, UPDATE_OWN_RELEASES, ARCHIVE_RELEASE, EXECUTE_VERIFICATION, VIEW_OWN_HISTORY, MANAGE_OWN_API_KEYS |
| U4 (Gerente de Org) | U2 + VIEW_ORG_PROJECTS, CREATE_PROJECT, UPDATE_PROJECT, ARCHIVE_PROJECT, DELETE_PROJECT, MANAGE_CONNECTORS, MANAGE_PROFILES, MANAGE_RULES, VIEW_ORG_DASHBOARD, INVITE_USERS, MANAGE_ROLES |
| U3 (Admin Global) | Todos los permisos |

**Funciones de Verificación de Dependencias:**
- `require_role(min_role)` - Valida jerarquía de roles
- `require_permission(permission)` - Verificación directa de permiso
- `require_org_access()` - Valida que el usuario tiene membresía en la organización
- `require_project_access()` - Valida que el proyecto pertenece a la organización del usuario
- `require_release_access()` - Valida que la release pertenece a la organización del usuario
- `require_connector_access()` - Valida que el conector pertenece a la organización del usuario
- `require_profile_access()` - Valida que el perfil pertenece a la organización del usuario
- `require_rule_access()` - Valida que la regla pertenece a la organización del usuario
- `require_custom_role_access()` - Valida que el rol personalizado pertenece a la organización del usuario
- `require_api_key_access()` - Valida que la API key pertenece a la organización del usuario

### Headers de Seguridad (solo producción)
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Referrer-Policy: strict-origin-when-cross-origin
```

---

## 7. Multi-Tenancy

**Aislamiento Basado en Organizaciones con Membresía N:M de Usuarios**

1. **Identificación del Tenant:**
   - Los usuarios pueden pertenecer a múltiples organizaciones vía tabla `user_membership`
   - El contexto de organización activa del usuario se determina desde el token JWT (claim `organization_id`)
   - Los usuarios U3 pueden acceder a todas las organizaciones globalmente

2. **Aislamiento de Datos:**
   - Todas las consultas de entidades están limitadas por las membresías de organización del usuario
   - Las funciones de verificación de acceso validan la membresía antes de retornar datos
   - El acceso entre tenants está explícitamente bloqueado

3. **Alcance de API Keys:**
   - Las API keys son del usuario (no de la organización directamente)
   - Se usan para acceso programático dentro del contexto del tenant
   - Un usuario solo puede ver/administrar sus propias claves

---

## 8. Rate Limiting

**Implementación:** SlowAPI

| Tipo de Endpoint | Límite |
|------------------|--------|
| Endpoints de auth (`/auth/*`) | 30 requests/minuto |
| Endpoints por defecto | 100 requests/minuto |
| Endpoints de búsqueda | 30 requests/minuto |
| Endpoint de prueba de conector | 100 requests/minuto |

**Nota:** El límite de 30/min para auth evita conflictos con la política de bloqueo por intentos fallidos (AC1.7: bloqueo tras 5 intentos fallidos en 10 minutos).

---

## 9. Audit Logging

**Eventos de Audit (25 tipos):**

| Evento | Descripción |
|--------|-------------|
| LOGIN_SUCCESS | Usuario autenticado exitosamente |
| LOGIN_FAILED | Autenticación fallida |
| USER_INVITED | Usuario invitado a la organización |
| USER_ROLE_CHANGED | Rol del usuario actualizado |
| USER_REMOVED | Usuario removido de la organización |
| ORG_OWNERSHIP_TRANSFERRED | Propiedad de organización transferida |
| API_KEY_CREATED | Nueva API key generada |
| API_KEY_REVOKED | API key revocada |
| CONNECTOR_CREATED | Conector registrado |
| CONNECTOR_UPDATED | Configuración del conector actualizada |
| CONNECTOR_DELETED | Conector eliminado |
| CONNECTOR_TESTED | Conexión del conector probada |
| RELEASE_CREATED | Release creada |
| RELEASE_VERIFIED | Verificación lanzada |
| RELEASE_ARCHIVED | Release archivada |
| PROJECT_ARCHIVED | Proyecto archivado |
| PROFILE_CREATED | Perfil de verificación creado |
| PROFILE_UPDATED | Perfil de verificación modificado |
| PROFILE_DELETED | Perfil de verificación eliminado |
| RULE_CREATED | Regla de verificación agregada |
| RULE_UPDATED | Regla de verificación modificada |
| RULE_DELETED | Regla de verificación eliminada |
| CUSTOM_ROLE_CREATED | Rol personalizado creado |
| CUSTOM_ROLE_UPDATED | Rol personalizado modificado |
| CUSTOM_ROLE_DELETED | Rol personalizado eliminado |

---

## Resumen

| Componente | Cantidad |
|------------|----------|
| Routers | 14 |
| Endpoints | 65+ |
| Entidades de Dominio | 13 (+ 1 tabla intermedia) |
| Enums | 14 |
| Tablas de BD | 11 (10 oficiales + user_membership) |
| Conectores implementados | 20 |
| Tipos de eventos de audit | 25 |

---

## Uso de la Entidad API Key

La entidad **APIKey** permite acceso programático a la API sin necesidad de username/password.

**Casos de uso:**
1. Integraciones con sistemas externos (CI/CD, automatización)
2. Scripts que interactúan con la API
3. Acceso programático para usuarios que no quieren usar credenciales

**Características:**
- Generadas con formato `svk_` + 32 caracteres aleatorios (URL-safe)
- Hash SHA-256 almacenado en BD (nunca se almacena la clave en texto plano)
- Prefix de 12 caracteres para identificación (ej: `svk_abc123defg`)
- Opcionalmente expiran (configurable en días)
- Pueden ser revocadas instantáneamente
- Solo se muestra la clave completa en el momento de creación
- `last_used_at` permite auditar último uso

**Restricciones por usuario:**
- Máximo 5 claves API activas por usuario
- Cada usuario solo puede ver y administrar sus propias claves
- Las claves están asociadas a una organización para scoping multi-tenant

**Permisos:**
- Las API keys heredan los permisos del rol del usuario que las crea
- El rol predeterminado es U2 (puede ser modificado por el U4 de la org)

---

## Notas de Implementación

### Gestión de Proyectos Archivados

Según el requisito GR7.2 del SRS, cuando un proyecto se archiva:
- El proyecto pasa a modo solo lectura
- Todas las releases del proyecto también pasan a modo solo lectura
- No se permite el borrado físico de proyectos

### Endpoint de Verificación de Releases

Para consultar resultados de verificaciones, usar:
- `GET /api/v1/releases/{id}/results` - Historial de verificaciones
- `GET /api/v1/releases/{id}/results/{rid}` - Detalle de una verificación específica

### Conectores bajo Alcance de Organización

Todas las operaciones de conectores están anidadas bajo el alcance de su organización:
- `PATCH /api/v1/organizations/{org_id}/connectors/{connector_id}`
- `DELETE /api/v1/organizations/{org_id}/connectors/{connector_id}`
- `POST /api/v1/organizations/{org_id}/connectors/{connector_id}/test`
# SVAES — API de Verificación Automática de Entregas de Software

> **Sistema de Verificación Automática de Entregas de Software (SVAES)**
> Trabajo Fin de Grado — Adrián Martínez Fuentes (UO295454)
> Grado en Ingeniería Informática del Software — Universidad de Oviedo

---

## Índice

1. [Descripción General](#1-descripción-general)
2. [Arquitectura](#2-arquitectura)
3. [Autenticación y Autorización](#3-autenticación-y-autorización)
4. [Modelo de Datos](#4-modelo-de-datos)
5. [Sistema de Conectores](#5-sistema-de-conectores)
6. [API Endpoints](#6-api-endpoints)
7. [Sistema RBAC](#7-sistema-rbac)
8. [Seguridad](#8-seguridad)
9. [Ejecución del Proyecto](#9-ejecución-del-proyecto)

---

## 1. Descripción General

SVAES es una plataforma académica que automatiza la validación de releases de software contra un conjunto configurable de reglas de verificación (RV-01 a RV-10). El sistema permite:

- **Gestión de organizaciones y proyectos** — Estructura multi-tenant
- **Gestión de releases** — Creación, archivado y seguimiento de versiones de software
- **Artefactos** — Vinculación de código, tareas y documentos a cada release
- **Verificación automatizada** — Ejecución de reglas contra los artefactos conectados
- **Perfiles de verificación** — Configuración de reglas por proyecto
- **Conectores externos** — Integración con Jira, GitHub, GitLab, Linear, Trello, Asana, etc.

### Tecnologías

| Capa | Tecnología |
|------|------------|
| API Backend | FastAPI (Python 3.11+) |
| Base de datos | PostgreSQL 16 |
| ORM | SQLAlchemy 2.x |
| Migraciones | Alembic |
| Autenticación | JWT (HS256) |
| HTTP Client | httpx (async) |

---

## 2. Arquitectura

SVAES sigue **Clean Architecture** con separación estricta de capas:

```
src/
├── domain/           # Entidades, enums, excepciones (sin dependencias externas)
│   ├── entities/     # User, Organization, Project, Release, Artifact, ConnectorInstance
│   ├── enums.py      # UserRole, Permission, ConnectorType, ConnectorImplementation
│   └── exceptions.py # DomainException, EntityNotFoundError, etc.
│
├── application/      # Casos de uso (lógica de negocio)
│   ├── ports/       # Interfaces (puertos de entrada y salida)
│   │   ├── input/   # IReleaseService, IConnectorService, etc.
│   │   └── output/  # IUserRepository, IConnectorRegistry, IConnector
│   └── use_cases/   # Implementaciones de casos de uso
│
├── infrastructure/   # Adaptadores (implementaciones concretas)
│   ├── primary/     # Capa primaria (API, middleware, routers)
│   │   ├── routers/ # Endpoints FastAPI
│   │   └── middleware/ # JWT handler, password hasher
│   └── secondary/   # Capa secundaria (DB, queue, connectors)
│       ├── database/
│       │   ├── models/      # Modelos SQLAlchemy
│       │   └── repositories/ # Implementaciones de repositorios
│       ├── queue/           # Cola de tareas (Celery)
│       └── connectors/      # Implementaciones de conectores
│           ├── task_management/   # Jira, Linear, Trello, Asana
│           ├── source_control/     # GitHub, GitLab, Bitbucket, Gitea
│           ├── documentation/      # Confluence, Notion, Wiki.js, BookStack
│           ├── planning/           # ClickUp, Taiga, Plane, Miro
│           └── change_management/   # Jira SM, GLPI, Zammad, Redmine
│
└── core/            # Configuración, dependencias, rate limiting
```

### Principio Fundamental

> Las dependencias de código **sólo pueden apuntar hacia el interior**.
> `domain/` no importa nada de `application/` ni de `infrastructure/`.

---

## 3. Autenticación y Autorización

### 3.1 Autenticación JWT

Todos los endpoints protegidos requieren un token JWT en el header:

```
Authorization: Bearer <token>
```

El token contiene:

```json
{
  "sub": "<user_id>",
  "role": "OPERATOR|MANAGER|ADMIN",
  "email": "user@example.com",
  "organization_id": "<org_id>",
  "iat": 1234567890,
  "exp": 1234571490
}
```

### 3.2 Endpoints de Autenticación

#### Login
```
POST /api/v1/auth/login
```
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```
**Respuesta:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "user_id": "uuid",
  "role": "OPERATOR"
}
```

#### Refresh Token
```
POST /api/v1/auth/refresh
```
```json
{
  "refresh_token": "eyJ..."
}
```

### 3.3 Protección contra Fuerza Bruta

- **5 intentos fallidos** en 10 minutos → cuenta bloqueada **15 minutos**
- Cada intento fallido incrementa el contador `failed_login_attempts`
- Al bloquearse, el campo `locked_until` indica cuándo se lifted el bloqueo

---

## 4. Modelo de Datos

### 4.1 Entidades Principales

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│ Organization │───────│   Project    │───────│   Release    │
│              │  1:N  │              │  1:N  │              │
│ - name       │       │ - name       │       │ - version    │
│ - slug       │       │ - description│       │ - status     │
│ - owner_id   │       │ - profile_id │       │ - created_by │
│ - plan       │       └──────────────┘       └──────┬───────┘
└──────────────┘                                      │
       │  1:N                                        │ 1:N
       ▼                                             ▼
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│     User     │       │  Connector   │       │ Verification │
│              │       │  Instance    │       │   Profile    │
│ - email      │       │              │       │              │
│ - role       │       │ - connector_type    │ - name       │
│ - organization│      │ - connector_impl│       │ - is_default│
│   _id        │       │ - name       │       └──────┬───────┘
└──────────────┘       │ - encrypted  │              │ 1:N
                       │   _credentials│              ▼
                       │ - status     │       ┌──────────────┐
                       └──────────────┘       │    Rule      │
                                              │              │
┌──────────────┐       ┌──────────────┐       │ - template   │
│   Release    │───────│   Artifact   │       │ - severity   │
│              │  1:N  │              │       │ - params     │
│ - id         │       │ - type       │       │ - is_active  │
│ - version    │       │ - external_ref│       └──────────────┘
└──────────────┘       │ - metadata   │
                       └──────────────┘
```

### 4.2 Estados de Release

```
BORRADOR → PENDIENTE → EN_VERIFICACION → VALIDA
    │           │              │
    │           └──────────────┴──→ NO_VALIDA
    │                               │
    └───────────────────────────────┴──→ CON_ADVERTENCIAS
    │
    └──────────────────────────────────→ ARCHIVADA
```

### 4.3 Roles de Usuario

| Rol | Descripción |
|-----|-------------|
| **VIEWER** | Solo lectura en proyectos propios |
| **OPERATOR** | Crea/actualiza releases, ejecuta verificaciones en sus proyectos |
| **MANAGER** | Gestiona proyectos, conectores, perfiles de su organización |
| **ADMIN** | Acceso global a todo el sistema |

---

## 5. Sistema de Conectores

### 5.1 Conceptos Clave

El sistema de conectores sigue un diseño de **dos niveles**:

| Concepto | Descripción | Ejemplos |
|----------|-------------|----------|
| **ConnectorType** | Tipo funcional genérico | `GESTOR_TAREAS`, `REPO_CODIGO`, `SISTEMA_DOCUMENTAL` |
| **ConnectorImplementation** | Implementación concreta | `JIRA`, `GITHUB`, `CONFLUENCE`, `LINEAR` |

### 5.2 Tipos Funcionales (ConnectorType)

| Tipo | Descripción |
|------|-------------|
| `GESTOR_TAREAS` | Herramientas que rastrean trabajo diario, historias de usuario y bugs |
| `REPO_CODIGO` | Fuentes de verdad para ramas, commits y etiquetas de versión |
| `SISTEMA_DOCUMENTAL` | Informes de pruebas, manuales técnicos y planes de entrega |
| `HERRAMIENTA_PLANIFICACION` | Roadmap a largo plazo, épicas y planes de versiones |
| `GESTION_CAMBIOS` | Sistemas ITSM para aprobaciones formales, CABs e incidencias |

### 5.3 Implementaciones Disponibles (ConnectorImplementation)

#### GESTOR_TAREAS
| Implementación | API | Plan Gratuito |
|---------------|-----|---------------|
| `JIRA` | REST v2/v3 | 10 usuarios |
| `LINEAR` | GraphQL | Sólido |
| `TRELLO` | REST | Muy permisivo |
| `ASANA` | REST | 15 usuarios |

#### REPO_CODIGO
| Implementación | API | Plan Gratuito |
|---------------|-----|---------------|
| `GITLAB` | REST v4 | Ilimitado (SaaS o CE) |
| `GITHUB` | REST | Ilimitado |
| `BITBUCKET` | REST | 5 usuarios, repos privados ilimitados |
| `GITEA` | REST (compat GitHub) | Auto-alojado, open source |

#### SISTEMA_DOCUMENTAL
| Implementación | API | Plan Gratuito |
|---------------|-----|---------------|
| `CONFLUENCE` | REST | 10 usuarios |
| `NOTION` | REST | Muy completo |
| `WIKIJS` | GraphQL | Auto-alojado, open source |
| `BOOKSTACK` | REST | Auto-alojado, open source |

#### HERRAMIENTA_PLANIFICACION
| Implementación | API | Plan Gratuito |
|---------------|-----|---------------|
| `CLICKUP` | REST | Muy completo |
| `TAIGA` | REST | Cloud o auto-alojado |
| `PLANE` | REST | Auto-alojado, open source |
| `MIRO` | REST | 3 pizarras |

#### GESTION_CAMBIOS
| Implementación | API | Plan Gratuito |
|---------------|-----|---------------|
| `JIRA_SM` | REST | 3 agentes |
| `GLPI` | REST | Auto-alojado, open source |
| `ZAMMAD` | REST | Auto-alojado, open source |
| `REDMINE` | REST/XML | Auto-alojado, open source |

### 5.4 Endpoint de Tipos de Conector

```
GET /api/v1/connectors/types
```

Respuesta:

```json
{
  "implementations": [
    {
      "implementation": "GITHUB",
      "type": "REPO_CODIGO",
      "metadata": {
        "name": "GitHub",
        "version": "1.0",
        "artifact_types": ["pull_request", "commit", "release", "workflow_run"]
      },
      "config_schema": {
        "token": {"type": "string", "label": "Personal Access Token", "required": true, "sensitive": true},
        "owner": {"type": "string", "label": "Owner/Organization", "required": false},
        "repo": {"type": "string", "label": "Repository", "required": false},
        "base_url": {"type": "string", "label": "Base URL", "required": false, "default": "https://api.github.com"}
      }
    }
  ],
  "by_type": {
    "REPO_CODIGO": [
      {
        "implementation": "GITHUB",
        "metadata": {...},
        "config_schema": {...}
      },
      {
        "implementation": "GITLAB",
        "metadata": {...},
        "config_schema": {...}
      }
    ],
    "GESTOR_TAREAS": [...]
  }
}
```

### 5.5 Registro de Conectores

El `ConnectorRegistry` mantiene el mapeo entre implementaciones y sus clases concretas:

```
ConnectorRegistry
├── _by_implementation["GITHUB"] → GitHubConnector()
├── _by_implementation["JIRA"]    → JiraConnector()
├── _by_implementation["GITLAB"] → GitLabConnector()
└── ...
```

### 5.6 Flujo de Configuración

1. **UI consulta** `GET /api/v1/connectors/types` para ver implementaciones disponibles
2. **UI muestra** `config_schema` de cada implementación para renderizar formulario
3. **Manager llena** formulario y envía `POST /api/v1/organizations/{org_id}/connectors`
4. **Sistema guarda** `connector_type`, `connector_implementation` y credenciales cifradas
5. **En verificación** se usa `connector_implementation` para instanciar el conector correcto

---

## 6. API Endpoints

### 6.1 Autenticación

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/auth/login` | Iniciar sesión | No |
| POST | `/api/v1/auth/refresh` | Refrescar token | No |

### 6.2 Organizaciones

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/organizations` | Listar todas | ADMIN |
| POST | `/api/v1/organizations` | Crear | ADMIN |
| GET | `/api/v1/organizations/{org_id}/projects` | Listar proyectos | MANAGER+ |
| POST | `/api/v1/organizations/{org_id}/projects` | Crear proyecto | MANAGER+ |
| POST | `/api/v1/organizations/{org_id}/transfer-ownership` | Transferir propiedad | OWNER |

### 6.3 Releases

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/projects/{project_id}/releases` | Crear release | OPERATOR+ |
| GET | `/api/v1/projects/{project_id}/releases` | Listar releases | OPERATOR+ |
| GET | `/api/v1/releases/{id}` | Detalle release | OPERATOR+ |
| PATCH | `/api/v1/releases/{id}` | Actualizar release | OPERATOR+ |
| DELETE | `/api/v1/releases/{id}` | Eliminar release | OPERATOR+ |
| POST | `/api/v1/releases/{id}/archive` | Archivar release | OPERATOR+ |

### 6.4 Artefactos

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/releases/{id}/artifacts` | Listar artefactos | OPERATOR+ |
| POST | `/api/v1/releases/{id}/artifacts` | Agregar artefacto | OPERATOR+ |
| DELETE | `/api/v1/releases/{id}/artifacts/{artifact_id}` | Eliminar artefacto | OPERATOR+ |

### 6.5 Verificaciones

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/releases/{id}/verify` | Lanzar verificación | OPERATOR+ |
| GET | `/api/v1/releases/{id}/results` | Historial verificaciones | OPERATOR+ |
| GET | `/api/v1/releases/{id}/results/{rid}` | Detalle verificación | OPERATOR+ |
| GET | `/api/v1/tasks/{task_id}` | Estado tarea asíncrona | Cualquier usuario |

### 6.6 Conectores

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/connectors/types` | Listar tipos e implementaciones disponibles | Cualquier usuario |
| GET | `/api/v1/organizations/{org_id}/connectors` | Listar conectores de org | MANAGER+ |
| POST | `/api/v1/organizations/{org_id}/connectors` | Registrar conector | MANAGER+ |
| PATCH | `/api/v1/connectors/{connector_id}` | Actualizar conector | MANAGER+ |
| DELETE | `/api/v1/connectors/{connector_id}` | Eliminar conector | MANAGER+ |
| POST | `/api/v1/connectors/{connector_id}/test` | Probar conexión | MANAGER+ |

### 6.7 Perfiles de Verificación

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/organizations/{org_id}/profiles` | Listar perfiles | MANAGER+ |
| POST | `/api/v1/organizations/{org_id}/profiles` | Crear perfil | MANAGER+ |
| PATCH | `/api/v1/profiles/{profile_id}` | Actualizar perfil | MANAGER+ |
| DELETE | `/api/v1/profiles/{profile_id}` | Eliminar perfil | MANAGER+ |

### 6.8 Reglas

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/profiles/{profile_id}/rules` | Agregar regla | MANAGER+ |
| PATCH | `/api/v1/rules/{rule_id}` | Actualizar regla | MANAGER+ |
| DELETE | `/api/v1/rules/{rule_id}` | Eliminar regla | MANAGER+ |

### 6.9 Usuarios

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/users/me` | Perfil actual | Cualquier usuario |
| PATCH | `/api/v1/users/me` | Actualizar perfil | Cualquier usuario |
| POST | `/api/v1/users/me/password` | Cambiar contraseña | Cualquier usuario |
| GET | `/api/v1/organizations/{org_id}/users` | Listar usuarios org | MANAGER+ |
| POST | `/api/v1/organizations/{org_id}/users/invite` | Invitar usuario | MANAGER+ |
| PATCH | `/api/v1/organizations/{org_id}/users/{user_id}/role` | Cambiar rol | MANAGER+ |
| DELETE | `/api/v1/organizations/{org_id}/users/{user_id}` | Eliminar usuario org | MANAGER+ |

### 6.10 Roles Personalizados

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/organizations/{org_id}/roles` | Listar roles | MANAGER+ |
| POST | `/api/v1/organizations/{org_id}/roles` | Crear rol | MANAGER+ |
| PATCH | `/api/v1/roles/{role_id}` | Actualizar rol | MANAGER+ |
| DELETE | `/api/v1/roles/{role_id}` | Eliminar rol | MANAGER+ |

---

## 7. Sistema RBAC

### 7.1 Roles Predefinidos

```
ADMIN (4)
  │
  ├── MANAGE_ORGANIZATIONS, MANAGE_ALL_USERS
  │
MANAGER (3)
  │
  ├── MANAGE_CONNECTORS, MANAGE_PROFILES, MANAGE_RULES
  ├── INVITE_USERS, MANAGE_ROLES, TRANSFER_OWNERSHIP
  ├── VIEW_ORG_DASHBOARD, VIEW_ORG_PROJECTS
  ├── CREATE_PROJECT, UPDATE_PROJECT, DELETE_PROJECT
  │
OPERATOR (2)
  │
  ├── CREATE_RELEASE, UPDATE_OWN_RELEASES, ARCHIVE_RELEASE
  ├── EXECUTE_VERIFICATION, VIEW_OWN_HISTORY
  ├── MANAGE_OWN_API_KEYS
  │
VIEWER (1)
  │
  ├── VIEW_DASHBOARD, VIEW_OWN_PROJECTS
```

### 7.2 Roles Personalizados

Los Managers pueden crear roles a medida dentro de su organización:

```json
{
  "name": "QA Engineer",
  "permissions": [
    "VIEW_ORG_PROJECTS",
    "CREATE_RELEASE",
    "EXECUTE_VERIFICATION",
    "VIEW_OWN_HISTORY"
  ]
}
```

### 7.3 Aislamiento Multi-Tenant

**Regla crítica:** Todo acceso a recursos de otra organización debe ser rechazado con **HTTP 403 Forbidden**.

---

## 8. Seguridad

### 8.1 Contraseñas

- Hash con **Bcrypt** (factor de costo 12)
- Nunca se almacenan contraseñas en texto plano
- Validación: mínimo 8 caracteres

### 8.2 Tokens JWT

- Algoritmo: **HS256**
- Access token expira: **1 hora**
- Refresh token expira: **24 horas**
- Secret key configurable vía variable de entorno

### 8.3 Rate Limiting

- Configurable por endpoint
- Por defecto: 100 requests/minuto para reads, 20/min para writes
- Headers `X-RateLimit-*` en respuestas

### 8.4 Bloqueo por Fuerza Bruta

```
Intento 1-4 fallidos → "Credenciales inválidas. Intentos restantes: N"
Intento 5 fallido   → Cuenta bloqueada 15 minutos
```

### 8.5 Cifrado de Credenciales

Las credenciales de conectores se cifran con **Fernet** antes de almacenarse en BD.

---

## 9. Ejecución del Proyecto

### 9.1 Requisitos

- Python 3.11+
- PostgreSQL 16
- Poetry o pip

### 9.2 Variables de Entorno

Crear `.env` en `api/`:

```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/svaes
JWT_SECRET_KEY=tu-secret-key-de-al-menos-32-bytes
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60
ENVIRONMENT=development
ALLOWED_ORIGINS=http://localhost:4200
```

### 9.3 Instalación y Ejecución

```bash
# Con Poetry
cd api
poetry install
poetry run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# O con pip
pip install -e .
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 9.4 Migraciones de Base de Datos

```bash
alembic upgrade head
alembic revision --autogenerate -m "descripción"
```

### 9.5 Documentación de la API

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 10. Estados de Verificación

### 10.1 Severidad de Reglas

| Valor | Descripción |
|-------|-------------|
| `INFO` | Informativa, no afecta al veredicto |
| `LOW` | Baja prioridad |
| `MEDIUM` | Prioridad media |
| `HIGH` | Alta prioridad, afecta al veredicto |
| `CRITICAL` | Crítica, fail inmediato |

### 10.2 Veredictos

| Veredicto | Descripción |
|-----------|-------------|
| `VALID` | Todas las reglas obligatorias pasaron |
| `VALID_WITH_WARNINGS` | Pasó pero con advertencias |
| `INVALID` | Al menos una regla obligatoria falló |

---

## 11. Códigos de Error

| Código | Significado |
|--------|-------------|
| 400 | Bad Request — Datos inválidos |
| 401 | Unauthorized — Token inválido o expirado |
| 403 | Forbidden — Sin permisos para el recurso |
| 404 | Not Found — Recurso no encontrado |
| 409 | Conflict — Conflicto (e.g., duplicado) |
| 422 | Unprocessable Entity — Validación fallida |
| 429 | Too Many Requests — Rate limit excedido |
| 500 | Internal Server Error — Error inesperado |

---

*Última actualización: Mayo 2026 — Adrián Martínez Fuentes (UO295454)*
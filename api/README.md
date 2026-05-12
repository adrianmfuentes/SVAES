# SVAES — API Backend

Backend principal del **Sistema de Verificación Automática de Entregas de Software (SVAES)**. Servicio REST construido sobre **Python 3.11** y **FastAPI**, diseñado para entornos multi-tenant y orquestación de verificaciones de código mediante un motor externo en Rust.

---

## Tabla de contenidos

1. [Visión general](#visión-general)
2. [Arquitectura](#arquitectura)
3. [Estructura de directorios](#estructura-de-directorios)
4. [Tecnologías principales](#tecnologías-principales)
5. [Endpoints disponibles](#endpoints-disponibles)
6. [RBAC — Control de acceso por roles](#rbac--control-de-acceso-por-roles)
7. [Cola de tareas — Celery + Redis](#cola-de-tareas--celery--redis)
8. [Puesta en marcha](#puesta-en-marcha)
9. [Variables de entorno](#variables-de-entorno)
10. [Migraciones de base de datos](#migraciones-de-base-de-datos)

---

## Visión general

Este servicio actúa como el punto de entrada central de la plataforma SVAES. Es responsable de:

- Gestionar la autenticación y autorización de usuarios.
- Exponer la API REST consumida por los clientes.
- Orquestar los casos de uso de negocio: organizaciones, proyectos, perfiles de verificación, releases, conectores externos y reglas de verificación.
- Gestionar artefactos de software (tareas, commits, documentos) asociados a cada release.
- Delegar las tareas computacionalmente intensivas al **motor de verificación en Rust** mediante colas asíncronas.
- Emitir resultados de verificación en tiempo real mediante **Server-Sent Events (SSE)**.

---

## Arquitectura

El servicio sigue los principios de **Arquitectura Hexagonal** (_Ports & Adapters_) y **Clean Architecture**. El dominio de negocio permanece completamente aislado de frameworks, bases de datos y protocolos de transporte.

```
┌─────────────────────────────────────────────────────────┐
│                   Adaptadores Primarios                 │
└──────────────────────────┬──────────────────────────────┘
                           │  invocan
┌──────────────────────────▼──────────────────────────────┐
│                      Aplicación                          │
│             application/  ←  Casos de uso                │
└──────────┬───────────────────────────────┬──────────────┘
           │  lee/escribe vía puertos      │
┌──────────▼──────────┐        ┌───────────▼──────────────┐
│      Dominio        │        │  Adaptadores Secundarios   │
│  domain/            │        │  infrastructure/           │
│  Entidades, Puertos │        │  PostgreSQL (RLS), Celery, │
│  (interfaces)       │        │  Redis, psycopg3/2         │
└─────────────────────┘        └───────────────────────────┘
```

Las dependencias apuntan siempre hacia adentro: `infrastructure` y `api` dependen de `application`, que depende de `domain`. El dominio no importa nada externo.

### Separación async / sync

Los handlers HTTP (FastAPI) y repositorios usan **SQLAlchemy async** (`AsyncSession`, `psycopg3`). Los workers de Celery usan **SQLAlchemy síncrono** (`Session`, `psycopg2`) ya que corren en procesos separados sin event loop. Ambas capas coexisten:

- `SqlArtifactRepository` / `SqlVerificationResultRepository` → para la API (async)
- `SyncSqlArtifactRepository` / `SyncSqlVerificationResultRepository` → para workers (sync)

---

## Estructura de directorios

```
apps/api/                      # Raíz del proyecto
├── alembic/                  # Migraciones de base de datos
│   └── versions/             # Historial de revisiones Alembic
├── src/                      # Código fuente principal
│   │
│   ├── main.py               # Punto de entrada
│   │
│   ├── domain/               # Lógica de negocio pura (sin dependencias externas)
│   │   ├── entities/
│   │   │   ├── user.py, organization.py, project.py
│   │   │   ├── release.py, artifact.py
│   │   │   ├── verification_profile.py, verification_rule.py
│   │   │   ├── verification_result.py
│   │   │   ├── connector_instance.py
│   │   │   └── enums.py
│   │   ├── ports/            # Contratos
│   │   │   ├── i_user_repository.py, i_organization_repository.py
│   │   │   ├── i_project_repository.py, i_release_repository.py
│   │   │   ├── i_profile_repository.py, i_connector_repository.py
│   │   │   ├── i_artifact_repository.py
│   │   │   ├── i_verification_rule_repository.py
│   │   │   ├── i_verification_result_repository.py
│   │   │   ├── i_task_queue.py, i_verification_engine.py
│   │   │   ├── i_token_service.py, i_password_hasher.py
│   │   │   ├── i_credential_encryptor.py, i_connector.py
│   │   └── exceptions.py
│   │
│   ├── application/          # Casos de uso
│   │   └── use_cases/
│   │       ├── auth_use_cases.py
│   │       ├── user_use_cases.py
│   │       ├── organization_use_cases.py
│   │       ├── project_use_cases.py
│   │       ├── manage_profile.py
│   │       ├── create_release.py
│   │       ├── launch_verification.py
│   │       ├── get_verification_history.py
│   │       ├── configure_connector.py
│   │       ├── connector_use_cases.py
│   │       ├── artifact_use_cases.py
│   │       └── verification_rule_use_cases.py
│   │
│   ├── infrastructure/       # Adaptadores (implementan los puertos)
│   │   ├── config.py
│   │   ├── database/         # Persistencia con PostgreSQL + SQLAlchemy
│   │   │   ├── base.py
│   │   │   ├── session.py    # Sesiones async (API) y sync (workers)
│   │   │   ├── models/
│   │   │   └── repositories/
│   │   ├── queue/            # Cola de tareas asíncronas
│   │   │   ├── celery_app.py
│   │   │   └── celery_task_queue.py
│   │   ├── workers/          # Procesos en segundo plano
│   │   │   └── verification_worker.py
│   │   ├── security/         # Autenticación y cifrado
│   │   │   ├── jwt_handler.py
│   │   │   ├── password_hasher.py
│   │   │   ├── credential_encryptor.py
│   │   │   └── mock_task_queue.py
│   │   ├── adapters/         # Registro e instanciación de conectores
│   │   │   └── connector_registry.py
│   │   └── logging/         # Configuración de logs
│   │
│   ├── api/              # Endpoints HTTP (FastAPI)
│   │   ├── dependencies.py      # Inyección de dependencias + guards RBAC
│   │   ├── routers/
│   │   │   ├── auth.py                 # /auth/login, /auth/register
│   │   │   ├── users.py                # /users, /users/me
│   │   │   ├── organizations.py        # /organizations
│   │   │   ├── projects.py             # /projects
│   │   │   ├── profiles.py             # /profiles
│   │   │   ├── releases.py             # /releases, /releases/{id}/verify
│   │   │   ├── artifacts.py            # /releases/{id}/artifacts
│   │   │   ├── connectors.py           # /organizations/{id}/connectors
│   │   │   └── verification_rules.py   # /profiles/{id}/rules
│   │   └── schemas/             # Modelos Pydantic (petición/respuesta HTTP)
│   │       ├── auth.py, user.py, organization.py
│   │       ├── project.py, release.py
│   │       ├── profile.py, verification_rule.py
│   │       ├── connector.py, artifact.py
│   │
│   └── rate_limit.py        # Límite de peticiones (slowapi)
│
├── tests/                   # Suite de tests (fuera de src/)
│
├── alembic.ini              # Configuración de migraciones
├── pyproject.toml           # Dependencias Python
└── Dockerfile               # Imagen Docker
```

---

## Tecnologías principales

| Componente | Tecnología | Versión |
|---|---|---|
| Runtime | Python | 3.11+ |
| Framework HTTP | FastAPI + Uvicorn | 0.136 |
| Base de datos | PostgreSQL (con RLS) | 16 |
| ORM / migraciones | SQLAlchemy + Alembic | 2.x |
| Driver async (API) | psycopg3 (binary) | 3.2 |
| Driver sync (workers) | psycopg2-binary | 2.9 |
| Autenticación | PyJWT + passlib/bcrypt | — |
| Cifrado de credenciales | cryptography (Fernet) | 46.x |
| Rate limiting | slowapi | 0.1.9 |
| Streaming en tiempo real | SSE (Server-Sent Events) | nativo FastAPI |
| Configuración | pydantic-settings | 2.x |
| Gestor de paquetes | uv | — |
| Cola de tareas | Celery | 5.x |
| Broker / result backend | Redis | 7.x |
| Tests | pytest + pytest-asyncio + httpx | — |
| Contenedor | Docker | — |

---

## Endpoints disponibles

Todos los endpoints llevan el prefijo `/api/v1`. Los endpoints marcados con rol requieren un JWT válido en `Authorization: Bearer <token>`.

Los endpoints de listado aceptan `?skip=0&limit=N` para paginación.

### Auth
| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| `POST` | `/auth/login` | Público | Email + password → JWT |
| `POST` | `/auth/register` | Público (5 req/min) | Registro de usuario → JWT |

### Users
| Método | Ruta | Rol mínimo | Descripción |
|---|---|---|---|
| `GET` | `/users/me` | Cualquiera | Perfil del usuario autenticado |
| `PATCH` | `/users/me/password` | Cualquiera (5/min) | Cambiar contraseña propia |
| `GET` | `/users` | ADMIN | Listar usuarios (paginado) |
| `POST` | `/users` | ADMIN | Crear usuario con rol concreto |
| `GET` | `/users/{id}` | ADMIN | Obtener usuario por ID |
| `PATCH` | `/users/{id}` | ADMIN | Actualizar email o rol |
| `DELETE` | `/users/{id}` | ADMIN | Eliminar usuario (soft-delete) |

### Organizations
| Método | Ruta | Rol mínimo | Descripción |
|---|---|---|---|
| `POST` | `/organizations` | ADMIN | Crear organización |
| `GET` | `/organizations` | Cualquiera | Listar organizaciones (paginado) |
| `GET` | `/organizations/{id}` | Cualquiera | Obtener organización |
| `PATCH` | `/organizations/{id}` | MANAGER | Actualizar nombre |
| `DELETE` | `/organizations/{id}` | ADMIN | Eliminar organización |

### Projects
| Método | Ruta | Rol mínimo | Descripción |
|---|---|---|---|
| `POST` | `/projects` | MANAGER | Crear proyecto |
| `GET` | `/projects?organization_id=` | Cualquiera | Listar proyectos (paginado) |
| `GET` | `/projects/{id}` | Cualquiera | Obtener proyecto |
| `PATCH` | `/projects/{id}` | MANAGER | Actualizar |
| `DELETE` | `/projects/{id}` | ADMIN | Eliminar |

### Profiles (perfiles de verificación)
| Método | Ruta | Rol mínimo | Descripción |
|---|---|---|---|
| `POST` | `/profiles` | MANAGER | Crear perfil |
| `GET` | `/profiles?organization_id=` | Cualquiera | Listar perfiles (paginado) |
| `GET` | `/profiles/{id}` | Cualquiera | Obtener perfil |
| `PATCH` | `/profiles/{id}` | MANAGER | Actualizar |
| `DELETE` | `/profiles/{id}` | ADMIN | Eliminar |

### Verification Rules (reglas de un perfil)
| Método | Ruta | Rol mínimo | Descripción |
|---|---|---|---|
| `POST` | `/profiles/{id}/rules` | MANAGER (30/min) | Añadir regla al perfil |
| `GET` | `/profiles/{id}/rules` | VIEWER | Listar reglas (ordenadas por `display_order`) |
| `GET` | `/profiles/{id}/rules/{rule_id}` | VIEWER | Obtener regla |
| `PATCH` | `/profiles/{id}/rules/{rule_id}` | MANAGER | Actualizar parámetros, severidad, estado |
| `DELETE` | `/profiles/{id}/rules/{rule_id}` | MANAGER | Eliminar regla |

Plantillas válidas: `RV-01` … `RV-10`. Severidades: `OBLIGATORIA`, `RECOMENDADA`, `INFORMATIVA`.

### Releases
| Método | Ruta | Rol mínimo | Descripción |
|---|---|---|---|
| `POST` | `/releases` | OPERATOR | Crear release |
| `GET` | `/releases?project_id=` | Cualquiera | Listar releases (paginado) |
| `GET` | `/releases/{id}` | Cualquiera | Obtener release |
| `PATCH` | `/releases/{id}` | OPERATOR | Actualizar descripción |
| `DELETE` | `/releases/{id}` | MANAGER | Eliminar release |
| `GET` | `/releases/{id}/results` | VIEWER | Historial de verificaciones |
| `POST` | `/releases/{id}/verify` | OPERATOR (10/min) | Lanzar verificación (encola tarea Celery) |
| `GET` | `/releases/{id}/verify/stream` | VIEWER | **SSE** — stream en tiempo real de resultados |

### Artifacts
| Método | Ruta | Rol mínimo | Descripción |
|---|---|---|---|
| `POST` | `/releases/{id}/artifacts` | OPERATOR (30/min) | Registrar artefacto en la release |
| `GET` | `/releases/{id}/artifacts` | VIEWER | Listar artefactos (paginado) |
| `GET` | `/releases/{id}/artifacts/{artifact_id}` | VIEWER | Obtener artefacto |
| `DELETE` | `/releases/{id}/artifacts/{artifact_id}` | MANAGER | Eliminar artefacto |

Tipos de artefacto permitidos: `TAREA`, `CODIGO`, `DOCUMENTO`, `PRUEBA`, `INCIDENTE`. Cualquier otro valor es rechazado con `422`.

### Connectors
| Método | Ruta | Rol mínimo | Descripción |
|---|---|---|---|
| `POST` | `/organizations/{org_id}/connectors` | MANAGER (20/min) | Registrar conector |
| `GET` | `/organizations/{org_id}/connectors` | VIEWER | Listar conectores (paginado, `?include_inactive=true`) |
| `GET` | `/organizations/{org_id}/connectors/{id}` | VIEWER | Obtener conector |
| `PATCH` | `/organizations/{org_id}/connectors/{id}` | MANAGER | Actualizar nombre o estado |
| `DELETE` | `/organizations/{org_id}/connectors/{id}` | ADMIN | Eliminar conector |
| `POST` | `/organizations/{org_id}/connectors/{id}/test` | MANAGER | Retestar conexión y actualizar estado |

Las credenciales cifradas nunca aparecen en ninguna respuesta de la API.

### Sistema
| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/health` | Estado del servicio: PostgreSQL **y Redis** (`200 ok` / `503 degraded`) |

---

## RBAC — Control de acceso por roles

Los roles siguen una jerarquía estricta. Un rol de nivel superior incluye todos los permisos de los inferiores.

| Rol | Nivel | Puede hacer |
|---|---|---|
| `VIEWER` | 0 | Leer cualquier recurso |
| `OPERATOR` | 1 | Crear releases y artefactos, lanzar verificaciones |
| `MANAGER` | 2 | Crear proyectos/perfiles/conectores/reglas, actualizar recursos, eliminar artefactos |
| `ADMIN` | 3 | Gestión completa: usuarios, organizaciones, eliminar conectores |

La aplicación del rol se hace en `api/dependencies.py` mediante `require_min_role(UserRole.X)`. Los errores de autorización devuelven `403 Forbidden`. Los recursos inexistentes o que pertenecen a otra organización devuelven `404` (para no filtrar la existencia de organizaciones ajenas).

---

## Cola de tareas — Celery + Redis

La verificación de releases es asíncrona. El flujo completo:

```
POST /releases/{id}/verify
  → LaunchVerificationUseCase          # cambia status a EN_VERIFICACION
      → CeleryTaskQueue.enqueue()       # manda mensaje a Redis
          ↓ proceso separado
      → verification_worker.run_verification()
          → carga Release de DB (SQLAlchemy sync)
          → IVerificationEngine.execute_verification()   # motor Rust
          → escribe VerificationResult en DB
          → actualiza status de Release a VALIDA / CON_ADVERTENCIAS / NO_VALIDA

GET /releases/{id}/verify/stream       # SSE — el cliente se suscribe y recibe el resultado
```

### Arrancar el worker

```bash
cd apps/api
PYTHONPATH=src uv run celery -A infrastructure.queue.celery_app:celery_app worker \
    --loglevel=info -Q verification
```

### Consultar estado de una tarea

```python
from infrastructure.queue.celery_app import celery_app
result = celery_app.AsyncResult("task-id-aqui")
print(result.status)   # PENDING | STARTED | SUCCESS | FAILURE
print(result.result)   # dict con verdict y duration_ms si SUCCESS
```

---

## Puesta en marcha

### Con Docker Compose (recomendado)

```bash
# Solo la base de datos y Redis (para desarrollo local con uv)
docker compose up postgres redis -d

# Toda la pila (API + Postgres + Redis)
docker compose up --build
```

### En local (uv)

```bash
cd apps/api

# Instalar dependencias (incluyendo dev)
uv sync --extra dev

# Arrancar servidor (migraciones automáticas al arrancar)
uv run uvicorn src.main:app --reload --port 8000 --app-dir src

# En otra terminal: arrancar worker de Celery
PYTHONPATH=src uv run celery -A infrastructure.queue.celery_app:celery_app worker \
    --loglevel=info -Q verification
```

Verificar que el servidor está operativo:

```bash
curl http://localhost:8000/health
# {"status": "ok", "db": "reachable", "redis": "reachable"}
```

---

## Variables de entorno

Copiar `.env.example` como `.env` y rellenar los valores. Todas son obligatorias salvo `ENCRYPTION_KEY`.

| Variable | Descripción | Ejemplo |
|---|---|---|
| `DATABASE_URL` | DSN de PostgreSQL (psycopg3 async) | `postgresql+psycopg://user:pass@localhost:5432/svaes` |
| `JWT_SECRET_KEY` | Clave de firma JWT — nunca commitear | clave aleatoria ≥ 32 chars |
| `JWT_ALGORITHM` | Algoritmo de firma | `HS256` |
| `JWT_EXPIRE_MINUTES` | TTL del token en minutos | `60` |
| `ENCRYPTION_KEY` | Clave Fernet para cifrado de credenciales de conectores | Generada automáticamente si se omite — **efímera** |
| `ALLOWED_ORIGINS` | Orígenes CORS permitidos (JSON array o lista separada por comas) | `["http://localhost:4200"]` |
| `ENVIRONMENT` | Entorno de ejecución — oculta `/docs` en `production` | `development` \| `production` |
| `CELERY_BROKER_URL` | URL de Redis como broker de Celery | `redis://localhost:6379/0` |
| `CELERY_RESULT_BACKEND` | URL de Redis como backend de resultados | `redis://localhost:6379/0` |

---

## Migraciones de base de datos

Las migraciones se aplican automáticamente al arrancar el servidor (`alembic upgrade head` en el lifespan de FastAPI).

| Revisión | Descripción |
|---|---|
| `2fd6efcfd6c9` | Schema inicial (todas las tablas) |
| `a1b2c3d4e5f6` | Row-Level Security en `projects`, `verification_profiles`, `connector_instances` |

Para crear una nueva migración tras modificar un modelo ORM:

```bash
cd apps/api
uv run alembic revision --autogenerate -m "descripcion_del_cambio"
# Revisar el archivo en alembic/versions/ antes de commitear
uv run alembic upgrade head
```

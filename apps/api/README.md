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
7. [Puesta en marcha](#puesta-en-marcha)
8. [Variables de entorno](#variables-de-entorno)
9. [Migraciones de base de datos](#migraciones-de-base-de-datos)
10. [Pendiente / en progreso](#pendiente--en-progreso)

---

## Visión general

Este servicio actúa como el punto de entrada central de la plataforma SVAES. Es responsable de:

- Gestionar la autenticación y autorización de usuarios (JWT + RBAC por roles).
- Exponer la API REST consumida por los clientes (web, CLI, integraciones CI/CD).
- Orquestar los casos de uso de negocio: creación de organizaciones, gestión de releases, consulta de resultados.
- Delegar las tareas computacionalmente intensivas (análisis estático, ejecución de tests, comparación de artefactos) al **motor de verificación en Rust** mediante colas asíncronas.

---

## Arquitectura

El servicio sigue los principios de **Arquitectura Hexagonal** (_Ports & Adapters_) y **Clean Architecture**. El dominio de negocio permanece completamente aislado de frameworks, bases de datos y protocolos de transporte.

```
┌─────────────────────────────────────────────────────────┐
│                   Adaptadores Primarios                  │
│           api/  ←  REST, JWT, RBAC, rate limiting        │
└──────────────────────────┬──────────────────────────────┘
                           │  invoca
┌──────────────────────────▼──────────────────────────────┐
│                      Aplicación                          │
│          application/  ←  Casos de uso, comandos         │
└──────────┬───────────────────────────────┬──────────────┘
           │  lee/escribe via puertos       │
┌──────────▼──────────┐        ┌───────────▼──────────────┐
│      Dominio        │        │  Adaptadores Secundarios   │
│  domain/            │        │  infrastructure/           │
│  Entidades, Puertos │        │  PostgreSQL, Celery,       │
│  (interfaces)       │        │  Redis, cliente Rust       │
└─────────────────────┘        └───────────────────────────┘
```

Las dependencias apuntan siempre hacia adentro: `infrastructure` y `api` dependen de `application`, que depende de `domain`. El dominio no importa nada externo.

---

## Estructura de directorios

```
apps/api/
├── alembic.ini                         # Configuración de migraciones
├── alembic/
│   ├── env.py                          # Entorno de migraciones (lee DATABASE_URL)
│   └── versions/                       # Historial de migraciones generadas
├── pyproject.toml
├── uv.lock
└── src/
    ├── main.py                         # Punto de entrada FastAPI + lifespan
    │
    ├── domain/
    │   ├── entities/                   # Dataclasses puras (sin ORM)
    │   │   ├── user.py
    │   │   ├── organization.py
    │   │   ├── project.py
    │   │   ├── release.py
    │   │   └── enums.py                # UserRole, ReleaseStatus, etc.
    │   ├── ports/                      # Interfaces de repositorio (abstractos)
    │   └── exceptions.py              # EntityNotFoundError, DuplicateEntityError, etc.
    │
    ├── application/
    │   └── use_cases/                  # Un caso de uso por archivo
    │       ├── user_use_cases.py
    │       ├── organization_use_cases.py
    │       ├── project_use_cases.py
    │       ├── manage_profile.py
    │       ├── create_release.py
    │       └── launch_verification.py
    │
    ├── infrastructure/
    │   ├── config.py                   # Settings (pydantic-settings, todo desde .env)
    │   └── database/
    │       ├── base.py                 # DeclarativeBase de SQLAlchemy
    │       ├── models/                 # Modelos ORM
    │       ├── repositories/          # Implementaciones concretas de los puertos
    │       └── session.py             # Factoría de sesiones async
    │
    └── api/
        ├── dependencies.py            # DI: use cases, get_current_user, require_min_role
        ├── rate_limit.py              # Configuración de slowapi
        ├── routers/                   # Un router por recurso
        │   ├── auth.py
        │   ├── users.py
        │   ├── organizations.py
        │   ├── projects.py
        │   ├── profiles.py
        │   ├── releases.py
        │   └── connectors.py
        └── schemas/                   # Pydantic request/response models
```

---

## Tecnologías principales

| Componente | Tecnología | Versión |
|---|---|---|
| Runtime | Python | 3.11+ |
| Framework HTTP | FastAPI + Uvicorn | 0.136 |
| Base de datos | PostgreSQL | 16 |
| ORM / migraciones | SQLAlchemy + Alembic | 2.x |
| Driver async | psycopg3 (binary) | 3.2 |
| Autenticación | PyJWT + passlib/bcrypt | — |
| Rate limiting | slowapi | 0.1.9 |
| Validación de email | email-validator | 2.2 |
| Configuración | pydantic-settings | 2.x |
| Gestor de paquetes | uv | — |
| Cola de tareas | Celery + Redis | 5.x / 7.x |
| Contenedor | Docker | — |

---

## Endpoints disponibles

Todos los endpoints llevan el prefijo `/api/v1`.

### Auth
| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| `POST` | `/auth/login` | Público | Login con email + password, devuelve JWT |
| `POST` | `/auth/register` | Público (5 req/min) | Registro de nuevo usuario, devuelve JWT |

### Users
| Método | Ruta | Rol mínimo | Descripción |
|---|---|---|---|
| `GET` | `/users/me` | Cualquiera | Perfil del usuario autenticado |
| `GET` | `/users` | ADMIN | Listar todos los usuarios |
| `POST` | `/users` | ADMIN | Crear usuario con rol concreto |
| `GET` | `/users/{id}` | ADMIN | Obtener usuario por ID |
| `PATCH` | `/users/{id}` | ADMIN | Actualizar email o rol |
| `DELETE` | `/users/{id}` | ADMIN | Desactivar usuario (soft delete) |

### Organizations
| Método | Ruta | Rol mínimo | Descripción |
|---|---|---|---|
| `POST` | `/organizations` | ADMIN | Crear organización |
| `GET` | `/organizations` | Cualquiera | Listar organizaciones activas |
| `GET` | `/organizations/{id}` | Cualquiera | Obtener organización |
| `PATCH` | `/organizations/{id}` | MANAGER | Actualizar nombre |
| `DELETE` | `/organizations/{id}` | ADMIN | Desactivar organización (soft delete) |

### Projects
| Método | Ruta | Rol mínimo | Descripción |
|---|---|---|---|
| `POST` | `/projects` | MANAGER | Crear proyecto |
| `GET` | `/projects?organization_id=` | Cualquiera | Listar proyectos de una organización |
| `GET` | `/projects/{id}` | Cualquiera | Obtener proyecto |
| `PATCH` | `/projects/{id}` | MANAGER | Actualizar nombre o descripción |
| `DELETE` | `/projects/{id}` | ADMIN | Eliminar proyecto |

### Profiles (perfiles de verificación)
| Método | Ruta | Rol mínimo | Descripción |
|---|---|---|---|
| `POST` | `/profiles` | MANAGER | Crear perfil de verificación |
| `GET` | `/profiles?organization_id=` | Cualquiera | Listar perfiles de una organización |
| `GET` | `/profiles/{id}` | Cualquiera | Obtener perfil |
| `PATCH` | `/profiles/{id}` | MANAGER | Actualizar nombre |
| `DELETE` | `/profiles/{id}` | ADMIN | Eliminar perfil |

### Releases
| Método | Ruta | Rol mínimo | Descripción |
|---|---|---|---|
| `POST` | `/releases` | OPERATOR | Crear release |
| `GET` | `/releases?project_id=` | Cualquiera | Listar releases de un proyecto |
| `GET` | `/releases/{id}` | Cualquiera | Obtener release |
| `PATCH` | `/releases/{id}` | OPERATOR | Actualizar descripción (solo en estado BORRADOR) |
| `DELETE` | `/releases/{id}` | MANAGER | Eliminar release (solo en estado BORRADOR) |
| `GET` | `/releases/{id}/results` | Cualquiera | Historial de verificaciones |
| `POST` | `/releases/{id}/verify` | OPERATOR | Lanzar verificación |

### Sistema
| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/health` | Estado del servicio y conectividad con la BD (503 si no alcanzable) |

---

## RBAC — Control de acceso por roles

Los roles siguen una jerarquía de niveles. Un rol de nivel superior incluye todos los permisos de los inferiores.

| Rol | Nivel |
|---|---|
| `VIEWER` | 0 |
| `OPERATOR` | 1 |
| `MANAGER` | 2 |
| `ADMIN` | 3 |

La aplicación del rol se hace en `api/dependencies.py` mediante `require_min_role(UserRole.X)`, que se usa directamente como `Depends` en cada endpoint. Los errores de autorización devuelven `403 Forbidden`.

---

## Puesta en marcha

### Con Docker Compose (recomendado)

Desde la raíz del repositorio:

```bash
# Solo la base de datos (para desarrollo local con uv)
docker compose up postgres -d

# Toda la pila (API + Postgres + Redis)
docker compose up --build
```

### En local (desarrollo con uv)

```bash
cd apps/api

# Instalar dependencias
uv sync --extra dev

# Arrancar servidor
uv run uvicorn main:app --reload --port 8000 --app-dir src
```

Las migraciones se aplican automáticamente al arrancar el servidor.

El endpoint de salud confirma que el servicio está operativo:

```bash
curl http://localhost:8000/health
# {"status": "ok", "db": "reachable", "message": "The backend is running correctly"}
```

---

## Variables de entorno

Todas las variables son obligatorias salvo `ENCRYPTION_KEY`. Copiar `.env.example` como `.env` y rellenar los valores.

| Variable | Descripción | Ejemplo |
|---|---|---|
| `DATABASE_URL` | DSN de conexión a PostgreSQL (psycopg3) | `postgresql+psycopg://user:pass@localhost:5432/svaes` |
| `JWT_SECRET_KEY` | Clave para firma de tokens JWT | clave aleatoria larga |
| `JWT_ALGORITHM` | Algoritmo de firma JWT | `HS256` |
| `JWT_EXPIRE_MINUTES` | Tiempo de expiración del token en minutos | `60` |
| `ENCRYPTION_KEY` | Clave Fernet para cifrar credenciales de conectores | generada automáticamente si se omite (efímera) |
| `ALLOWED_ORIGINS` | Lista de orígenes CORS permitidos (JSON array) | `["http://localhost:4200"]` |
| `ENVIRONMENT` | Entorno de ejecución (oculta `/docs` en producción) | `development` \| `production` |

---

## Migraciones de base de datos

Las migraciones se aplican automáticamente al arrancar el servidor (`alembic upgrade head` en el lifespan de FastAPI).

Para crear una nueva migración tras modificar un modelo:

```bash
cd apps/api

# Genera el archivo de migración comparando modelos vs BD
uv run alembic revision --autogenerate -m "descripcion_del_cambio"

# Revisar el archivo generado en alembic/versions/ antes de commitear
# Aplicar manualmente si no quieres reiniciar el servidor
uv run alembic upgrade head
```

---

## Pendiente / en progreso

### Sin implementar

- **Motor de verificación Rust** — `LaunchVerificationUseCase` encola la tarea pero el cliente hacia el motor Rust (`infrastructure/rust_client/`) no existe todavía. Las verificaciones quedan en estado pendiente indefinidamente.
- **Celery workers** — La infraestructura de Redis y Celery está declarada en Docker Compose pero los workers no están implementados. Las tareas de verificación no se procesan.
- **WebSocket / notificaciones en tiempo real** — El flujo de resultados de verificación requiere notificar al cliente cuando termina. De momento solo hay polling via `GET /releases/{id}/results`.
- **Row-Level Security (RLS)** — El aislamiento entre tenants está a nivel de aplicación (filtros en los repositorios). El RLS en PostgreSQL como segunda línea de defensa no está configurado.
- **Endpoint de cambio de contraseña** — No existe `PATCH /users/me/password`. Actualmente no hay forma de cambiar la contraseña desde la API.
- **Paginación** — Los endpoints de listado devuelven todos los registros sin límite. Necesitan `skip`/`limit` o cursor-based pagination.
- **Router de conectores** — `api/routers/connectors.py` existe pero los endpoints de gestión de conectores (crear, probar conexión, listar) no están completamente implementados.

### Parcialmente implementado / mockeado

- **Perfiles de verificación** — El modelo y el CRUD están completos, pero las `VerificationRule` asociadas a un perfil no tienen endpoints propios todavía. Solo se pueden consultar indirectamente.
- **Artefactos de release** — El modelo `ArtifactModel` existe y está en la migración, pero no hay endpoints para subir ni consultar artefactos de un release.
- **Health check** — Prueba la conectividad con PostgreSQL pero no comprueba Redis ni la disponibilidad del motor Rust.
- **Tests de nuevos endpoints** — Los endpoints de CRUD completo (GET, PATCH, DELETE) añadidos en la última iteración tienen cobertura parcial. Los tests de routers necesitan actualización para cubrir los nuevos casos de uso y la aplicación de roles.

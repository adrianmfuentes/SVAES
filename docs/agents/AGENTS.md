# AGENTS.md — Guía para agentes de IA

> Este fichero describe el contexto del proyecto, las convenciones del repositorio y las
> instrucciones operativas que deben respetar los agentes de IA (Copilot, Claude, Cursor,
> etc.) cuando trabajen sobre este código.

---

## 1. Descripción del proyecto

**SVAES** (Sistema de Verificación Automática de Entregas de Software) es una plataforma
académica genérica que automatiza la validación de *releases* de software contra un conjunto
configurable de reglas de verificación (RV-01 a RV-10).

El proyecto es el Trabajo Fin de Grado de **Adrián Martínez Fuentes (UO295454)** en el
Grado en Ingeniería Informática del Software — Universidad de Oviedo (EII).

**No existe entorno de producción real.** Todos los conectores externos (GitLab, Jira, etc.)
son conectores de referencia que implementan el puerto `IConnector`; no son dependencias
obligatorias del núcleo.

---

## 2. Stack tecnológico

| Capa | Tecnología | Versión mínima |
|---|---|---|
| API backend | FastAPI (Python) | 0.136 |
| Lógica de dominio | Python | 3.11 |
| Base de datos | PostgreSQL | 16 |
| ORM / migraciones | SQLAlchemy + Alembic | 2.x / 1.x |
| Motor de verificación | Rust (Actix-web + Rayon) | 1.77 (✅ Implementado — motor completo con evaluación paralela de reglas) |
| Cola de tareas | Celery + Redis | 5.x / 7.x (worker implementado) |
| Frontend | Angular + TypeScript | Angular 17 (en desarrollo) |
| Contenedores | Docker + Docker Compose | 25 / 2.x |

---

## 3. Estructura del repositorio

```
svaes/
├── api/                       # FastAPI — código completo
│   ├── src/
│   │   ├── domain/            # Entidades, puertos (sin dependencias externas)
│   │   ├── application/       # Casos de uso
│   │   │   ├── ports/input/   # Interfaces de servicios (IReleaseService, etc.)
│   │   │   └── ports/output/  # Interfaces de repositorios y servicios externos
│   │   ├── infrastructure/    # Adaptadores (DB, seguridad, workers, routers)
│   │   └── main.py
│   ├── alembic/              # Migraciones de BD
│   ├── tests/                # Tests propios de la API
│   └── pyproject.toml
├── engine/                    # Motor de verificación Rust (completo con evaluador paralelo y 10 reglas)
│   └── src/
├── web/                       # SPA Angular (en desarrollo)
│   └── src/
├── docs/
│   ├── api/                   # Documentación de la API
│   └── agents/                # Especificaciones para agentes
├── scripts/                   # Scripts auxiliares
├── docker-compose.yml         # Servicios: api, postgres, redis
└── tests/                     # Suite de pruebas completa
    ├── unit/                  # ✅ Implementado — domain, application, infrastructure
    └── ...
```

**Estado actual:**
- ✅ Backend FastAPI completo en `api/src/`
- ✅ Worker Celery implementado (`api/src/infrastructure/workers/verification_worker.py`)
- ✅ Motor de verificación Rust completo (`engine/src/` — evaluador, agregador, 10 reglas RV-01 a RV-10)
- ⚠️ Frontend Angular en desarrollo (`web/` con contenido parcial)
- ✅ Routers registrados: auth, organizations, releases, connectors, profiles, tasks, users, custom_roles, dashboard, api_keys, templates, notifications, admin
- ⚠️ Paquetes compartidos pendientes (`packages/` vacío)

---

## 4. Principios de diseño — reglas que el agente DEBE respetar

1. **Regla de dependencia (Clean Architecture):** las dependencias de código sólo pueden
   apuntar hacia el interior. `domain/` no importa nada de `application/` ni de
   `infrastructure/`. Cualquier cambio que viole esta regla debe rechazarse.

2. **Genericidad obligatoria:** el núcleo del sistema no puede acoplarse a ninguna
   herramienta externa concreta. Toda integración se realiza implementando `IConnector`.

3. **Motor de verificación:** el motor Rust reside en `engine/` y se comunica con el
   backend vía HTTP (configurable via `ENGINE_URL`). El motor está completamente implementado
   con evaluador paralelo (Rayon) y las 10 reglas RV-01…RV-10. No debe añadirse lógica de acceso a BD ni a conectores dentro
   del engine.

4. **Multi-tenancy:** todos los repositorios y casos de uso deben filtrar obligatoriamente
   por `organization_id`. Un agente no debe generar código que acceda a datos de otra
   organización.

5. **RBAC:** los roles son `U1 < U2 < U3 < U4`. El agente debe respetar los guards
   correspondientes en todo endpoint nuevo.

6. **No referencias a Indra, Multideployment ni Flask:** estos contextos son obsoletos.
   Si aparecen en algún fichero existente, deben eliminarse o generalizarse.

---

## 5. Convenciones de código

### Python (backend — api/src/)
- Formato: **Black** + **isort**. Longitud máxima de línea: 88.
- Tipos: todas las funciones deben estar anotadas. Se usa **Pydantic v2** para modelos.
- Tests: **pytest**. Cobertura mínima objetivo: 80 % en `domain/` y `application/`.
- Migraciones Alembic: un fichero por cambio de esquema, con mensaje descriptivo.
- Estructura interior de `src/`:
  ```
  src/
  ├── domain/           # entities/, enums.py, exceptions.py, ports/
  ├── application/      # use_cases/main/, use_cases/others/, ports/
  ├── infrastructure/   # primary/, secondary/
  ├── core/             # audit.py, config.py, dependencies.py, logger.py, rate_limit.py
  └── main.py
  ```

### TypeScript (frontend — web/)
- Formato: **Prettier** + **ESLint** (angular-eslint).
- Componentes standalone (Angular 17+).

### Rust (engine — engine/)
- Formato: **rustfmt** (configuración por defecto).
- Sin `unsafe` salvo justificación documentada.
- Tests unitarios dentro del mismo módulo (`#[cfg(test)]`).

### Git
- Ramas: `main` (estable), `dev` (integración), `feat/<nombre>`, `fix/<nombre>`.
- Commits en **inglés**, formato Conventional Commits:
  `feat(api): add RV-07 traceability rule`.
- No se hace push directamente a `main`.

---

## 6. Tareas que el agente puede realizar sin confirmación

- Leer y analizar cualquier fichero del repositorio.
- Proponer o generar código nuevo que respete los principios del §4.
- Escribir o actualizar tests unitarios.
- Generar migraciones Alembic a partir de cambios en los modelos SQLAlchemy.
- Actualizar la especificación OpenAPI cuando se añaden endpoints.
- Actualizar este fichero o `SPECS.md` / `API_DOCUMENTATION.md` para reflejar cambios aprobados.

## 7. Tareas que requieren confirmación explícita del desarrollador

- Modificar el esquema de la base de datos (tablas, columnas, tipos enumerados).
- Cambiar la interfaz HTTP entre backend y engine (cuando exista).
- Añadir dependencias nuevas (`pyproject.toml`, `Cargo.toml`, `package.json`).
- Eliminar o renombrar puertos (`IConnector`, `IReleaseRepository`, etc.).
- Cualquier cambio en la lógica de agregación de veredictos (§4 de `SPECS.md`).

---

## 8. Lo que el agente NO debe hacer

- Añadir llamadas de red dentro de `domain/`.
- Instanciar conectores concretos dentro de los casos de uso.
- Hardcodear nombres de herramientas externas (Jira, GitLab, Confluence…) fuera de
  `infrastructure/adapters/`.
- Generar código que omita el filtro por `organization_id`.
- Modificar `verification_result` para que sea mutable después de crearse.

---

## 9. Convenciones de testing

### Tests unitarios (`tests/unit/`)

```
tests/
├── conftest.py              # PYTHONPATH, DATABASE_URL dummy
├── api/
│   └── test_routers.py     # handlers HTTP
├── application/use_cases/
│   ├── test_auth_use_cases.py
│   ├── test_configure_connector.py
│   ├── test_create_release.py
│   ├── test_get_verification_history.py
│   ├── test_launch_verification.py
│   ├── test_manage_profile.py
│   ├── test_organization_use_cases.py
│   └── test_project_use_cases.py
├── domain/
│   ├── test_entities.py    # entidades y enums
│   └── test_ports.py       # puertos (si aplica)
└── infrastructure/
    ├── test_repositories.py # repositorios SQLAlchemy (mockeados)
    └── test_security.py    # JWT, Fernet, MockTaskQueue
```

- Un archivo por módulo: `test_<nombre_del_módulo>.py`
- Una clase por unidad: `class Test<NombreDeLaUnidad>`
- Métodos: `test_<condición>_<resultado_esperado>`
- Entidades de dominio y comandos de aplicación **nunca** se mockean.

### Niveles pendientes (`tests/integration/`, `tests/e2e/`, etc.)

Pendientes de implementar según `tests/README.md`.

---

## 10. Routers registrados en main.py

Los siguientes routers están conectados en `api/src/main.py`:

| Router | Archivo | Descripción |
|--------|---------|-------------|
| auth_router | v1/auth | Autenticación (login, refresh) |
| organizations_router | v1/organizations | Gestión de organizaciones |
| releases_router | v1/releases | Gestión de releases y artefactos |
| connectors_router | v1/connectors | Gestión de conectores |
| profiles_router | v1/profiles | Gestión de perfiles de verificación |
| tasks_router | v1/tasks | Consulta de estado de tareas async |
| users_router | v1/users | Gestión de usuarios |
| custom_roles_router | v1/custom_roles | Roles personalizados |
| dashboard_router | v1/dashboard | Métricas del dashboard |
| api_keys_router | v1/api_keys | Gestión de API keys |
| templates_router | v1/templates | Plantillas de release |
| notifications_router | v1/notifications | Configuración de notificaciones |
| admin_router | v1/admin | Operaciones de administración |

---

*Última actualización: mayo 2026 — Adrián Martínez Fuentes (UO295454)*
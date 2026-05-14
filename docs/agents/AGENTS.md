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
| Frontend | Angular + TypeScript | Angular 17 (pendiente) |
| Motor de verificación | Rust (Actix-web + Rayon) | 1.77 (pendiente) |
| Cola de tareas | Celery + Redis | 5.x / 7.x (pendiente) |
| Contenedores | Docker + Docker Compose | 25 / 2.x |

---

## 3. Estructura del repositorio

```
svaes/
├── apps/
│   ├── api/               # FastAPI — código completo
│   │   ├── src/
│   │   │   ├── domain/    # Entidades, puertos (sin dependencias externas)
│   │   │   ├── application/ # Casos de uso
│   │   │   ├── infrastructure/ # Adaptadores (DB, seguridad, logging)
│   │   │   ├── api/       # Routers FastAPI
│   │   │   └── main.py
│   │   ├── alembic/       # Migraciones de BD
│   │   ├── tests/         # Tests propios de la API (ver tests/)
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   └── web/               # SPA Angular (pendiente — directorio vacío)
├── packages/              # Paquetes internos compartidos (pendiente)
├── tests/                 # Suite de pruebas completa
│   ├── unit/              # ✅ Implementado — domain, application, infrastructure
│   ├── integration/       # ⏳ Pendiente
│   ├── e2e/               # ⏳ Pendiente
│   ├── performance/       # ⏳ Pendiente
│   └── security/           # ⏳ Pendiente
├── scripts/                # Scripts auxiliares
├── docker-compose.yml     # Servicios: api, postgres, redis
└── docs/                  # Documentación técnica (pendiente)
```

**Estado actual:**
- Backend FastAPI completo en `apps/api/src/`
- Frontend Angular pendiente (`apps/web/` vacío)
- Motor Rust pendiente
- Worker Celery pendiente (usa `MockTaskQueue` en tests)
- Paquetes compartidos pendientes (`packages/` vacío)

---

## 4. Principios de diseño — reglas que el agente DEBE respetar

1. **Regla de dependencia (Clean Architecture):** las dependencias de código sólo pueden
   apuntar hacia el interior. `domain/` no importa nada de `application/` ni de
   `infrastructure/`. Cualquier cambio que viole esta regla debe rechazarse.

2. **Genericidad obligatoria:** el núcleo del sistema no puede acoplarse a ninguna
   herramienta externa concreta. Toda integración se realiza implementando `IConnector`.

3. **Motor de verificación:** pending de implementación. Cuando se implemente, el engine
   no realizará llamadas de red. Recibirá un payload JSON del worker (vía HTTP local
   Actix-web) y devolverá el resultado de verificación. No debe añadirse lógica de acceso
   a BD ni a conectores dentro del engine.

4. **Multi-tenancy:** todos los repositorios y casos de uso deben filtrar obligatoriamente
   por `organization_id`. Un agente no debe generar código que acceda a datos de otra
   organización.

5. **RBAC:** los roles son `VIEWER < OPERATOR < MANAGER < ADMIN`. El agente debe
   respetar los guards correspondientes en todo endpoint nuevo.

6. **No referencias a Indra, Multideployment ni Flask:** estos contextos son obsoletos.
   Si aparecen en algún fichero existente, deben eliminarse o generalizarse.

---

## 5. Convenciones de código

### Python (backend — apps/api/src/)
- Formato: **Black** + **isort**. Longitud máxima de línea: 88.
- Tipos: todas las funciones deben estar anotadas. Se usa **Pydantic v2** para modelos.
- Tests: **pytest**. Cobertura mínima objetivo: 80 % en `domain/` y `application/`.
- Migraciones Alembic: un fichero por cambio de esquema, con mensaje descriptivo.
- Estructura interior de `src/`:
  ```
  src/
  ├── domain/           # entities/, ports/, exceptions.py
  ├── application/      # use_cases/
  ├── infrastructure/   # adapters/, database/, security/, logging/
  ├── api/              # routers/, schemas/
  └── main.py
  ```

### TypeScript (frontend — pendiente)
- Formato: **Prettier** + **ESLint** (angular-eslint).
- El cliente REST se generará desde la especificación OpenAPI; no se escriben llamadas
  HTTP a mano.
- Componentes standalone (Angular 17+).

### Rust (engine — pendiente)
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
- Actualizar este fichero o `SPECS.md` / `DESIGN.md` para reflejar cambios aprobados.

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
tests/unit/
├── conftest.py              # PYTHONPATH, DATABASE_URL dummy
├── api/
│   ├── test_dependencies.py # get_current_user
│   └── test_routers.py      # handlers HTTP
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
│   ├── test_entities.py     # entidades y enums
│   └── test_ports.py        # puertos (si aplica)
└── infrastructure/
    ├── test_repositories.py # repositorios SQLAlchemy (mockeados)
    └── test_security.py     # JWT, Fernet, MockTaskQueue
```

- Un archivo por módulo: `test_<nombre_del_módulo>.py`
- Una clase por unidad: `class Test<NombreDeLaUnidad>`
- Métodos: `test_<condición>_<resultado_esperado>`
- Entidades de dominio y comandos de aplicación **nunca** se mockean.

### Niveles pendientes (`tests/integration/`, `tests/e2e/`, etc.)

Pendientes de implementar según `tests/README.md`.

---

*Última actualización: mayo 2026 — Adrián Martínez Fuentes (UO295454)*
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=adrianmfuentes_SVAES&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=adrianmfuentes_SVAES)

# SVAES  
## Sistema de Verificación Automática de Entregas de Software  

Trabajo Fin de Grado  
Grado en Ingeniería Informática del Software  
Universidad de Oviedo  

Autor: Adrián Martínez Fuentes  
Curso: 2025/2026  

---

# 1. Introducción

El Sistema de Verificación Automática de Entregas de Software (SVAES) es una plataforma diseñada para automatizar la validación de entregas de software dentro de procesos de desarrollo modernos basados en integración continua.

El sistema actúa como un mecanismo de control de calidad (Quality Gate), evaluando de forma automática la coherencia, integridad y completitud de los artefactos asociados a una release, mediante la integración con múltiples sistemas externos.

El objetivo principal es eliminar procesos manuales de validación, reducir errores humanos y garantizar la trazabilidad completa del ciclo de vida de las entregas.

---

# 2. Objetivos del sistema

## 2.1 Objetivo general

Diseñar e implementar un sistema extensible y desacoplado capaz de verificar automáticamente entregas de software en entornos multi-herramienta.

## 2.2 Objetivos específicos

- Automatizar la validación de releases  
- Garantizar trazabilidad completa de verificaciones  
- Integrarse con herramientas externas sin acoplamiento  
- Proporcionar métricas y observabilidad del proceso de calidad  
- Permitir su uso como Quality Gate en pipelines CI/CD  

---

# 3. Alcance funcional

El sistema cubre las siguientes capacidades:

- Gestión de organizaciones (multi-tenant)  
- Gestión de proyectos y releases  
- Configuración de conectores externos  
- Definición de perfiles de verificación  
- Ejecución automática de verificaciones  
- Registro de resultados y auditoría  
- Exposición de API REST para integración  

Quedan fuera del alcance:

- Ejecución de pipelines CI/CD  
- Modificación de sistemas externos  
- Análisis predictivo o inteligencia artificial  

---

# 4. Arquitectura del sistema

## 4.1 Enfoque arquitectónico

El sistema adopta una arquitectura híbrida basada en:

- Arquitectura hexagonal (Ports & Adapters)  
- Clean Architecture  

Principio clave:

Las dependencias solo pueden apuntar hacia el dominio.

---

## 4.2 Descomposición en contenedores

El sistema se divide en los siguientes componentes:

- Frontend (Angular SPA)  
- Backend (FastAPI)  
- Motor de verificación (Rust)  
- Cola de tareas (Celery + Redis)  
- Base de datos (PostgreSQL)  
- Conectores externos  

---

## 4.3 Flujo de ejecución

1. El usuario lanza una verificación  
2. El backend valida el estado de la release  
3. Se encola una tarea  
4. Un worker procesa la tarea  
5. Se obtienen datos mediante conectores  
6. Se ejecuta el motor  
7. Se guarda el resultado  
8. El frontend consulta el estado  

---

# 5. Modelo de dominio

Entidades principales:

- Organization  
- Project  
- Release  
- Artifact  
- VerificationProfile  
- VerificationRule  
- VerificationResult  
- ConnectorInstance  

Cada verificación almacena un snapshot completo del estado evaluado.

---

# 6. Ciclo de vida de una release

El ciclo de vida de una release define los estados por los que pasa una entrega desde su creación hasta el resultado final de la verificación.

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

| Estado | Descripción |
| --- | --- |
| `BORRADOR` | Release creada, todavía editable y sin enviar a verificación. |
| `PENDIENTE` | Release preparada para ser verificada. |
| `EN_VERIFICACION` | Verificación en curso por parte del worker. |
| `VALIDA` | Release verificada correctamente. |
| `NO_VALIDA` | Release rechazada por incumplir reglas obligatorias. |
| `CON_ADVERTENCIAS` | Release aceptable, pero con incidencias no bloqueantes. |

Estados finales: `VALIDA`, `NO_VALIDA` y `CON_ADVERTENCIAS`.

---

# 7. Motor de verificación

Implementado en Rust.

Características:

- Ejecución paralela  
- Sin llamadas de red  
- Procesamiento en memoria  
- Resultado determinista  

Pipeline:

1. Validación  
2. Evaluación de reglas  
3. Agregación  
4. Veredicto  

---

# 8. Conectores

Puerto principal:

IConnector

Permite integrar sistemas externos sin modificar el núcleo.

---

# 9. Persistencia

Base de datos PostgreSQL:

- UUID como identificadores  
- JSONB para datos dinámicos  
- Integridad referencial  
- Auditoría  

---

# 10. Seguridad

| Capa | Mecanismo | Detalle |
|---|---|---|
| Autenticación | JWT (HS256) | Tokens firmados con `PyJWT`. Claims: `sub`, `role`, `iat`, `exp` |
| Contraseñas | bcrypt (passlib) | Cost factor 12. Comparación en tiempo constante |
| Credenciales conectores | Fernet (AES-128-CBC) | Cifrado autenticado — falla si el ciphertext se modifica |
| Endpoints protegidos | Bearer token | `Authorization: Bearer <jwt>` obligatorio en todos los endpoints de negocio |
| Transacciones | SQLAlchemy `session.begin()` | COMMIT automático en éxito, ROLLBACK automático en excepción |

### Flujo de autenticación

```
POST /api/v1/auth/login
  body: { "email": "...", "password": "..." }
  → verifica bcrypt contra hash en DB
  → devuelve JWT

Peticiones protegidas:
  header: Authorization: Bearer <JWT>
  → get_current_user valida firma + expiración
  → inyecta entidad User al endpoint
  → 401 si token inválido o expirado
```

---

# 11. Tecnologías

- Angular  
- FastAPI  
- Rust  
- PostgreSQL  
- Celery  
- Redis  
- Docker  

---

# 12. Estructura

```text
SVAES/
|-- apps/
|   |-- api/                         # API principal (FastAPI + Python)
|   |   |-- Dockerfile               # Multi-stage: builder → runtime
|   |   |-- pyproject.toml           # Dependencias Python
|   |   `-- src/
|   |       |-- main.py              # Entrada FastAPI (CORS, lifespan, routers)
|   |       |-- api/
|   |       |   |-- dependencies.py  # Inyección de dependencias y get_current_user
|   |       |   |-- routers/         # auth, organizations, projects, profiles, releases, connectors
|   |       |   `-- schemas/         # Pydantic request/response models
|   |       |-- application/
|   |       |   `-- use_cases/       # Casos de uso de la aplicación
|   |       |-- domain/
|   |       |   |-- entities/        # User, Organization, Release, ...
|   |       |   |-- ports/           # Interfaces: IUserRepository, IPasswordHasher, ...
|   |       |   `-- exceptions.py
|   |       `-- infrastructure/
|   |           |-- config.py        # Settings (pydantic-settings, .env)
|   |           |-- database/
|   |           |   |-- base.py
|   |           |   |-- session.py   # AsyncSession con transacciones automáticas
|   |           |   |-- models/      # Modelos SQLAlchemy
|   |           |   `-- repositories/
|   |           |-- security/
|   |           |   |-- password_hasher.py    # BcryptPasswordHasher
|   |           |   |-- jwt_handler.py        # JwtHandler (HS256)
|   |           |   |-- credential_encryptor.py # FernetCredentialEncryptor
|   |           |   `-- mock_task_queue.py
|   |           |-- adapters/
|   |           |   `-- connector_registry.py
|   |           `-- logging/
|   |               `-- logger.py    # get_logger() factory
|   `-- web/                         # Aplicacion frontend
|       |-- public/
|       |-- src/
|       |   |-- app/
|       |   |-- components/
|       |   |-- features/
|       |   |-- hooks/
|       |   |-- pages/
|       |   |-- routes/
|       |   |-- services/
|       |   `-- styles/
|       `-- package.json
|-- docs/
|   |-- api/
|   |   `-- openapi.yaml
|   |-- database/
|   |   `-- erd.puml
|   |-- diagrams/
|   |   |-- exported/
|   |   `-- plantuml/
|   `-- tfg/
|-- packages/
|   |-- application/
|   |   |-- src/
|   |   |   |-- dto/
|   |   |   |-- ports/
|   |   |   |-- services/
|   |   |   `-- use-cases/
|   |   `-- tests/
|   |-- connectors/
|   |   |-- change-management/
|   |   |-- confluence/
|   |   |-- gitlab/
|   |   |-- jira/
|   |   |-- planning/
|   |   `-- shared/
|   |-- domain/
|   |   |-- src/
|   |   |   |-- organizations/
|   |   |   |-- policies/
|   |   |   |-- projects/
|   |   |   |-- releases/
|   |   |   |-- users/
|   |   |   `-- verification/
|   |   `-- tests/
|   |-- infrastructure/
|   |   |-- src/
|   |   |   |-- external/
|   |   |   |-- logging/
|   |   |   |-- persistence/
|   |   |   |-- queue/
|   |   |   `-- security/
|   |   `-- tests/
|   `-- shared/
|       |-- constants/
|       |-- errors/
|       |-- types/
|       `-- utils/
|-- scripts/
|   |-- db/
|   |-- deploy/
|   `-- dev/
|-- tests/
|   |-- e2e/
|   |-- integration/
|   |-- performance/
|   |-- security/
|   `-- unit/
|-- workers/
|   `-- verification-worker/
|       |-- src/
|       |   |-- executors/
|       |   |-- jobs/
|       |   |-- result-writers/
|       |   `-- rules/
|       |-- tests/
|       `-- package.json
|-- .env.example
|-- docker-compose.yml
|-- LICENSE
`-- README.md
```

---

# 13. Variables de entorno

Copia `.env.example` como referencia. Las variables que consume la API Python:

| Variable | Descripción | Obligatoria en prod |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://user:pass@host:5432/db` | Sí |
| `JWT_SECRET_KEY` | Clave de firma de tokens JWT | Sí |
| `JWT_ALGORITHM` | Algoritmo JWT (default: `HS256`) | No |
| `JWT_EXPIRE_MINUTES` | Expiración del token en minutos (default: `60`) | No |
| `ENCRYPTION_KEY` | Clave Fernet para cifrado de credenciales | Sí |

Generar `ENCRYPTION_KEY`:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

# 14. API — Endpoints principales

Base URL: `http://localhost:8000/api/v1`  
Documentación interactiva: `http://localhost:8000/docs`

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| `POST` | `/auth/login` | No | Login → devuelve JWT |
| `POST` | `/organizations` | Sí | Crear organización |
| `GET` | `/organizations` | Sí | Listar organizaciones |
| `POST` | `/projects` | Sí | Crear proyecto |
| `POST` | `/profiles` | Sí | Crear perfil de verificación |
| `POST` | `/releases` | Sí | Crear release |
| `POST` | `/releases/{id}/verify` | Sí | Lanzar verificación |
| `GET` | `/releases/{id}/results` | Sí | Obtener resultados |
| `POST` | `/organizations/{id}/connectors` | Sí | Registrar conector |
| `GET` | `/health` | No | Health check |

---

# 15. Ejecución

## Desarrollo local (con Docker)

```bash
git clone https://github.com/adrianmfuentes/svaes.git
cd svaes
docker compose up --build
```

Docker Compose carga automáticamente `docker-compose.yml` + `docker-compose.override.yml`:
- API en `http://localhost:8000` con **hot reload** — los cambios en `src/` se reflejan sin rebuild
- Swagger UI en `http://localhost:8000/docs`
- PostgreSQL expuesto en `localhost:5432` (usuario: `svaes`, contraseña: `svaes`, db: `svaes`)

## Desarrollo local (sin Docker, solo uvicorn)

```bash
# Levantar solo la BD
docker compose up postgres -d

# Crear apps/api/src/.env con:
# DATABASE_URL=postgresql+psycopg://svaes:svaes@localhost:5432/svaes
# JWT_SECRET_KEY=cualquier-string

cd apps/api
pip install .
cd src
uvicorn main:app --reload
```

## Producción (servidor)

```bash
# Exportar variables reales en el servidor
export DATABASE_URL="postgresql+psycopg://user:pass@host:5432/svaes"
export JWT_SECRET_KEY="clave-larga-aleatoria-segura"
export ENCRYPTION_KEY="$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")"

docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Diferencias con dev: sin hot reload, sin puerto de postgres expuesto, `restart: always`.

---

# 16. Conclusión

El sistema proporciona una solución desacoplada, extensible y robusta para la verificación automática de entregas de software.

---
---

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

---

## 4.2 Container decomposition

The system is divided into the following components:

- Frontend (Angular SPA)  
- Backend (FastAPI)  
- Verification engine (Rust)  
- Task queue (Celery + Redis)  
- Database (PostgreSQL)  
- External connectors  

---

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

# 7. Verification engine

Implemented in Rust.

Characteristics:

- Parallel execution  
- No network calls  
- In-memory processing  
- Deterministic result  

Pipeline:

1. Validation  
2. Rule evaluation  
3. Aggregation  
4. Verdict  

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
|---|---|---|
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

# 12. Structure

```text
SVAES/
|-- apps/
|   |-- api/                         # Main API (FastAPI + Python)
|   |   |-- Dockerfile               # Multi-stage: builder → runtime
|   |   |-- pyproject.toml           # Python dependencies
|   |   `-- src/
|   |       |-- main.py              # FastAPI entry point (CORS, lifespan, routers)
|   |       |-- api/
|   |       |   |-- dependencies.py  # Dependency injection and get_current_user
|   |       |   |-- routers/         # auth, organizations, projects, profiles, releases, connectors
|   |       |   `-- schemas/         # Pydantic request/response models
|   |       |-- application/
|   |       |   `-- use_cases/       # Application use cases
|   |       |-- domain/
|   |       |   |-- entities/        # User, Organization, Release, ...
|   |       |   |-- ports/           # Interfaces: IUserRepository, IPasswordHasher, ...
|   |       |   `-- exceptions.py
|   |       `-- infrastructure/
|   |           |-- config.py        # Settings (pydantic-settings, .env)
|   |           |-- database/
|   |           |   |-- base.py
|   |           |   |-- session.py   # AsyncSession with automatic transactions
|   |           |   |-- models/      # SQLAlchemy models
|   |           |   `-- repositories/
|   |           |-- security/
|   |           |   |-- password_hasher.py    # BcryptPasswordHasher
|   |           |   |-- jwt_handler.py        # JwtHandler (HS256)
|   |           |   |-- credential_encryptor.py # FernetCredentialEncryptor
|   |           |   `-- mock_task_queue.py
|   |           |-- adapters/
|   |           |   `-- connector_registry.py
|   |           `-- logging/
|   |               `-- logger.py    # get_logger() factory
|   `-- web/                         # Frontend application
|       |-- public/
|       |-- src/
|       |   |-- app/
|       |   |-- components/
|       |   |-- features/
|       |   |-- hooks/
|       |   |-- pages/
|       |   |-- routes/
|       |   |-- services/
|       |   `-- styles/
|       `-- package.json
|-- docs/
|   |-- api/
|   |   `-- openapi.yaml
|   |-- database/
|   |   `-- erd.puml
|   |-- diagrams/
|   |   |-- exported/
|   |   `-- plantuml/
|   `-- tfg/
|-- packages/
|-- scripts/
|-- tests/
|-- workers/
|-- .env.example
|-- docker-compose.yml
|-- LICENSE
`-- README.md
```

---

# 13. Environment variables

Copy `.env.example` as a reference. Variables consumed by the Python API:

| Variable | Description | Required in prod |
|---|---|---|
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
|---|---|---|---|
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

Docker Compose automatically loads `docker-compose.yml` + `docker-compose.override.yml`:
- API at `http://localhost:8000` with **hot reload** — changes in `src/` are reflected without rebuild
- Swagger UI at `http://localhost:8000/docs`
- PostgreSQL exposed at `localhost:5432` (user: `svaes`, password: `svaes`, db: `svaes`)

## Local development (without Docker, uvicorn only)

```bash
# Start only the database
docker compose up postgres -d

# Create apps/api/src/.env with:
# DATABASE_URL=postgresql+psycopg://svaes:svaes@localhost:5432/svaes
# JWT_SECRET_KEY=any-string

cd apps/api
pip install .
cd src
uvicorn main:app --reload
```

## Production (server)

```bash
# Export real variables on the server
export DATABASE_URL="postgresql+psycopg://user:pass@host:5432/svaes"
export JWT_SECRET_KEY="long-random-secure-key"
export ENCRYPTION_KEY="$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")"

docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Differences from dev: no hot reload, no exposed postgres port, `restart: always`.

---

# 16. Conclusion

The system provides a decoupled, extensible, and robust solution for automatic software delivery verification.

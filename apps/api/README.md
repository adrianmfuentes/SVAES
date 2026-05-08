# SVAES — API Backend

Backend principal del **Sistema de Verificación Automática de Entregas de Software (SVAES)**. Servicio REST construido sobre **Python 3.11** y **FastAPI**, diseñado para entornos multi-tenant y orquestación de verificaciones de código mediante un motor externo en Rust.

---

## Tabla de contenidos

1. [Visión general](#visión-general)
2. [Arquitectura](#arquitectura)
3. [Estructura de directorios](#estructura-de-directorios)
4. [Tecnologías principales](#tecnologías-principales)
5. [Modelo Multi-tenant](#modelo-multi-tenant)
6. [Motor de verificación Rust](#motor-de-verificación-rust)
7. [Puesta en marcha](#puesta-en-marcha)
8. [Variables de entorno](#variables-de-entorno)

---

## Visión general

Este servicio actúa como el punto de entrada central de la plataforma SVAES. Es responsable de:

- Gestionar la autenticación y autorización de usuarios (JWT + RBAC).
- Exponer la API REST consumida por los clientes (web, CLI, integraciones CI/CD).
- Orquestar los casos de uso de negocio: creación de organizaciones, gestión de entregas, consulta de resultados.
- Delegar las tareas computacionalmente intensivas (análisis estático, ejecución de tests, comparación de artefactos) al **motor de verificación en Rust** mediante colas asíncronas.

---

## Arquitectura

El servicio sigue los principios de **Arquitectura Hexagonal** (_Ports & Adapters_) y **Clean Architecture**. El objetivo central es que el **dominio de negocio permanezca completamente aislado** de frameworks, bases de datos y protocolos de transporte.

```
┌─────────────────────────────────────────────────────────┐
│                      Adaptadores Primarios               │
│              api/  ←  REST, JWT, RBAC, WebSocket         │
└──────────────────────────┬──────────────────────────────┘
                           │  invoca
┌──────────────────────────▼──────────────────────────────┐
│                      Aplicación                          │
│          application/  ←  Casos de uso, DTOs             │
└──────────┬───────────────────────────────┬──────────────┘
           │  lee/escribe via puertos       │
┌──────────▼──────────┐        ┌───────────▼──────────────┐
│      Dominio        │        │   Adaptadores Secundarios  │
│  domain/            │        │   infrastructure/          │
│  Entidades, Puertos │        │   PostgreSQL, Celery,      │
│  (interfaces)       │        │   Redis, cliente Rust      │
└─────────────────────┘        └───────────────────────────┘
```

### Regla de dependencia

Las dependencias apuntan **siempre hacia adentro**: `infrastructure` y `api` dependen de `application`, que a su vez depende de `domain`. El dominio no importa nada externo.

---

## Estructura de directorios

```
apps/api/
├── Dockerfile
├── pyproject.toml
├── alembic.ini                     # Configuración de migraciones de base de datos
└── src/
    ├── main.py                     # Punto de entrada de la aplicación FastAPI
    │
    ├── domain/                     # Núcleo de negocio — sin dependencias externas
    │   ├── entities/               # Entidades puras (dataclasses, sin ORM)
    │   │   └── organization.py     # Raíz del agregado multi-tenant
    │   ├── ports/                  # Interfaces (puertos de salida)
    │   │   └── organization_repository.py
    │   └── exceptions.py           # Excepciones de dominio tipadas
    │
    ├── application/                # Casos de uso — orquestación de lógica de negocio
    │   ├── use_cases/              # Un archivo por caso de uso
    │   └── dtos/                   # Objetos de transferencia de datos (entrada/salida)
    │
    ├── infrastructure/             # Adaptadores secundarios — detalles de implementación
    │   ├── persistence/            # SQLAlchemy 2.x — modelos ORM y repositorios
    │   ├── workers/                # Celery — tareas asíncronas y beat scheduler
    │   └── rust_client/            # Cliente HTTP/gRPC para el motor de verificación Rust
    │
    └── api/                        # Adaptador primario — capa de presentación HTTP
        ├── routers/                # Routers FastAPI agrupados por recurso
        ├── middleware/             # JWT decoding, tenant resolution, logging
        └── dependencies/           # Inyección de dependencias (repositorios, servicios)
```

---

## Tecnologías principales

| Componente | Tecnología | Versión |
|---|---|---|
| Runtime | Python | 3.11 |
| Framework HTTP | FastAPI + Uvicorn | ≥ 0.110 |
| Base de datos | PostgreSQL | 16 |
| ORM / migraciones | SQLAlchemy + Alembic | 2.x |
| Cola de tareas | Celery | 5.x |
| Broker / caché | Redis | 7.x |
| Autenticación | JWT (python-jose) | — |
| Contenedor | Docker | — |

---

## Modelo Multi-tenant

La plataforma está diseñada desde el inicio para soportar **múltiples organizaciones (tenants)** de forma aislada. Cada organización es la raíz del agregado de dominio y actúa como límite de contexto para todos los recursos del sistema (usuarios, cursos, entregas, resultados).

**Características del modelo:**

- Identificación por `UUID v4` para evitar enumeración de recursos.
- `slug` único por organización, usado en las rutas de la API (`/orgs/{slug}/...`).
- Resolución de tenant en la capa de middleware, antes de llegar a los casos de uso.
- Row-Level Security (RLS) en PostgreSQL como segunda línea de defensa.
- Entidades de dominio sin acoplamiento a ningún ORM; la conversión ocurre en la capa de infraestructura.

---

## Motor de verificación Rust

El análisis de entregas (ejecución de tests, análisis estático, comparación de salidas) es delegado a un **servicio independiente escrito en Rust**, optimizado para procesamiento paralelo de alta intensidad computacional.

**Flujo de una verificación:**

```
Cliente HTTP
    │
    ▼
api/  →  application/SubmitDeliveryUseCase
                │
                ▼
        infrastructure/workers/  (Celery task encolada en Redis)
                │
                ▼
        infrastructure/rust_client/  →  Motor Rust (HTTP/gRPC)
                │
                ▼
        Resultado almacenado en PostgreSQL
                │
                ▼
        Notificación al cliente (WebSocket / polling)
```

La separación garantiza que el servicio Python permanece **no bloqueante** y puede escalar horizontalmente de forma independiente al motor de verificación.

---

## Puesta en marcha

### Con Docker Compose (recomendado)

Desde la raíz del repositorio:

```bash
docker compose up --build api
```

### En local (desarrollo)

```bash
cd apps/api
pip install -e ".[dev]"
uvicorn src.main:app --reload --port 8000
```

El endpoint de salud confirma que el servicio está operativo:

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

### Migraciones de base de datos

```bash
cd apps/api
alembic upgrade head
```

---

## Variables de entorno

| Variable | Descripción | Ejemplo |
|---|---|---|
| `DATABASE_URL` | DSN de conexión a PostgreSQL | `postgresql+asyncpg://user:pass@db:5432/svaes` |
| `REDIS_URL` | URL del broker Redis para Celery | `redis://redis:6379/0` |
| `SECRET_KEY` | Clave para firma de tokens JWT | `changeme-in-production` |
| `RUST_ENGINE_URL` | URL base del motor de verificación Rust | `http://rust-engine:50051` |
| `ENVIRONMENT` | Entorno de ejecución | `development` \| `production` |

---
---

# SVAES — API Backend

Main backend of the **Automatic Software Delivery Verification System (SVAES)**. REST service built on **Python 3.11** and **FastAPI**, designed for multi-tenant environments and orchestration of code verifications via an external Rust engine.

---

## Table of contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Directory structure](#directory-structure)
4. [Main technologies](#main-technologies)
5. [Multi-tenant model](#multi-tenant-model)
6. [Rust verification engine](#rust-verification-engine)
7. [Getting started](#getting-started)
8. [Environment variables](#environment-variables)

---

## Overview

This service acts as the central entry point of the SVAES platform. It is responsible for:

- Managing user authentication and authorization (JWT + RBAC).
- Exposing the REST API consumed by clients (web, CLI, CI/CD integrations).
- Orchestrating business use cases: organization creation, delivery management, result queries.
- Delegating computationally intensive tasks (static analysis, test execution, artifact comparison) to the **Rust verification engine** via asynchronous queues.

---

## Architecture

The service follows the principles of **Hexagonal Architecture** (_Ports & Adapters_) and **Clean Architecture**. The central objective is that the **business domain remains completely isolated** from frameworks, databases, and transport protocols.

```
┌─────────────────────────────────────────────────────────┐
│                      Primary Adapters                    │
│              api/  ←  REST, JWT, RBAC, WebSocket         │
└──────────────────────────┬──────────────────────────────┘
                           │  invokes
┌──────────────────────────▼──────────────────────────────┐
│                      Application                         │
│          application/  ←  Use cases, DTOs                │
└──────────┬───────────────────────────────┬──────────────┘
           │  reads/writes via ports        │
┌──────────▼──────────┐        ┌───────────▼──────────────┐
│       Domain        │        │   Secondary Adapters       │
│  domain/            │        │   infrastructure/          │
│  Entities, Ports    │        │   PostgreSQL, Celery,      │
│  (interfaces)       │        │   Redis, Rust client       │
└─────────────────────┘        └───────────────────────────┘
```

### Dependency rule

Dependencies always point **inward**: `infrastructure` and `api` depend on `application`, which in turn depends on `domain`. The domain imports nothing external.

---

## Directory structure

```
apps/api/
├── Dockerfile
├── pyproject.toml
├── alembic.ini                     # Database migration configuration
└── src/
    ├── main.py                     # FastAPI application entry point
    │
    ├── domain/                     # Business core — no external dependencies
    │   ├── entities/               # Pure entities (dataclasses, no ORM)
    │   │   └── organization.py     # Multi-tenant aggregate root
    │   ├── ports/                  # Interfaces (output ports)
    │   │   └── organization_repository.py
    │   └── exceptions.py           # Typed domain exceptions
    │
    ├── application/                # Use cases — business logic orchestration
    │   ├── use_cases/              # One file per use case
    │   └── dtos/                   # Data transfer objects (input/output)
    │
    ├── infrastructure/             # Secondary adapters — implementation details
    │   ├── persistence/            # SQLAlchemy 2.x — ORM models and repositories
    │   ├── workers/                # Celery — async tasks and beat scheduler
    │   └── rust_client/            # HTTP/gRPC client for the Rust verification engine
    │
    └── api/                        # Primary adapter — HTTP presentation layer
        ├── routers/                # FastAPI routers grouped by resource
        ├── middleware/             # JWT decoding, tenant resolution, logging
        └── dependencies/           # Dependency injection (repositories, services)
```

---

## Main technologies

| Component | Technology | Version |
|---|---|---|
| Runtime | Python | 3.11 |
| HTTP framework | FastAPI + Uvicorn | ≥ 0.110 |
| Database | PostgreSQL | 16 |
| ORM / migrations | SQLAlchemy + Alembic | 2.x |
| Task queue | Celery | 5.x |
| Broker / cache | Redis | 7.x |
| Authentication | JWT (python-jose) | — |
| Container | Docker | — |

---

## Multi-tenant model

The platform is designed from the ground up to support **multiple organizations (tenants)** in isolation. Each organization is the root of the domain aggregate and acts as a context boundary for all system resources (users, courses, deliveries, results).

**Model characteristics:**

- `UUID v4` identification to prevent resource enumeration.
- Unique `slug` per organization, used in API routes (`/orgs/{slug}/...`).
- Tenant resolution in the middleware layer, before reaching use cases.
- Row-Level Security (RLS) in PostgreSQL as a second line of defense.
- Domain entities with no ORM coupling; conversion occurs in the infrastructure layer.

---

## Rust verification engine

Delivery analysis (test execution, static analysis, output comparison) is delegated to an **independent service written in Rust**, optimized for high-intensity parallel processing.

**Verification flow:**

```
HTTP Client
    │
    ▼
api/  →  application/SubmitDeliveryUseCase
                │
                ▼
        infrastructure/workers/  (Celery task enqueued in Redis)
                │
                ▼
        infrastructure/rust_client/  →  Rust Engine (HTTP/gRPC)
                │
                ▼
        Result stored in PostgreSQL
                │
                ▼
        Notification to client (WebSocket / polling)
```

This separation guarantees that the Python service remains **non-blocking** and can scale horizontally independently from the verification engine.

---

## Getting started

### With Docker Compose (recommended)

From the repository root:

```bash
docker compose up --build api
```

### Locally (development)

```bash
cd apps/api
pip install -e ".[dev]"
uvicorn src.main:app --reload --port 8000
```

The health endpoint confirms the service is running:

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

### Database migrations

```bash
cd apps/api
alembic upgrade head
```

---

## Environment variables

| Variable | Description | Example |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection DSN | `postgresql+asyncpg://user:pass@db:5432/svaes` |
| `REDIS_URL` | Redis broker URL for Celery | `redis://redis:6379/0` |
| `SECRET_KEY` | JWT token signing key | `changeme-in-production` |
| `RUST_ENGINE_URL` | Base URL of the Rust verification engine | `http://rust-engine:50051` |
| `ENVIRONMENT` | Execution environment | `development` \| `production` |

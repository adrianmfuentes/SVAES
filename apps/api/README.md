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

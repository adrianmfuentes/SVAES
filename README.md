[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=adrianmfuentes_SVAES&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=adrianmfuentes_SVAES)
[![Status](https://img.shields.io/badge/TFG-Finalizado-success)](https://github.com/adrianmfuentes/SVAES)
[![Deploy](https://img.shields.io/badge/Deploy-Producción-blue)](https://github.com/adrianmfuentes/SVAES)

**[English](README.en.md)** · **[Français](README.fr.md)**

# SVAES

## Sistema de Verificación Automática de Entregas de Software

Trabajo Fin de Grado — Finalizado
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

# 3. Estado del proyecto

| Componente       | Estado           |
| ---------------- | ---------------- |
| Backend FastAPI  | API REST completa con todos los endpoints                 |
| Frontend Angular | SPA con autenticación, dashboard, releases, conectores, perfil, admin, i18n ES/EN/FR, 2FA, diseño responsivo, accesibilidad WCAG 2.1 AA, eliminación de cuenta con transferencia automática de propiedad |
| Motor Rust       | Motor completo en engine/, evaluador paralelo + 10 reglas |
| Worker Celery    | Worker real en verification_worker.py                     |
| Conectores       | 20 conectores en 5 categorías funcionales                 |
| Despliegue       | Desplegado en producción con Docker Compose + Oracle Cloud |

---

# 4. Alcance funcional

El sistema cubre las siguientes capacidades:

- Gestión de organizaciones (multi-tenant)
- Gestión de proyectos y releases
- **Configuración de conectores externos (20 implementaciones)**
- Definición de perfiles de verificación
- Ejecución automática de verificaciones
- Registro de resultados y auditoría
- Exposición de API REST para integración

Quedan fuera del alcance:

- Ejecución de pipelines CI/CD
- Modificación de sistemas externos
- Análisis predictivo o inteligencia artificial

---

# 5. Arquitectura del sistema

## 5.1 Enfoque arquitectónico

El sistema adopta una arquitectura híbrida basada en:

- Arquitectura hexagonal (Ports & Adapters)
- Clean Architecture

Principio clave:

> Las dependencias solo pueden apuntar hacia el dominio.

## 5.2 Descomposición en contenedores

El sistema se divide en los siguientes componentes:

- Frontend (Angular SPA)
- Backend (FastAPI)
- Motor de verificación (Rust)
- Cola de tareas (Celery + Redis)
- Base de datos (PostgreSQL)
- Conectores externos

## 5.3 Estructura del backend

```
api/src/
├── domain/                    # Entidades, enums, excepciones
│   ├── entities/              # User, Organization, Project, Release, Artifact, ConnectorInstance
│   └── enums.py               # UserRole, ConnectorType, ConnectorImplementation, etc.
│
├── application/               # Casos de uso (lógica de negocio)
│   ├── ports/
│   │   ├── input/             # IReleaseService, IConnectorService, etc.
│   │   └── output/            # IUserRepository, IConnectorRegistry, IConnector
│   └── use_cases/             # Implementaciones de casos de uso
│
├── infrastructure/            # Adaptadores
│   ├── primary/
│   │   ├── routers/           # Endpoints FastAPI (v1)
│   │   └── middleware/         # JWT, rate limiting, password hasher
│   └── secondary/
│       ├── database/          # SQLAlchemy models + repositories
│       ├── queue/             # Celery + Redis
│       └── connectors/         # Implementaciones de conectores
│           ├── task_management/   # Jira, Linear, Trello, Asana
│           ├── source_control/    # GitHub, GitLab, Bitbucket, Gitea
│           ├── documentation/       # Confluence, Notion, Wiki.js, BookStack
│           ├── planning/           # ClickUp, Taiga, Plane, Miro
│           └── change_management/  # Jira SM, GLPI, Zammad, Redmine
│
└── core/                      # Config, dependencies, rate limiting
```

---

# 6. Sistema de conectores

## 6.1 Arquitectura de dos niveles

El sistema de conectores sigue un diseño de **dos niveles**:

| Concepto                    | Descripción             | Ejemplos                                             |
| --------------------------- | ----------------------- | ---------------------------------------------------- |
| **ConnectorType**           | Tipo funcional genérico | `GESTOR_TAREAS`, `REPO_CODIGO`, `SISTEMA_DOCUMENTAL` |
| **ConnectorImplementation** | Implementación concreta | `JIRA`, `GITHUB`, `CONFLUENCE`, `LINEAR`             |

Un manager configura en su organización qué implementaciones concretas quiere usar para cada tipo funcional.

## 6.2 Tipos funcionales disponibles

| Tipo                        | Descripción                                                           |
| --------------------------- | --------------------------------------------------------------------- |
| `GESTOR_TAREAS`             | Herramientas que rastrean trabajo diario, historias de usuario y bugs |
| `REPO_CODIGO`               | Fuentes de verdad para ramas, commits y etiquetas de versión          |
| `SISTEMA_DOCUMENTAL`        | Informes de pruebas, manuales técnicos y planes de entrega            |
| `HERRAMIENTA_PLANIFICACION` | Roadmap a largo plazo, épicas y planes de versiones                   |
| `GESTION_CAMBIOS`           | Sistemas ITSM para aprobaciones formales, CABs e incidencias          |

---

# 7. Modelo de dominio

Entidades principales:

- **Organization** — Tenant principal con owner
- **User** — Usuario con rol y organización
- **Project** — Pertenece a una org, tiene perfil de verificación
- **Release** — Versión de software con estado y artefactos
- **Artifact** — Referencia externa vinculada a una release
- **ConnectorInstance** — Configuración de un conector en una org
- **VerificationProfile** — Conjunto de reglas para un proyecto
- **VerificationRule** — Plantilla con severidad y parámetros
- **VerificationResult** — Resultado de una verificación con veredicto

---

# 8. Ciclo de vida de una release

```text
BORRADOR → PENDIENTE → EN_VERIFICACION → VALIDA
    │           │              │
    │           └──────────────┴──→ NO_VALIDA
    │                               │
    └───────────────────────────────┴──→ CON_ADVERTENCIAS
    │
    └──────────────────────────────────→ ARCHIVADA
```

| Estado             | Descripción                                                   |
| ------------------ | ------------------------------------------------------------- |
| `BORRADOR`         | Release creada, todavía editable y sin enviar a verificación. |
| `PENDIENTE`        | Release preparada para ser verificada.                        |
| `EN_VERIFICACION`  | Verificación en curso por parte del worker.                   |
| `VALIDA`           | Release verificada correctamente.                             |
| `NO_VALIDA`        | Release rechazada por incumplir reglas obligatorias.          |
| `CON_ADVERTENCIAS` | Release aceptable, pero con incidencias no bloqueantes.       |

---

# 9. Persistencia

Base de datos PostgreSQL:

- UUID como identificadores
- JSONB para datos dinámicos
- Integridad referencial
- Auditoría de cambios

---

# 10. Seguridad

| Capa                     | Mecanismo                    | Detalle                                              |
| ------------------------ | ---------------------------- | ---------------------------------------------------- |
| Autenticación            | JWT (HS256)                  | Tokens firmados. Claims: `sub`, `role`, `iat`, `exp` |
| Doble factor (2FA)       | TOTP (pyotp + segno)         | Autenticación de dos pasos opcional por usuario      |
| Contraseñas              | bcrypt (passlib)             | Cost factor 12. Comparación en tiempo constante      |
| Credenciales conectores  | Fernet (AES-128-CBC)         | Cifrado autenticado                                  |
| Endpoints protegidos     | Bearer token                 | `Authorization: Bearer <jwt>` obligatorio            |
| Aislamiento multi-tenant | Filtro por `organization_id` | 403 en acceso cruzado                                |
| Rate limiting            | slowapi                      | 30 req/min en auth, 100 req/min reads, 20 req/min writes |
| Fuerza bruta             | Bloqueo de cuenta            | 5 intentos fallidos → 15 min bloqueo                 |
| Auditoría GDPR           | audit_log (PostgreSQL)       | Trazabilidad completa; pseudonimización en verificaciones |

---

# 11. Tecnologías

| Capa               | Tecnología               |
| ------------------ | ------------------------ |
| API Backend        | FastAPI (Python 3.11+)   |
| Base de datos      | PostgreSQL 16            |
| ORM                | SQLAlchemy 2.x           |
| Migraciones        | Alembic                  |
| Autenticación      | JWT (PyJWT)              |
| HTTP Client        | httpx (async)            |
| Frontend           | Angular 21               |
| Motor verificación | Rust (Actix-web + Rayon) |
| Cola de tareas     | Celery + Redis           |
| Contenedores       | Docker + Docker Compose  |

---

# 12. Variables de entorno

| Variable             | Descripción                                     | Obligatoria |
| -------------------- | ----------------------------------------------- | ----------- |
| `DATABASE_URL`       | `postgresql+asyncpg://user:pass@host:5432/db`   | Sí          |
| `JWT_SECRET_KEY`     | Clave de firma de tokens JWT                    | Sí          |
| `JWT_ALGORITHM`      | Algoritmo JWT (default: `HS256`)                | No          |
| `JWT_EXPIRE_MINUTES` | Expiración del token en minutos (default: `60`) | No          |
| `ENCRYPTION_KEY`     | Clave Fernet para cifrado de credenciales       | Sí          |
| `ENVIRONMENT`        | `development` o `production`                    | No          |
| `ALLOWED_ORIGINS`    | Orígenes CORS separados por coma                | No          |

Generar `ENCRYPTION_KEY`:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

# 13. API — Endpoints principales

Base URL: `http://localhost:8000/api/v1`
Documentación interactiva: `http://localhost:8000/docs`

### Autenticación

| Método | Ruta                   | Auth | Descripción                     |
| ------ | ---------------------- | ---- | ------------------------------- |
| `POST` | `/auth/login`          | No   | Login → devuelve JWT (paso 1 si 2FA activo) |
| `POST` | `/auth/2fa/verify`     | No   | Verificar código TOTP (paso 2)  |
| `POST` | `/auth/refresh`        | No   | Refrescar token                 |
| `POST` | `/auth/register`       | No   | Registro con aceptación de términos |

### Organizaciones

| Método | Ruta                                 | Auth     | Descripción        |
| ------ | ------------------------------------ | -------- | ------------------ |
| `GET`  | `/organizations`                     | ADMIN    | Listar todas       |
| `POST` | `/organizations`                     | ADMIN    | Crear              |
| `GET`  | `/organizations/{org_id}/connectors` | MANAGER+ | Listar conectores  |
| `POST` | `/organizations/{org_id}/connectors` | MANAGER+ | Registrar conector |

### Releases y verificaciones

| Método | Ruta                      | Auth      | Descripción          |
| ------ | ------------------------- | --------- | -------------------- |
| `POST` | `/projects/{id}/releases` | OPERATOR+ | Crear release        |
| `POST` | `/releases/{id}/verify`   | OPERATOR+ | Lanzar verificación  |
| `GET`  | `/releases/{id}/results`  | OPERATOR+ | Historial resultados |

### Conectores

| Método | Ruta                    | Auth              | Descripción                     |
| ------ | ----------------------- | ----------------- | ------------------------------- |
| `GET`  | `/connectors/types`     | Cualquier usuario | Listar tipos e implementaciones |
| `POST` | `/connectors/{id}/test` | MANAGER+          | Probar conexión                 |

---

# 14. Ejecución

## Desarrollo local (con Docker)

```bash
git clone https://github.com/adrianmfuentes/svaes.git
cd svaes
docker compose up --build
```

API: `http://localhost:8000` · Swagger: `http://localhost:8000/docs` · PostgreSQL: `localhost:5432`

## Desarrollo local (sin Docker)

```bash
# Solo la base de datos
docker compose up postgres -d

cd api
pip install -e .
uvicorn src.main:app --reload --port 8000
```

## Producción

```bash
export DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/svaes"
export JWT_SECRET_KEY="clave-larga-aleatoria"
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

---

# 15. Conclusión

El proyecto ha sido finalizado como Trabajo Fin de Grado en la Universidad de Oviedo (2025/2026), pendiente de entrega y defensa. El sistema proporciona una solución desacoplada, extensible y robusta para la verificación automática de entregas de software, actualmente desplegada en producción.

El sistema está completamente operativo con:

- 20 implementaciones de conectores en 5 tipos funcionales
- Frontend Angular con autenticación 2FA, dashboard, gestión de releases y conectores, eliminación de cuenta con transferencia automática de propiedad de organizaciones
- Internacionalización ES/EN/FR en todos los módulos del frontend
- Diseño responsivo: sidebar hamburguesa ≤1024px, tablas con scroll horizontal, grid colapsable ≤768px
- Accesibilidad WCAG 2.1 AA: skip links, ARIA, indicadores de color+texto, focus-visible
- Aislamiento multi-tenant completo con auditoría GDPR
- RBAC con tres roles predefinidos (OPERATOR, MANAGER, ADMIN)
- Suite de pruebas completa: 200+ tests unitarios, 16 de integración, 5 de seguridad, 4 de rendimiento, 12 de aceptación

---

_Última actualización: 25 de junio de 2026 — Adrián Martínez Fuentes (UO295454)_

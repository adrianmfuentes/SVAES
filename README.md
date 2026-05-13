[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=adrianmfuentes_SVAES&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=adrianmfuentes_SVAES)

**[English](README.en.md)** · **[Français](README.fr.md)**

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

# 3. Estado del proyecto

| Componente | Estado | Descripción |
|------------|--------|-------------|
| Backend FastAPI | ✅ Completo | API REST completa con todos los endpoints |
| Frontend Angular | ⏳ Pendiente | SPA vacía, pendiente de implementación |
| Motor Rust | ⏳ Pendiente | engine/ vacío, no implementado aún |
| Worker Celery | ⏳ Pendiente | Usa MockTaskQueue en tests |
| Conectores | ✅ Implementados | 20 conectores en 5 categorías funcionales |

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

- Frontend (Angular SPA) — ⏳ Pendiente
- Backend (FastAPI) — ✅ Completo
- Motor de verificación (Rust) — ⏳ Pendiente
- Cola de tareas (Celery + Redis) — ⏳ Pendiente
- Base de datos (PostgreSQL) — ✅ Operativo
- Conectores externos — ✅ 20 implementaciones

## 5.3 Estructura del backend

```
apps/api/src/
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

| Concepto | Descripción | Ejemplos |
|----------|-------------|----------|
| **ConnectorType** | Tipo funcional genérico | `GESTOR_TAREAS`, `REPO_CODIGO`, `SISTEMA_DOCUMENTAL` |
| **ConnectorImplementation** | Implementación concreta | `JIRA`, `GITHUB`, `CONFLUENCE`, `LINEAR` |

Un manager configura en su organización qué implementaciones concretas quiere usar para cada tipo funcional.

## 6.2 Tipos funcionales disponibles

| Tipo | Descripción |
|------|-------------|
| `GESTOR_TAREAS` | Herramientas que rastrean trabajo diario, historias de usuario y bugs |
| `REPO_CODIGO` | Fuentes de verdad para ramas, commits y etiquetas de versión |
| `SISTEMA_DOCUMENTAL` | Informes de pruebas, manuales técnicos y planes de entrega |
| `HERRAMIENTA_PLANIFICACION` | Roadmap a largo plazo, épicas y planes de versiones |
| `GESTION_CAMBIOS` | Sistemas ITSM para aprobaciones formales, CABs e incidencias |

## 6.3 Implementaciones disponibles

### GESTOR_TAREAS
| Implementación | API | Plan gratuito |
|---------------|-----|--------------|
| Jira | REST v2/v3 | 10 usuarios |
| Linear | GraphQL | Sólido |
| Trello | REST | Muy permisivo |
| Asana | REST | 15 usuarios |

### REPO_CODIGO
| Implementación | API | Plan gratuito |
|---------------|-----|--------------|
| GitLab | REST v4 | Ilimitado |
| GitHub | REST | Ilimitado |
| Bitbucket | REST | 5 usuarios |
| Gitea | REST | Auto-alojado, open source |

### SISTEMA_DOCUMENTAL
| Implementación | API | Plan gratuito |
|---------------|-----|--------------|
| Confluence | REST | 10 usuarios |
| Notion | REST | Muy completo |
| Wiki.js | GraphQL | Auto-alojado, open source |
| BookStack | REST | Auto-alojado, open source |

### HERRAMIENTA_PLANIFICACION
| Implementación | API | Plan gratuito |
|---------------|-----|--------------|
| ClickUp | REST | Muy completo |
| Taiga | REST | Cloud o auto-alojado |
| Plane | REST | Auto-alojado, open source |
| Miro | REST | 3 pizarras |

### GESTION_CAMBIOS
| Implementación | API | Plan gratuito |
|---------------|-----|--------------|
| Jira Service Management | REST | 3 agentes |
| GLPI | REST | Auto-alojado, open source |
| Zammad | REST | Auto-alojado, open source |
| Redmine | REST/XML | Auto-alojado, open source |

## 6.4 Puerto IConnector

```python
class IConnector(Protocol):
    @property
    def connector_type(self) -> str: ...

    @property
    def connector_implementation(self) -> str: ...

    async def test_connection(self, config: Dict[str, Any]) -> bool: ...

    async def fetch_artifact(self, ref: str, config: Dict[str, Any]) -> Dict[str, Any]: ...

    async def list_artifacts(self, filter_params: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]: ...

    def get_metadata(self) -> Dict[str, Any]: ...
```

## 6.5 Flujo de configuración por UI

1. UI consulta `GET /api/v1/connectors/types` para ver implementaciones disponibles
2. UI muestra `config_schema` de cada implementación para renderizar formulario
3. Manager llena formulario y envía `POST /api/v1/organizations/{org_id}/connectors`
4. Sistema guarda `connector_type`, `connector_implementation` y credenciales cifradas
5. En verificación se usa `connector_implementation` para instanciar el conector correcto

---

# 7. Modelo de dominio

Entidades principales:

- **Organization** — Tenant principal con plan y owner
- **User** — Usuario con rol y organización
- **Project** — Pertenece a una org, tiene perfil de verificación
- **Release** — Versión de software con estado y artefactos
- **Artifact** — Referencia externa vinculada a una release
- **ConnectorInstance** — Configuración de un conector en una org
- **VerificationProfile** — Conjunto de reglas para un proyecto
- **VerificationRule** — Plantilla con severidad y parámetros
- **VerificationResult** — Resultado de una verificación con veredicto

Cada verificación almacena un snapshot completo del estado evaluado.

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

| Estado | Descripción |
| --- | --- |
| `BORRADOR` | Release creada, todavía editable y sin enviar a verificación. |
| `PENDIENTE` | Release preparada para ser verificada. |
| `EN_VERIFICACION` | Verificación en curso por parte del worker. |
| `VALIDA` | Release verificada correctamente. |
| `NO_VALIDA` | Release rechazada por incumplir reglas obligatorias. |
| `CON_ADVERTENCIAS` | Release aceptable, pero con incidencias no bloqueantes. |

---

# 9. Persistencia

Base de datos PostgreSQL:

- UUID como identificadores
- JSONB para datos dinámicos
- Integridad referencial
- Auditoría de cambios

---

# 10. Seguridad

| Capa | Mecanismo | Detalle |
| --- | --- | --- |
| Autenticación | JWT (HS256) | Tokens firmados. Claims: `sub`, `role`, `iat`, `exp` |
| Contraseñas | bcrypt (passlib) | Cost factor 12. Comparación en tiempo constante |
| Credenciales conectores | Fernet (AES-128-CBC) | Cifrado autenticado |
| Endpoints protegidos | Bearer token | `Authorization: Bearer <jwt>` obligatorio |
| Aislamiento multi-tenant | Filtro por `organization_id` | 403 en acceso cruzado |
| Rate limiting | slowapi | 100 req/min reads, 20 req/min writes |
| Fuerza bruta | Bloqueo de cuenta | 5 intentos fallidos → 15 min bloqueo |

---

# 11. Tecnologías

| Capa | Tecnología | Estado |
|------|-------------|--------|
| API Backend | FastAPI (Python 3.11+) | ✅ Completo |
| Base de datos | PostgreSQL 16 | ✅ Operativo |
| ORM | SQLAlchemy 2.x | ✅ Operativo |
| Migraciones | Alembic | ✅ Operativo |
| Autenticación | JWT (PyJWT) | ✅ Completo |
| HTTP Client | httpx (async) | ✅ Integrado en conectores |
| Frontend | Angular 17 | ⏳ Pendiente |
| Motor verificación | Rust (Actix-web + Rayon) | ⏳ Pendiente |
| Cola de tareas | Celery + Redis | ⏳ Pendiente |
| Contenedores | Docker + Docker Compose | ✅ Configurado |

---

# 12. Variables de entorno

| Variable | Descripción | Obligatoria |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@host:5432/db` | Sí |
| `JWT_SECRET_KEY` | Clave de firma de tokens JWT | Sí |
| `JWT_ALGORITHM` | Algoritmo JWT (default: `HS256`) | No |
| `JWT_EXPIRE_MINUTES` | Expiración del token en minutos (default: `60`) | No |
| `ENCRYPTION_KEY` | Clave Fernet para cifrado de credenciales | Sí |
| `ENVIRONMENT` | `development` o `production` | No |
| `ALLOWED_ORIGINS` | Orígenes CORS separados por coma | No |

Generar `ENCRYPTION_KEY`:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

# 13. API — Endpoints principales

Base URL: `http://localhost:8000/api/v1`
Documentación interactiva: `http://localhost:8000/docs`

### Autenticación
| Método | Ruta | Auth | Descripción |
| --- | --- | --- | --- |
| `POST` | `/auth/login` | No | Login → devuelve JWT |
| `POST` | `/auth/refresh` | No | Refrescar token |

### Organizaciones
| Método | Ruta | Auth | Descripción |
| --- | --- | --- | --- |
| `GET` | `/organizations` | ADMIN | Listar todas |
| `POST` | `/organizations` | ADMIN | Crear |
| `GET` | `/organizations/{org_id}/connectors` | MANAGER+ | Listar conectores |
| `POST` | `/organizations/{org_id}/connectors` | MANAGER+ | Registrar conector |

### Releases y verificaciones
| Método | Ruta | Auth | Descripción |
| --- | --- | --- | --- |
| `POST` | `/projects/{id}/releases` | OPERATOR+ | Crear release |
| `POST` | `/releases/{id}/verify` | OPERATOR+ | Lanzar verificación |
| `GET` | `/releases/{id}/results` | OPERATOR+ | Historial resultados |

### Conectores
| Método | Ruta | Auth | Descripción |
| --- | --- | --- | --- |
| `GET` | `/connectors/types` | Cualquier usuario | Listar tipos e implementaciones |
| `POST` | `/connectors/{id}/test` | MANAGER+ | Probar conexión |

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

cd apps/api
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

El sistema proporciona una solución desacoplada, extensible y robusta para la verificación automática de entregas de software.

El backend FastAPI está completamente operativo con:
- 20 implementaciones de conectores across 5 tipos funcionales
- Sistema de configuración via UI para managers
- Aislamiento multi-tenant completo
- RBAC con roles predefinidos y personalizados

Pendiente: frontend Angular, motor Rust y worker Celery.

---

*Última actualización: Mayo 2026 — Adrián Martínez Fuentes (UO295454)*
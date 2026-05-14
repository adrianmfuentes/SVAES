# SPECS.md — Especificación funcional de SVAES

> Resumen de referencia rápida de los requisitos del sistema. La especificación completa
> se encuentra en el **Capítulo 4 (SRS)** de la memoria del TFG y en el documento
> `docs/SRS_SVAES.pdf`.

---

## 1. Propósito del sistema

SVAES automatiza la validación de *releases* de software contra un conjunto configurable
de reglas de verificación. Elimina la revisión manual, centraliza la trazabilidad y produce
un veredicto estructurado por cada ejecución.

El sistema es **genérico**: no está acoplado a ninguna herramienta externa concreta.
Cualquier fuente de datos puede integrarse implementando el puerto `IConnector`.

---

## 2. Actores

| ID | Rol | Descripción |
|---|---|---|
| U1 | Viewer | Consulta releases y resultados de verificación. Sin permisos de escritura. |
| U2 | Operator | Crea y gestiona releases; lanza verificaciones. |
| U3 | Manager | Configura conectores, perfiles y plantillas de su organización. |
| U4 | Admin (org) | Gestiona usuarios y organizaciones propias. |
| U5 | Admin global | Administración completa de la plataforma. |

Jerarquía de roles: `VIEWER < OPERATOR < MANAGER < ADMIN`.

---

## 3. Épicas funcionales

### Épica 1 — Multi-tenancy y seguridad (FEAT-01, FEAT-02)
- Organizaciones completamente aisladas (`organization_id` obligatorio en toda consulta).
- Autenticación JWT stateless con refresh token en BD.
- RBAC aplicado en el adaptador HTTP.
- Cifrado AES-256-GCM de credenciales de conector.
- Cumplimiento RGPD y OWASP Top 10 (2021).

### Épica 2 — Gestión de releases (FEAT-03)
- Ciclo de vida: `BORRADOR → PENDIENTE → EN_VERIFICACION → COMPLETADA | RECHAZADA`.
- Artefactos tipados: `TAREA`, `CODIGO`, `DOCUMENTO`.
- Plantillas de release reutilizables por organización.

### Épica 3 — Conectores (FEAT-04)
- Puerto `IConnector` con operaciones: `get_artifact`, `check_connectivity`, `list_artifacts`.
- Conectores de referencia: gestor de tareas genérico, repositorio de código genérico,
  sistema documental genérico.
- Timeout configurable por conector. Reglas sobre conector `INACTIVO` → `NO_EVALUADA`.

### Épica 4 — Perfiles de verificación (FEAT-05)
- Perfil = conjunto de instancias de reglas (RV-01…RV-10) con nivel `OBLIGATORIA | OPCIONAL`.
- Perfil por defecto no eliminable; disponible en todas las organizaciones.
- El perfil se asigna al proyecto; la release hereda el del proyecto (modificable en `BORRADOR`).
- Snapshot inmutable del perfil por cada ejecución (trazabilidad histórica).

### Épica 5 — Motor de verificación (FEAT-06)
- Ejecución asíncrona: backend responde `202 Accepted`; frontend hace polling de estado.
- El motor Rust se ejecuta en `engine/` como microservicio separado, comunica via HTTP.
- Política de agregación de veredictos (ver §4).
- Reglas personalizadas vía fichero de configuración estructurado.
- **Estado actual:** stub en `engine/src/main.rs` — placeholder "Hello World"; implementación completa pendiente.

### Épica 6 — Resultados y trazabilidad (FEAT-07)
- `verification_result` es **inmutable** tras su creación.
- Por cada regla: resultado individual, evidencias, conector consultado, timestamp.
- Dashboard con tasa de éxito, tiempo medio y evolución temporal.

### Épica 7 — Notificaciones y API pública (FEAT-08, FEAT-09)
- API REST documentada con OpenAPI 3.x; cliente Angular generado automáticamente.
- Rate limiting (ventana deslizante, Redis).
- Notificaciones por canal configurable (extensible sin modificar el núcleo).

---

## 4. Política de agregación de veredictos

| Condición | Veredicto global |
|---|---|
| Alguna regla `OBLIGATORIA` → `ERROR` | `NO_VÁLIDA` |
| Todas las `OBLIGATORIA` → `OK` y alguna `OPCIONAL` → `WARNING` | `CON_ADVERTENCIAS` |
| Todas las reglas activas → `OK` | `VÁLIDA` |

Si existe al menos una regla `NO_EVALUADA`, se añade el sufijo `_CON_INCIDENCIAS`
como indicador secundario.

---

## 5. Catálogo de reglas de verificación (RV-01 a RV-10)

| ID | Nombre | Severidad por defecto | Conector requerido |
|---|---|---|---|
| RV-01 | Existencia de artefactos | ERROR | Cualquier conector activo |
| RV-02 | Estado de tareas | ERROR | Gestor de tareas |
| RV-03 | Cobertura documental | ERROR | Conector documental |
| RV-04 | Coherencia de versión | ERROR | Todos los conectores activos |
| RV-05 | Ausencia de elementos bloqueantes | ERROR | Gestor de tareas |
| RV-06 | Completitud de metadatos | WARNING | Cualquier conector activo |
| RV-07 | Trazabilidad bidireccional | WARNING | Gestor de tareas |
| RV-08 | Antigüedad de artefactos | WARNING | Cualquier conector activo |
| RV-09 | Unicidad de referencia externa | ERROR | Cualquier conector activo |
| RV-10 | Regla personalizable (JSONPath/JMESPath) | Configurable | Configurable |

Nuevas reglas pueden añadirse sin modificar el motor (RNF-33).

---

## 6. Requisitos no funcionales clave

| ID | Requisito |
|---|---|
| RNF-01 | Interfaz de usuario usable sin formación específica. |
| RNF-03 | API documentada con OpenAPI; cliente generado automáticamente. |
| RNF-04 | Autenticación JWT + RBAC + rate limiting. |
| RNF-05 | Cumplimiento RGPD; cifrado AES-256-GCM de credenciales. |
| RNF-06 | Tiempo de verificación < 5 s para perfiles estándar (10 reglas, 3 conectores). |
| RNF-07 | Fiabilidad: el motor no debe producir falsos negativos en reglas deterministas. |
| RNF-08 | Despliegue reproducible con Docker Compose. |
| RNF-33 | Extensibilidad de reglas sin modificar el motor. |
| RNF-35 | Trazabilidad completa por verificación (fuente, recurso, resultado, timestamp). |
| RNF-36 | Snapshot inmutable del perfil y artefactos por verificación. |
| RNF-38 | Cumplimiento RGPD en almacenamiento y acceso a datos personales. |
| RNF-39 | Mitigación de riesgos OWASP Top 10 (2021). |
| RNF-40 | API REST legible por máquina (OpenAPI 3.x). |

---

## 7. Casos de uso principales

| ID | Nombre | Actor principal |
|---|---|---|
| CU-01 | Autenticación en el sistema | U1–U5 |
| CU-02 | Ciclo de vida completo de una release | U2–U3 |

El detalle expandido (precondiciones, flujo principal, alternativas, postcondiciones)
se encuentra en la sección 4.8 del SRS.

---

## 8. Estándares y normativa aplicable

- **IEEE 830:1998** — Especificación de Requisitos del Software.
- **UNE 157801:2007** — Proyectos de Sistemas de Información.
- **ISO/IEC 25010:2011** — Modelo de calidad del software (base de los RNF).
- **OpenAPI Specification 3.x** — Contrato de la API REST.
- **RGPD (UE) 2016/679** — Tratamiento de datos personales.
- **OWASP Top 10 (2021)** — Seguridad en aplicaciones web.

---

## 9. Estado de implementación

| Componente | Estado | Notas |
|---|---|---|
| Backend FastAPI | Implementado | `api/src/` — dominio, aplicación, infraestructura completos |
| Worker Celery | Implementado | `api/src/infrastructure/workers/verification_worker.py` — worker real |
| Motor Rust | Stub | `engine/src/main.rs` — placeholder "Hello World"; implementación pendiente |
| Frontend Angular | Parcial | `web/` — contenido parcial en desarrollo |
| Paquetes compartidos | Pendiente | `packages/` — directorio creado, vacío |
| Tests unitarios | Implementado | `tests/unit/` — cobertura domain, application, infrastructure |
| Tests integración | Pendiente | `tests/integration/` — vacío |
| Tests e2e | Pendiente | `tests/e2e/` — vacío |
| Tests rendimiento | Pendiente | `tests/performance/` — vacío |
| Tests seguridad | Pendiente | `tests/security/` — vacío |

**Routers conectados (14 total):**
- auth, organizations, releases, connectors, profiles, tasks, users, custom_roles, dashboard, api_keys, templates, notifications, admin

**Endpoints por router:** 65+ endpoints implementados

---

*Última actualización: mayo 2026 — Adrián Martínez Fuentes (UO295454)*
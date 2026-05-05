# Security Policy — SVAES

**Sistema de Verificación Automática de Entregas de Software**

---

## Versiones soportadas

SVAES se encuentra actualmente en fase de desarrollo activo como Trabajo de Fin de Grado. Solo la rama principal recibe correcciones de seguridad.

| Versión | Soporte de seguridad |
|---------|----------------------|
| `main` (desarrollo) | Activo |
| Releases etiquetadas `v0.x.x` | Solo la última |
| Versiones anteriores | Sin soporte |

---

## Alcance de la política

### En alcance

Las siguientes superficies de ataque son relevantes para este proyecto:

- **API REST** (`apps/api/`): inyección SQL, IDOR, broken authentication, RBAC incorrecto.
- **Autenticación JWT**: algoritmos débiles, ausencia de validación de firma, tokens sin expiración.
- **Aislamiento multi-tenant**: acceso cruzado entre organizaciones, filtración de datos entre tenants.
- **Motor de verificación Rust**: vulnerabilidades en el canal de comunicación API → Motor (deserialización, path traversal en artefactos).
- **Gestión de secretos**: credenciales expuestas en logs, variables de entorno o respuestas HTTP.
- **Dependencias de terceros**: vulnerabilidades CVE conocidas en las dependencias declaradas en `pyproject.toml`.

### Fuera de alcance

- Ataques de denegación de servicio (DoS/DDoS).
- Ingeniería social sobre los mantenedores.
- Vulnerabilidades en la infraestructura de hosting (fuera del control del proyecto).
- Reportes generados automáticamente por herramientas de escaneo sin evidencia de explotabilidad real.

---

## Cómo reportar una vulnerabilidad

Este proyecto es de carácter académico; no existe un programa de recompensas (bug bounty). Se solicita **divulgación responsable** siguiendo estos pasos:

### Opción 1 — GitHub Private Vulnerability Reporting (preferida)

1. Ve a la pestaña **Security** del repositorio en GitHub.
2. Haz clic en **"Report a vulnerability"**.
3. Completa el formulario con la información indicada a continuación.

### Opción 2 — Correo electrónico

Envía un mensaje a **amf13azul@gmail.com** con el asunto:

```
[SVAES][SECURITY] <descripción breve>
```

### Información requerida en el reporte

Para agilizar el análisis, incluye:

| Campo | Descripción |
|-------|-------------|
| **Componente afectado** | `apps/api`, motor Rust, infraestructura, etc. |
| **Tipo de vulnerabilidad** | OWASP Top 10, CWE, o descripción libre |
| **Severidad estimada** | Crítica / Alta / Media / Baja |
| **Pasos para reproducir** | Descripción detallada o PoC mínimo |
| **Impacto potencial** | Qué datos o funcionalidades quedan expuestos |
| **Versión o commit afectado** | Hash de commit o rama |

---

## Tiempos de respuesta

| Acción | Plazo objetivo |
|--------|----------------|
| Acuse de recibo del reporte | 72 horas |
| Confirmación o descarte de la vulnerabilidad | 7 días |
| Publicación de la corrección (si aplica) | 30 días |
| Divulgación pública coordinada | Acordada con el reportador |

Dado que SVAES es un proyecto académico mantenido individualmente, los plazos son orientativos y pueden variar en periodos de evaluación.

---

## Arquitectura de seguridad (referencia)

Las siguientes medidas de seguridad están implementadas o planificadas en el sistema:

| Mecanismo | Estado | Ubicación |
|-----------|--------|-----------|
| Autenticación JWT (HS256/RS256) | Planificado | `apps/api/src/api/` |
| Control de acceso RBAC | Planificado | `apps/api/src/api/middleware/` |
| Aislamiento multi-tenant por organización | Implementado (dominio) | `apps/api/src/domain/` |
| Row-Level Security en PostgreSQL | Planificado | Migraciones Alembic |
| Validación de entrada con Pydantic | Planificado | `apps/api/src/api/` |
| Análisis estático de seguridad (CodeQL) | Activo | `.github/workflows/codeql.yml` |
| Actualización automática de dependencias | Activo | `.github/dependabot.yml` |
| Secretos gestionados por variables de entorno | Activo | `.env` (no versionado) |

---

## Divulgación pública

Una vez corregida la vulnerabilidad, se realizará una divulgación pública coordinada con el reportador. Se dará crédito explícito en el historial de cambios salvo que el reportador prefiera el anonimato.

---

*Política en vigor desde mayo de 2026. Mantenida por [@adrianmfuentes](https://github.com/adrianmfuentes).*

# Walkthrough

Guía práctica para ir de `git clone` a tu primera verificación en menos de una hora. No sustituye a [docs/README.md](README.md) (referencia técnica completa) ni a la memoria del TFG (`Adrian-Memoria-TFG.pdf`, justificación de diseño) — es el puente entre ambos.

## 0. Modelo mental

SVAES es un *quality gate*: se conecta a tus herramientas (GitLab, Jira, Confluence...), evalúa una **release** contra un conjunto configurable de **reglas** y emite un **veredicto**.

| Objeto | Qué es |
|---|---|
| **Organización** | Contenedor multi-tenant. Todo cuelga de aquí. |
| **Proyecto** | Unidad de trabajo dentro de una organización; tiene un perfil de verificación. |
| **Perfil de verificación** | Conjunto de reglas (con severidad) que se aplican a las releases de un proyecto. |
| **Conector** | Credenciales + configuración para leer un sistema externo. |
| **Release** | Lo que se verifica: versión (SemVer), artefactos vinculados, estado. |

Una release se verifica ejecutando las reglas del perfil contra los artefactos que devuelven los conectores. Con eso tienes el 80% del modelo.

**Roles:** `OPERATOR` (estándar: crea releases, lanza verificaciones), `MANAGER` (gestiona conectores/perfiles/reglas de su organización) y `ADMIN` (global). No hay jerarquía de "viewer" separada — todo rol puede leer lo que le pertenece.

## 1. Levantar el entorno

```bash
git clone https://github.com/adrianmfuentes/SVAES.git
cd SVAES
cp .env.example .env      # rellena JWT_SECRET_KEY, ENCRYPTION_KEY, ADMIN_EMAIL, ADMIN_PASSWORD, ...
docker compose up --build
```

Servicios (`docker compose ps`): `postgres`, `redis`, `api`, `worker` (Celery), `engine` (Rust), `web` (Angular).

Con el compose base: API en `http://localhost:8000` (Swagger en `/docs`), frontend en `http://localhost:8880`. Para desarrollo local con hot-reload del frontend en `http://localhost:4200`, usa `docker compose -f docker-compose.yml -f docker-compose.dev.yml up`.

Al arrancar, la API crea automáticamente el usuario administrador con las credenciales de `ADMIN_EMAIL`/`ADMIN_PASSWORD` — no hay organización de ejemplo, la crea el admin en el paso 2.

## 2. Primer login y primera organización

1. Entra en el frontend con `ADMIN_EMAIL` / `ADMIN_PASSWORD`.
2. Activa 2FA desde *Perfil → Seguridad* (recomendado).
3. Como `ADMIN`, crea una organización (*Administración → Organizaciones → Nueva*).
4. Invita o crea un usuario `MANAGER` o `OPERATOR` para esa organización y trabaja como él el resto de la guía — el admin global es para gestionar la instancia, no para operar día a día.

## 3. Crear un proyecto y un perfil de verificación

*Proyectos → Nuevo proyecto* — necesitas un perfil de verificación asociado. Crea uno vacío en *Perfiles* y añádele un par de reglas para empezar (paso 4).

## 4. Elegir reglas de verificación

10 reglas de negocio (RV-01 a RV-10) más `custom_field_check` para condiciones declarativas propias. Tabla completa: [Engine Reference](engine/reference.md#verification-rules).

Para la primera prueba, activa solo **RV-01** (los artefactos existen) y **RV-04** (los campos numéricos son válidos) — no dependen de que tengas todos los conectores configurados. Ve añadiendo el resto a medida que conectes más sistemas.

## 5. Configurar un conector

Un conector = credenciales + tipo + implementación, cifradas con Fernet antes de tocar la base de datos.

**GitLab** (el más rápido para probar): *Organización → Conectores → Añadir → GitLab*, con `base_url` (por defecto `https://gitlab.com/api/v4`), `token` (Personal Access Token, scope `read_api`) y `project_id`. Pulsa **Probar conexión** antes de guardar.

Cada regla declara qué tipo de conector necesita; si falta, esa regla se marca `NOT_EVALUATED` en lugar de romper la verificación entera. Los 20 conectores disponibles están en [docs/README.md](README.md#connector-system-two-level-design).

## 6. Crear una release y verificar

*Proyecto → Releases → Nueva release*: nombre, versión (SemVer, p. ej. `0.1.0-demo`), descripción. Añade artefactos (manual o `POST /releases/{id}/artifacts/import`) y pulsa **Verificar**.

Bajo el capó:
1. `POST /api/v1/releases/{id}/verify` encola un job en Celery.
2. El worker aplica pseudonimización a los metadatos y llama al motor Rust (`POST /api/v1/verify`, autenticado con `ENGINE_API_KEY`).
3. El motor evalúa las reglas activas en paralelo y devuelve resultados por regla.
4. Se agrega el veredicto global (`VALID`, `INVALID` o `VALID_WITH_WARNINGS`) y se persiste — consúltalo en `GET /releases/{id}/results`.

Lógica de agregación: cualquier regla `BLOCKING` en `FAIL` → `INVALID`; si todas las `BLOCKING` pasan pero hay `WARNING` en alguna `NON_BLOCKING` → `VALID_WITH_WARNINGS`; si todo pasa → `VALID`.

## 7. El resto del sistema

- **API keys** (`/users/{user_id}/api-keys`, máx. 5 activas): para integrar en CI/CD. La clave completa (`svk_...`) solo se muestra al crearla.
- **Auditoría**: cada acción sensible queda en `audit_log` — *Administración → Auditoría*.
- **Exportación**: resultados de verificación a PDF, historial de proyecto a CSV.
- **i18n**: frontend en ES/EN/FR.

## 8. Integrar en CI

Ejemplos completos y probados para GitHub Actions y GitLab CI: [`docs/ci-examples/`](ci-examples/). El patrón es crear la release vía API al taggear, lanzar la verificación, hacer polling del resultado y fallar el job si el veredicto no es `VALID`.

## 9. Dónde seguir leyendo

| Necesitas... | Ve a... |
|---|---|
| Referencia técnica completa (arquitectura, seguridad, endpoints) | [docs/README.md](README.md) |
| Referencia completa de la API | `http://localhost:8000/docs` (Swagger) o [docs/api/reference.md](api/reference.md) |
| Detalle del motor de reglas | [docs/engine/reference.md](engine/reference.md) |
| Desplegar en producción | [docs/DEPLOY.md](DEPLOY.md) |
| Justificación de las decisiones de diseño | `Adrian-Memoria-TFG.pdf` |

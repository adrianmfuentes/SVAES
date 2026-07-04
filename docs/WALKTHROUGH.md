# SVAES — Walkthrough

> Guía de primer contacto pensada para quien acaba de clonar el repo y quiere llegar,
> en menos de una hora, a lanzar su primera verificación automática de una entrega
> y entender el veredicto que devuelve el sistema.
>
> Este documento **no sustituye** al `README.md` (instalación fría, variables de
> entorno completas, referencia de API) ni a la memoria del TFG (justificación de
> diseño, decisiones arquitectónicas). Es el *puente* entre ambos: el recorrido
> guiado que te lleva de `git clone` a un `VALIDA` en pantalla.

---

## 0. Antes de empezar

### 0.1 Qué es SVAES en una frase

Una plataforma *quality gate* que se conecta a tus herramientas (GitLab, Jira,
Confluence, ClickUp…), evalúa una entrega de software contra un conjunto
configurable de reglas (RV-01 a RV-10) y emite un veredicto:
`VALIDA`, `NO_VALIDA`, `CON_INCIDENCIAS` o `NO_EVALUADA`.

### 0.2 Modelo mental de los cuatro objetos que vas a manejar

| Objeto        | Qué es                                                                 |
|---------------|------------------------------------------------------------------------|
| **Organización** | Contenedor multi-tenant. Todo cuelga de aquí.                       |
| **Proyecto**  | Unidad de trabajo dentro de una organización. Agrupa entregas y reglas.|
| **Conector**  | Credencial + configuración para hablar con un sistema externo.         |
| **Entrega**   | El artefacto (una release, un tag, un sprint cerrado) que se verifica. |

Si entiendes que **una entrega se verifica ejecutando las reglas del proyecto
contra los datos que devuelven los conectores**, ya tienes el 80% del modelo.

### 0.3 Los cuatro roles (RBAC)

- **U1 — ADMIN global**: administra la instancia. No lo necesitas para probar.
- **U2 — Técnico**: usuario estándar. Es el rol con el que operarás.
- **U3 — Manager / Owner**: dueño de un proyecto. Gestiona miembros y reglas.
- **U4 — Viewer**: solo lectura.

> ⚠️ Ojo con el orden: **Técnico es U2, no U3**. Es la confusión más habitual.

---

## 1. Levantar el entorno

### 1.1 Requisitos

- Docker + Docker Compose v2
- 4 GB de RAM libres (Postgres + Redis + Celery + API + Engine + Front)
- Puertos libres: `4200` (frontend), `8000` (API), `8080` (engine), `5432`, `6379`

### 1.2 Arranque

```bash
git clone https://github.com/adrianmfuentes/SVAES.git
cd SVAES
cp .env.example .env      # revisa las claves marcadas como REQUIRED
docker compose up -d
```

Los seis servicios que verás en `docker compose ps`:

```
svaes-postgres    ← PostgreSQL 17
svaes-redis       ← broker de Celery
svaes-api         ← FastAPI (backend principal)
svaes-worker      ← Celery worker (verificaciones asíncronas)
svaes-engine      ← motor Rust (RV-01…RV-10)
svaes-frontend    ← Angular SPA
```

### 1.3 Comprobación rápida (smoke test)

```bash
curl http://localhost:8000/health          # → {"status":"ok"}
curl http://localhost:8080/health          # → {"status":"ok","rules":10}
open http://localhost:4200                 # → pantalla de login
```

Si alguno de los tres falla, ve al apartado **§8 Troubleshooting**.

### 1.4 Migraciones y bootstrap

En arranque limpio, la API aplica las migraciones de Alembic y crea:

- La organización `Default`.
- El usuario administrador con las credenciales de `.env` (`ADMIN_EMAIL` /
  `ADMIN_PASSWORD`).

Si necesitas relanzar el bootstrap manualmente:

```bash
docker compose exec api alembic upgrade head
docker compose exec api python -m app.bootstrap
```

---

## 2. Primer login

1. Abre `http://localhost:4200`.
2. Entra con `ADMIN_EMAIL` / `ADMIN_PASSWORD`.
3. **Activa 2FA** desde *Perfil → Seguridad* (recomendado). Escanea el QR con
   tu app TOTP y guarda los códigos de recuperación en un sitio seguro.

> El *refresh token* viaja como cookie `HttpOnly`; el *access token* vive en
> memoria del SPA. Si al hacer F5 sigues logueado, es que la cookie funciona.

### 2.1 Crea un usuario de trabajo

Para no operar como ADMIN, crea un usuario U2 (Técnico) desde
*Administración → Usuarios*, ciérrale sesión al admin y vuelve a entrar como él.
El resto del walkthrough asume que estás como U2.

---

## 3. Crear tu primer proyecto

*Proyectos → Nuevo proyecto*.

| Campo       | Valor sugerido para la primera prueba |
|-------------|---------------------------------------|
| Nombre      | `demo-walkthrough`                    |
| Descripción | `Proyecto de prueba del walkthrough`  |
| Owner       | tu usuario (se autoasigna)            |

Al crearlo pasas automáticamente a rol **Manager (U3)** *dentro de ese
proyecto*. Fuera de él sigues siendo U2. Esto es intencional: los roles a
nivel proyecto se guardan en la tabla `user_membership`.

---

## 4. Configurar conectores

Un conector = credenciales + URL base + tipo. Las credenciales se cifran con
Fernet antes de tocar la base de datos, así que puedes usar tokens reales sin
sudores fríos.

### 4.1 Conector de GitLab (el más rápido para probar)

*Proyecto → Conectores → Añadir → GitLab*.

| Campo        | Valor                                              |
|--------------|----------------------------------------------------|
| Nombre       | `gitlab-demo`                                      |
| Base URL     | `https://gitlab.com` (o tu instancia self-hosted)  |
| Token        | Personal Access Token con scopes `read_api,read_repository` |
| Project ID   | ID numérico del proyecto de GitLab a auditar       |

Pulsa **Probar conexión**. Si devuelve verde, guarda.

### 4.2 Conectores opcionales

Puedes añadir los que quieras. Cada regla RV-* declara qué tipo(s) de conector
necesita — si falta el conector que una regla pide, esa regla emitirá
`NO_EVALUADA` en lugar de romper la verificación.

- **Jira**: URL de la instancia + email + API token.
- **Confluence**: mismo formato que Jira.
- **ClickUp**: API token + Team ID.

### 4.3 Nota sobre el port `IConnector`

Todos los conectores implementan la misma interfaz (`IConnector`) en el back.
Si mañana quieres añadir uno nuevo (Azure DevOps, GitHub, Bitbucket…), es lo
único que hay que implementar. La memoria detalla esto en el capítulo 5.

---

## 5. Elegir y configurar reglas de verificación

*Proyecto → Reglas*.

Las diez reglas del motor Rust:

| Regla  | Qué comprueba (resumen)                                            |
|--------|--------------------------------------------------------------------|
| RV-01  | Trazabilidad: cada commit referencia un issue existente            |
| RV-02  | Cobertura de tests reportada por CI supera el umbral configurado   |
| RV-03  | No hay issues bloqueantes abiertos asignados a la entrega          |
| RV-04  | Todos los merge requests están aprobados y mergeados               |
| RV-05  | Documentación mínima presente en Confluence para la versión        |
| RV-06  | El pipeline de CI de la rama de release está en verde              |
| RV-07  | No hay vulnerabilidades críticas abiertas                          |
| RV-08  | Cambios en dependencias justificados en changelog                  |
| RV-09  | Coincidencia de versiones entre tag Git y campos de gestión        |
| RV-10  | Criterios de aceptación de todas las historias del sprint marcados |

> Los detalles exactos de umbrales, campos y comportamiento están en el
> capítulo 6 de la memoria y en `engine/src/rules/README.md` del propio motor.

### 5.1 Empieza con dos reglas, no con las diez

Para la primera vuelta, activa solo **RV-01** y **RV-06**. Ajusta sus
parámetros (por ejemplo, patrón regex del ID de issue para RV-01). Guarda.

Ya podrás lanzar una verificación con sentido sin depender de que estén
correctamente configurados los cuatro conectores.

---

## 6. Lanzar una verificación

*Proyecto → Entregas → Nueva entrega*.

| Campo        | Valor                                                      |
|--------------|-----------------------------------------------------------|
| Identificador| `v0.1.0-demo`                                              |
| Rama / Tag   | El tag o rama de GitLab que quieres auditar                |
| Fecha corte  | Momento respecto al cual se leerán issues, MRs, pipelines  |

Al pulsar **Verificar**, la API:

1. Crea la entrega en estado `PENDIENTE`.
2. Encola un job en Celery.
3. El worker llama al motor Rust vía `POST /verify` con `X-Engine-Api-Key`.
4. El motor ejecuta las reglas activas en paralelo (Rayon).
5. Cada regla devuelve su sub-veredicto y evidencias.
6. Se agrega el veredicto global y se persiste.

**Deberías ver el estado moverse en tiempo real** (la SPA usa polling ligero).
El detalle final aparece en la ficha de la entrega: veredicto global, veredicto
por regla, y evidencias clicables.

### 6.1 Cómo se decide el veredicto global

- Si **todas** las reglas activas devuelven `VALIDA` → `VALIDA`.
- Si alguna devuelve `NO_VALIDA` → `NO_VALIDA`.
- Si no hay ninguna `NO_VALIDA` pero sí incidencias no bloqueantes → `CON_INCIDENCIAS`.
- Si el motor no pudo evaluar (conector caído, credenciales inválidas) →
  `NO_EVALUADA` en esa regla; el global toma el estado más severo del resto.

---

## 7. Recorrido rápido del resto del sistema

Cosas que **no necesitas** para tu primera verificación, pero que descubrirás
en cuanto empieces a usarlo en serio:

- **API keys de proyecto**: para integrar la verificación en un pipeline de CI.
  *Proyecto → Integraciones → API keys*. La clave se muestra **una única vez**
  al crearla; en BD solo queda el hash.
- **Programaciones**: puedes programar verificaciones periódicas (nightly, por
  ejemplo) con expresiones cron.
- **Notificaciones**: hooks salientes a Slack/Teams/email cuando un veredicto
  cambia.
- **Auditoría**: cada acción sensible queda registrada. *Administración → Auditoría*.
- **Idiomas**: la SPA soporta i18n vía ngx-translate. Español e inglés.

---

## 8. Troubleshooting

### El frontend arranca pero da 502 al hacer login
El SPA está listo antes que la API. Espera ~10 s tras `docker compose up`.
`docker compose logs -f api` te dice cuándo Alembic ha terminado.

### El motor devuelve 401
La clave `X-Engine-Api-Key` que usa el worker no coincide con la que espera
el engine. Revisa `ENGINE_API_KEY` en `.env` — tiene que ser el mismo valor
para los servicios `api`, `worker` y `engine`.

### La verificación se queda en `PENDIENTE` para siempre
El worker de Celery no está consumiendo. Comprueba `docker compose logs worker`.
Causa habitual: Redis no arrancó bien; reinicia con `docker compose restart redis worker`.

### El conector de GitLab falla con 403
El token no tiene los scopes correctos. Regenéralo con `read_api` y
`read_repository`. SVAES no necesita permisos de escritura para nada.

### RV-05 sale `NO_EVALUADA` aunque el conector de Confluence está OK
La regla necesita también el conector de Jira (para resolver la versión).
Configura los dos o desactiva RV-05 para la prueba.

### Se me olvidó el TOTP
Como ADMIN puedes resetear el 2FA de otro usuario desde
*Administración → Usuarios*. Si el que se ha quedado fuera es el propio ADMIN:

```bash
docker compose exec api python -m app.cli reset-2fa --email admin@example.com
```

---

## 9. Siguiente paso: integrar en CI

Cuando ya lances verificaciones desde la UI con soltura, el siguiente paso
natural es que tu pipeline lo haga solo al taggear una release. El patrón:

```bash
curl -X POST https://tu-svaes/api/v1/projects/$PROJECT_ID/deliveries \
  -H "Authorization: Bearer $SVAES_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"identifier":"'"$CI_COMMIT_TAG"'","ref":"'"$CI_COMMIT_TAG"'"}'
```

Y luego un *poll* al endpoint de estado, fallando el job de CI si el veredicto
no es `VALIDA`. En `docs/ci-examples/` hay un ejemplo completo para GitLab CI
y otro para GitHub Actions.

---

## 10. Dónde seguir leyendo

| Necesitas…                                | Ve a…                                    |
|-------------------------------------------|------------------------------------------|
| Instalar en producción (Oracle Cloud A1)  | `docs/deployment.md`                     |
| Referencia completa de la API             | `http://localhost:8000/docs` (Swagger)   |
| Añadir un conector nuevo                  | `docs/connectors.md` + memoria cap. 5    |
| Cambiar el comportamiento de una regla    | `engine/src/rules/rv_XX.rs`              |
| Justificación de las decisiones de diseño | Memoria del TFG (`memoria.pdf`)          |

---

*Última revisión: julio 2026.*

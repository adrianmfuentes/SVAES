# Soporte multi-organización

## Motivación

Antes de este cambio, cada usuario tenía **una única organización y un único rol
global** (`user.organization_id` + `user.role`). Un técnico que trabajase para
dos clientes, o un consultor que administrase varias organizaciones, no podía
representarse en el sistema: `invite_user` rechazaba explícitamente añadir a un
usuario ya vinculado a otra organización.

Esto respondía a las siguientes preguntas sobre el sistema anterior:

| Pregunta | Antes | Ahora |
|---|---|---|
| ¿Admin de una org puede ser admin de otra? | No | **Sí** |
| ¿Admin de una org puede ser técnico en otra? | No | **Sí** |
| ¿Técnico de una org puede ser técnico en otra? | No | **Sí** |
| ¿Un usuario puede estar vinculado a +1 org? | No | **Sí** |

## Diseño

Se adopta el patrón habitual en SaaS B2B multi-tenant (GitHub, Slack, Notion):
una sesión (JWT) está siempre **anclada a una organización activa**, pero un
usuario puede tener **múltiples membresías**, cada una con su propio rol
independiente. Cambiar de organización activa reemite el JWT con el `role` y
`organization_id` correctos para esa organización.

```
user (activo)              user_membership (fuente de verdad multi-org)
├─ organization_id  ◄──┐    ├─ user_id
└─ role                └────┤ organization_id
   (= rol en la org         ├─ role          (independiente por fila)
    activa, denormalizado)  └─ unique(organization_id, user_id)
```

- `user.organization_id` / `user.role` siguen existiendo y representan la
  **organización activa** de la sesión — se mantienen para no romper las
  ~10 dependencias de autorización de `core/dependencies.py` que ya
  comparaban contra ellos (`require_project_access`, `require_release_access`,
  `require_connector_access`, etc.), que siguen operando sobre la org activa.
- `user_membership` es la tabla que ya existía en el esquema desde la
  migración inicial (`2fd6efcfd6c9_initial_schema.py`) pero nunca se usaba
  desde el código de aplicación (ver auditoría previa). Se reactivó tal cual
  estaba: `id, organization_id, user_id, role, created_at`,
  `unique(organization_id, user_id)`.
- `require_org_access()` se extendió para aceptar acceso de lectura a una
  organización en la que el usuario tiene membresía aunque no sea su
  organización activa (además del owner y el ADMIN global), sin tocar los
  demás guards que siguen anclados a la org activa — cambio deliberadamente
  acotado para no disparar el alcance de esta primera iteración.

## Cambios de backend

### Dominio y puertos
- `domain/entities/user.py`: `UserMembership` (id, user_id, organization_id,
  role, created_at). Se corrigió un bug latente en el setter de
  `User.organization_id`: append en lugar de reemplazar el valor activo (sólo
  visible al reasignar la org activa a un valor distinto, algo que el código
  anterior nunca hacía).
- `application/use_cases/main/user_service.py::update_user_role`: se detectó
  (con un test) un segundo bug de aliasing durante el desarrollo: al cambiar
  el rol de un usuario en una organización que no es la activa, el código
  devolvía `updated = user` y luego mutaba `updated.role`, lo que también
  corrompía el rol activo en memoria por ser el mismo objeto. Se corrigió
  devolviendo una copia (`dataclasses.replace`) para la respuesta de la API,
  dejando `user` intacto.
- `application/ports/output/i_user_membership_repository.py`: puerto nuevo
  (`create/get/list_by_user/list_by_organization/update_role/delete/
  delete_all_for_user`).

### Infraestructura
- `infrastructure/secondary/database/models/user_membership_model.py`:
  modelo SQLAlchemy sobre la tabla existente.
- `infrastructure/secondary/database/repositories/user_membership_repository.py`:
  implementación SQL del puerto.
- `alembic/versions/u9v0w1x2y3z4_backfill_user_membership.py`: migración de
  **solo datos** (la tabla y sus columnas ya existían) que crea, para cada
  usuario con `organization_id` no nulo, una fila de membership con su rol
  actual — la relación single-org existente se convierte en su primera
  membership.

### Servicios de aplicación
`UserService` y `OrganizationService` reciben `user_membership_repository`
como dependencia **opcional** (`None` por defecto) para no romper la firma en
código/tests existentes; en producción `core/dependencies.py` siempre la
inyecta.

- `UserService.invite_user`: si el usuario ya existe y **no** es miembro de la
  organización destino, se crea una membership adicional con el rol indicado;
  si ya es miembro de esa organización, lanza `DuplicateEntityError`. Si el
  usuario invitado no tenía organización activa, la nueva organización pasa a
  serlo (comportamiento equivalente al anterior para altas nuevas).
- `UserService.update_user_role` / `remove_user_from_organization`: operan
  sobre la membership de la organización indicada, no sobre la org activa del
  usuario. Si la organización afectada es la activa, se sincroniza también
  `user.role` / `user.organization_id`; si no, sólo se actualiza/borra la
  membership (la sesión activa del usuario en otra organización no se ve
  afectada). Al eliminar la membership activa, si quedan otras, la primera
  pasa a ser la nueva organización activa; si no quedan, se limpia (mismo
  comportamiento que antes de esta feature).
- `UserService.list_organization_users`: lista por membership, devolviendo a
  cada miembro con **su rol en esa organización concreta** (puede diferir de
  su rol activo si su sesión está anclada en otra organización).
- `UserService.list_user_organizations(user_id)` (nuevo): todas las
  organizaciones del usuario con su rol en cada una.
- `UserService.switch_active_organization(user_id, organization_id)` (nuevo):
  valida que exista membership y actualiza `user.organization_id`/`role`.
- `UserService.delete_user_account`: la comprobación de "eres owner de una
  organización con otros miembros" ahora recorre **todas** las membership del
  usuario, no sólo la activa.
- `OrganizationService.create_organization`: crea la membership del owner
  junto con el registro de organización.
- `OrganizationService.transfer_ownership`: sincroniza el rol de la
  membership del owner saliente y entrante, además del rol denormalizado en
  `user`.

### API
- `GET /api/v1/users/me/organizations` (nuevo): lista las organizaciones del
  usuario autenticado con su rol en cada una y cuál es la activa.
- `POST /api/v1/users/me/switch-organization` (nuevo): cambia la organización
  activa (requiere membership existente) y reemite `access_token`/
  `refresh_token` con el `organization_id`/`role` actualizados.
- `GET /api/v1/organizations/{org_id}/users`: ahora también accesible a
  miembros de esa organización aunque no sea su organización activa.
- `POST /api/v1/organizations/{org_id}/users/invite`: ya no falla con un
  `assert` al invitar a un usuario ya activo a una segunda organización (no
  recibe un nuevo `activation_token`, así que el email de activación se omite
  y sólo se envía cuando corresponde).

## Cambios de frontend (Angular)

- `core/services/auth.service.ts`: `getMyOrganizations()` y
  `switchOrganization()` (esta última persiste los nuevos tokens y actualiza
  el usuario en `localStorage`).
- `features/layout/shell/shell.component.*`: la organización mostrada en la
  topbar se convierte en un desplegable ("Cambiar de organización") cuando el
  usuario pertenece a más de una; seleccionar otra llama a
  `switchOrganization` y recarga la aplicación para refrescar todo el estado
  anclado a la organización anterior.
- Claves i18n nuevas (`shell.switch_org_label`, `shell.switch_org_current`,
  `shell.switch_org_error`) añadidas a `en.json` y `es.json`.

## Limitaciones conocidas / alcance de esta primera iteración

- Operar dentro de una organización (crear proyectos, releases, conectores,
  perfiles…) sigue requiriendo que esa organización sea la **activa** de la
  sesión — sólo el acceso de lectura a metadatos de organización/miembros se
  extendió a "cualquier organización con membership". Ampliar esto
  (operar sin cambiar de organización activa) es un cambio mayor sobre
  `require_project_access`, `require_release_access`, etc., deliberadamente
  fuera de esta iteración.
- Cambiar de organización activa recarga la página en el frontend en lugar de
  refrescar el estado en memoria; es la opción más simple y segura dado que
  hay componentes que cachean datos por organización.

## Tests

- `tests/unit/test_repositories.py::TestSqlUserMembershipRepository` (10
  tests): CRUD del nuevo repositorio (create/get/list_by_user/
  list_by_organization/update_role/delete/delete_all_for_user), incluyendo
  los casos "no encontrado".
- `tests/unit/test_services.py::TestUserServiceMultiOrg` (12 tests): las
  cuatro preguntas de negocio de la tabla de arriba, cubiertas explícitamente
  (invitar a una segunda organización con rol distinto, rechazo si ya es
  miembro, cambio de rol en organización no-activa sin tocar la activa,
  fallback de organización activa al eliminar membership, listado con rol
  por-organización, `switch_active_organization`, borrado de cuenta
  comprobando todas las membership).
- `tests/unit/test_services.py::TestOrganizationServiceMultiOrg` (2 tests):
  creación de organización crea membership del owner; transferencia de
  ownership sincroniza roles de membership de ambos usuarios.
- `tests/unit/test_core.py` y `tests/unit/test_dependencies_factories.py`:
  actualizados los tests existentes de `require_org_access` para inyectar el
  nuevo `membership_repo` (regresión detectada y corregida durante esta
  implementación).
- Suite completa (`tests/unit`, 1158 tests) ejecutada sin regresiones tras
  el cambio (1158 passed, 0 failed).
- Frontend: `ng build` (configuración development) compila sin errores de
  tipos tras los cambios en `auth.service.ts` y `shell.component.ts`.

No se añadieron tests de integración end-to-end contra una base de datos real
para los dos endpoints nuevos ni para la migración de backfill; ambos se
verificaron por inspección y por los tests unitarios de servicio/repositorio
listados arriba.

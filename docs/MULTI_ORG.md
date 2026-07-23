# Soporte multi-organización

## Motivación

Un usuario puede pertenecer a varias organizaciones a la vez, cada una con su propio rol: un consultor puede ser admin en un cliente y técnico en otro; un técnico puede trabajar para dos organizaciones sin que una excluya a la otra.

## Diseño

Igual que GitHub, Slack o Notion: la sesión (JWT) está siempre **anclada a una organización activa**, pero el usuario puede tener **varias membresías** (`user_membership`), cada una con su propio rol independiente. Cambiar de organización activa reemite el JWT con el `role` y `organization_id` de la nueva organización.

```
user (sesión activa)         user_membership (una fila por organización)
├─ organization_id  ◄────┐   ├─ user_id
└─ role                  └───┤ organization_id
   (rol en la org activa)    ├─ role   (independiente por fila)
                              └─ unique(organization_id, user_id)
```

Las comprobaciones de acceso (`require_project_access`, `require_release_access`, etc.) siguen operando sobre la organización activa: **operar** dentro de una organización (crear proyectos, releases, conectores...) requiere que sea la activa de la sesión. Solo la lectura de metadatos de organización/miembros se extiende a cualquier organización donde el usuario tenga membresía.

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/v1/users/me/organizations` | Lista las organizaciones del usuario, con su rol en cada una y cuál está activa |
| `POST` | `/api/v1/users/me/switch-organization` | Cambia la organización activa (requiere membresía existente); reemite `access_token`/`refresh_token` |

En el frontend, cambiar de organización desde el desplegable de la topbar recarga la aplicación para refrescar el estado que quedaba anclado a la organización anterior.

## Alcance actual

Cambiar de organización activa sin recargar la página, u operar en una organización sin que sea la activa, quedan fuera de esta primera iteración.

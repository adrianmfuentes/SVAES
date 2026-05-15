# Guía para Testear la API con Postman

Esta guía describe cómo usar Postman (o cualquier cliente HTTP similar) para probar los endpoints de la API SVAES.

---

## 1. Configuración del Entorno

### URL Base

```
Development: http://localhost:8000
Production:  https://api.svaes.example.com
```

### Headers Comunes

| Header | Valor |
|--------|-------|
| `Content-Type` | `application/json` |
| `Accept` | `application/json` |

---

## 2. Autenticación

### Login

**Endpoint:** `POST /api/v1/auth/login`

**Request:**
```json
{
  "email": "usuario@ejemplo.com",
  "password": "contraseña123"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "Bearer",
  "user_id": "uuid-del-usuario",
  "role": "U2"
}
```

> Guarda el `access_token` para usar en subsequent requests.

### Usar el Token

En cada request protegida, añade el header:

```
Authorization: Bearer <access_token>
```

### Refrescar Token

**Endpoint:** `POST /api/v1/auth/refresh`

**Request:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

---

## 3. Colección de Requests por Router

### 3.1 Auth (`/api/v1/auth`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/v1/auth/login` | Login con email/password |
| POST | `/api/v1/auth/refresh` | Refrescar access token |

### 3.2 Users (`/api/v1/users`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/users/me` | Perfil del usuario actual |
| PATCH | `/api/v1/users/me` | Actualizar perfil |
| POST | `/api/v1/users/me/password` | Cambiar contraseña |

**GET /api/v1/users/me**

Response:
```json
{
  "id": "uuid",
  "email": "usuario@ejemplo.com",
  "display_name": "Nombre Usuario",
  "role": "U2",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

**PATCH /api/v1/users/me**
```json
{
  "display_name": "Nuevo Nombre"
}
```

**POST /api/v1/users/me/password**
```json
{
  "current_password": "contraseña123",
  "new_password": "nuevaContraseña456",
  "confirm_password": "nuevaContraseña456"
}
```

### 3.3 Organizations (`/api/v1/organizations`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/organizations` | Listar organizaciones (U3) |
| POST | `/api/v1/organizations` | Crear organización (U3) |
| GET | `/api/v1/organizations/{org_id}` | Detalles de org |
| GET | `/api/v1/projects` | Listar proyectos |
| POST | `/api/v1/organizations/{org_id}/projects` | Crear proyecto |

**POST /api/v1/organizations**
```json
{
  "name": "Mi Organización",
  "slug": "mi-organizacion",
  "plan": "default"
}
```

**GET /api/v1/projects**
Query params: `?page=1&size=25&status=ACTIVO&search=nombre&org_id=uuid`

### 3.4 Projects (`/api/v1/projects/{project_id}`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/projects/{project_id}` | Detalles del proyecto |
| PATCH | `/api/v1/projects/{project_id}` | Actualizar proyecto |
| POST | `/api/v1/organizations/{org_id}/projects/{project_id}/archive` | Archivar proyecto |

### 3.5 Releases (`/api/v1/releases`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/v1/projects/{project_id}/releases` | Crear release |
| GET | `/api/v1/projects/{project_id}/releases` | Listar releases |
| GET | `/api/v1/releases/{release_id}` | Detalles de release |
| PATCH | `/api/v1/releases/{release_id}` | Actualizar release |
| DELETE | `/api/v1/releases/{release_id}` | Eliminar release |
| POST | `/api/v1/releases/{release_id}/archive` | Archivar release |
| POST | `/api/v1/releases/{release_id}/verify` | Lanzar verificación |
| GET | `/api/v1/releases/{release_id}/results` | Historial de verificaciones |

**POST /api/v1/projects/{project_id}/releases**
```json
{
  "name": "Release v1.0.0",
  "version": "1.0.0",
  "description": "Primera release",
  "profile_id": "uuid-del-perfil"
}
```

**PATCH /api/v1/releases/{release_id}**
```json
{
  "name": "Release v1.0.1",
  "status": "PENDIENTE"
}
```

**POST /api/v1/releases/{release_id}/verify**
Response (202 Accepted):
```json
{
  "task_id": "uuid-de-la-tarea"
}
```

### 3.6 Artifacts

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/releases/{release_id}/artifacts` | Listar artefactos |
| POST | `/api/v1/releases/{release_id}/artifacts` | Agregar artefacto |
| DELETE | `/api/v1/releases/{release_id}/artifacts/{artifact_id}` | Eliminar artefacto |
| POST | `/api/v1/releases/{release_id}/artifacts/import` | Importar artefactos (JSON array) |

**POST /api/v1/releases/{release_id}/artifacts**
```json
{
  "connector_instance_id": "uuid",
  "connector_implementation": "JIRA",
  "artifact_type": "TAREA",
  "external_ref": "PROJ-123",
  "metadata": {}
}
```

### 3.7 Connectors (`/api/v1/organizations/{org_id}/connectors`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/connectors/types` | Listar tipos de conectores |
| GET | `/api/v1/organizations/{org_id}/connectors` | Listar conectores |
| POST | `/api/v1/organizations/{org_id}/connectors` | Crear conector |
| PATCH | `/api/v1/organizations/{org_id}/connectors/{connector_id}` | Actualizar conector |
| DELETE | `/api/v1/organizations/{org_id}/connectors/{connector_id}` | Eliminar conector |
| POST | `/api/v1/organizations/{org_id}/connectors/{connector_id}/test` | Probar conexión |

**POST /api/v1/organizations/{org_id}/connectors**
```json
{
  "connector_type": "GESTOR_TAREAS",
  "connector_implementation": "JIRA",
  "name": "Mi Conector JIRA",
  "credentials": {
    "api_token": "token-jira",
    "instance_url": "https://mi-empresa.atlassian.net"
  }
}
```

### 3.8 Profiles (`/api/v1/organizations/{org_id}/profiles`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/organizations/{org_id}/profiles` | Listar perfiles |
| POST | `/api/v1/organizations/{org_id}/profiles` | Crear perfil |
| PATCH | `/api/v1/profiles/{profile_id}` | Actualizar perfil |
| DELETE | `/api/v1/profiles/{profile_id}` | Eliminar perfil |

**POST /api/v1/organizations/{org_id}/profiles**
```json
{
  "name": "Perfil de Verificación Estándar",
  "description": "Perfil para releases de producción",
  "is_default": false
}
```

### 3.9 Rules

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/v1/profiles/{profile_id}/rules` | Agregar regla |
| PATCH | `/api/v1/rules/{rule_id}` | Actualizar regla |
| DELETE | `/api/v1/rules/{rule_id}` | Eliminar regla |

**POST /api/v1/profiles/{profile_id}/rules**
```json
{
  "rule_template": "RV-01",
  "severity": "HIGH",
  "params": {},
  "display_order": 0
}
```

### 3.10 Tasks (`/api/v1/tasks/{task_id}`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/tasks/{task_id}` | Estado de tarea async |

Response:
```json
{
  "task_id": "uuid",
  "status": "SUCCESS",
  "result": "Resultado de la tarea"
}
```

### 3.11 Custom Roles (`/api/v1/organizations/{org_id}/roles`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/organizations/{org_id}/roles` | Listar roles |
| POST | `/api/v1/organizations/{org_id}/roles` | Crear rol |
| PATCH | `/api/v1/roles/{role_id}` | Actualizar rol |
| DELETE | `/api/v1/roles/{role_id}` | Eliminar rol |

**POST /api/v1/organizations/{org_id}/roles**
```json
{
  "name": "Supervisor de Releases",
  "permissions": ["VIEW_ORG_PROJECTS", "CREATE_RELEASE", "EXECUTE_VERIFICATION"]
}
```

### 3.12 Dashboard (`/api/v1/dashboard/metrics`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/dashboard/metrics?org_id={org_id}` | Métricas del dashboard |

Response:
```json
{
  "total_releases": 42,
  "valid_releases": 30,
  "invalid_releases": 5,
  "pending_releases": 7,
  "total_verifications": 150,
  "pass_rate": 0.85
}
```

### 3.13 API Keys (`/api/v1/users/{user_id}/api-keys`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/v1/users/{user_id}/api-keys` | Crear API key |
| GET | `/api/v1/users/{user_id}/api-keys` | Listar API keys |
| DELETE | `/api/v1/users/{user_id}/api-keys/{key_id}` | Revocar API key |

**POST /api/v1/users/{user_id}/api-keys**
```json
{
  "name": "Mi API Key para CI/CD",
  "expires_in_days": 90
}
```

> La clave completa solo se retorna al crear. Guárdala porque no se puede recuperar después.

### 3.14 Templates (`/api/v1/templates`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/v1/templates` | Crear template |
| GET | `/api/v1/templates` | Listar templates |
| GET | `/api/v1/templates/{template_id}` | Detalles del template |
| PATCH | `/api/v1/templates/{template_id}` | Actualizar template |
| POST | `/api/v1/templates/{template_id}/archive` | Archivar template |
| POST | `/api/v1/templates/{template_id}/clone` | Clonar template |

### 3.15 Notifications (`/api/v1/notifications`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/notifications/channels` | Listar canales |
| POST | `/api/v1/notifications/channels` | Configurar canal |
| PATCH | `/api/v1/notifications/channels/{channel_id}` | Actualizar canal |
| DELETE | `/api/v1/notifications/channels/{channel_id}` | Eliminar canal |
| GET | `/api/v1/notifications/preferences` | Preferencias del usuario |
| PATCH | `/api/v1/notifications/preferences` | Actualizar preferencias |
| POST | `/api/v1/notifications/subscriptions` | Suscribirse a evento |
| DELETE | `/api/v1/notifications/subscriptions/{event_type}` | Desuscribirse |

### 3.16 Admin (`/api/v1/admin`) - Solo U3

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/v1/admin/rules/reload` | Recargar reglas en caliente |
| GET | `/api/v1/admin/users` | Listar todos los usuarios |
| POST | `/api/v1/admin/users` | Crear usuario global |
| PATCH | `/api/v1/admin/users/{user_id}/activate` | Activar usuario |
| PATCH | `/api/v1/admin/users/{user_id}/deactivate` | Desactivar usuario |
| PATCH | `/api/v1/admin/users/{user_id}/role` | Cambiar rol global |

---

## 4. Códigos de Estado HTTP

| Código | Significado |
|-------|-------------|
| 200 | OK - Request exitosa |
| 201 | Created - Recurso creado |
| 202 | Accepted - Request aceptada (async) |
| 400 | Bad Request - Datos inválidos |
| 401 | Unauthorized - No autenticado |
| 403 | Forbidden - Sin permisos |
| 404 | Not Found - Recurso no existe |
| 409 | Conflict - Estado inválido (ej: transición de release) |
| 422 | Unprocessable Entity - Validación fallida |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error - Error del servidor |

---

## 5. Rate Limiting

| Tipo de Endpoint | Límite |
|------------------|--------|
| Auth (`/auth/*`) | 30 requests/min |
| Búsqueda | 30 requests/min |
| Prueba de conector | 100 requests/min |
| Por defecto | 100 requests/min |

Si excedes el límite, recibirás `429 Too Many Requests` con header `Retry-After`.

---

## 6. Importar Colección en Postman

### Pasos:

1. Abrir Postman
2. Click en **Import** (esquina superior izquierda)
3. Seleccionar **Link** y pegar: `https://api.svaes.example.com/openapi.json` (o la URL de tu entorno)
4. O manualmente: Exportar el JSON de OpenAPI desde `/openapi.json` y arrastrarlo a Postman

### Configurar Environment:

1. Crear environment `SVAES Local` o similar
2. Añadir variables:

| Variable | Initial Value | Current Value |
|----------|---------------|---------------|
| `base_url` | `http://localhost:8000` | `http://localhost:8000` |
| `access_token` | (vacío) | (se llena tras login) |
| `refresh_token` | (vacío) | (se llena tras login) |
| `user_id` | (vacío) | (se llena tras login) |
| `org_id` | (uuid de org) | (uuid de org) |

3. En el tab **Authorization** de la colección, usar:
   - Type: `Bearer Token`
   - Token: `{{access_token}}`

---

## 7. Ejemplo de Flow Completo

### Crear una Release con Verificación:

```
1. POST /api/v1/auth/login
   → Guardar access_token

2. GET /api/v1/users/me
   → Obtener organization_ids

3. GET /api/v1/organizations/{org_id}/projects
   → Obtener project_id

4. POST /api/v1/projects/{project_id}/releases
   Body: {"name": "v1.0.0", "version": "1.0.0"}
   → Obtener release_id

5. POST /api/v1/releases/{release_id}/artifacts
   Body: {"connector_instance_id": "...", "connector_implementation": "JIRA", "artifact_type": "TAREA", "external_ref": "PROJ-1"}
   → Artifact creado

6. PATCH /api/v1/releases/{release_id}
   Body: {"status": "PENDIENTE"}

7. POST /api/v1/releases/{release_id}/verify
   → Obtener task_id

8. GET /api/v1/tasks/{task_id}
   → Verificar estado (SUCCESS/FAILURE)

9. GET /api/v1/releases/{release_id}/results
   → Obtener resultado de verificación
```

---

## 8. Scripts de Pre-request (Postman)

Para automatizar el token en cada request:

```javascript
// En la colección o folder, usar auth/token
if (pm.collectionVariables.get("access_token")) {
    pm.request.headers.add({
        key: "Authorization",
        value: "Bearer " + pm.collectionVariables.get("access_token")
    });
}
```

O usar el tab Authorization de cada request con **Inherit from parent**.

---

## 9. Verificar Health del Servicio

```
GET /health
```

Response esperada:
```json
{
  "status": "ok",
  "service": "svaes-api",
  "version": "1.0.0"
}
```
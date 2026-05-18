# Guide to Testing the API with Postman

This guide describes how to use Postman (or any similar HTTP client) to test the SVAES API endpoints.

---

## 1. Environment Setup

### Base URL

```
Development: http://localhost:8000
Production:  https://api.svaes.example.com
```

### Common Headers

| Header | Value |
|--------|-------|
| `Content-Type` | `application/json` |
| `Accept` | `application/json` |

---

## 2. Authentication

### Login

**Endpoint:** `POST /api/v1/auth/login`

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "Bearer",
  "user_id": "user-uuid",
  "role": "U2"
}
```

> Save the `access_token` to use in subsequent requests.

### Using the Token

For each protected request, add the header:

```
Authorization: Bearer <access_token>
```

### Refreshing the Token

**Endpoint:** `POST /api/v1/auth/refresh`

**Request:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

---

## 3. Request Collection by Router

### 3.1 Auth (`/api/v1/auth`)

| Method | Route | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/login` | Login with email/password |
| POST | `/api/v1/auth/refresh` | Refresh access token |

### 3.2 Users (`/api/v1/users`)

| Method | Route | Description |
|--------|------|-------------|
| GET | `/api/v1/users/me` | Current user profile |
| PATCH | `/api/v1/users/me` | Update profile |
| POST | `/api/v1/users/me/password` | Change password |

**GET /api/v1/users/me**

Response:
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "display_name": "User Name",
  "role": "U2",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

**PATCH /api/v1/users/me**
```json
{
  "display_name": "New Name"
}
```

**POST /api/v1/users/me/password**
```json
{
  "current_password": "password123",
  "new_password": "newPassword456",
  "confirm_password": "newPassword456"
}
```

### 3.3 Organizations (`/api/v1/organizations`)

| Method | Route | Description |
|--------|------|-------------|
| GET | `/api/v1/organizations` | List organizations (U3) |
| POST | `/api/v1/organizations` | Create organization (U3) |
| GET | `/api/v1/organizations/{org_id}` | Organization details |
| GET | `/api/v1/projects` | List projects |
| POST | `/api/v1/organizations/{org_id}/projects` | Create project |

**POST /api/v1/organizations**
```json
{
  "name": "My Organization",
  "slug": "my-organization",
  "plan": "default"
}
```

**GET /api/v1/projects**
Query params: `?page=1&size=25&status=ACTIVE&search=name&org_id=uuid`

### 3.4 Projects (`/api/v1/projects/{project_id}`)

| Method | Route | Description |
|--------|------|-------------|
| GET | `/api/v1/projects/{project_id}` | Project details |
| PATCH | `/api/v1/projects/{project_id}` | Update project |
| POST | `/api/v1/organizations/{org_id}/projects/{project_id}/archive` | Archive project |

### 3.5 Releases (`/api/v1/releases`)

| Method | Route | Description |
|--------|------|-------------|
| POST | `/api/v1/projects/{project_id}/releases` | Create release |
| GET | `/api/v1/projects/{project_id}/releases` | List releases |
| GET | `/api/v1/releases/{release_id}` | Release details |
| PATCH | `/api/v1/releases/{release_id}` | Update release |
| DELETE | `/api/v1/releases/{release_id}` | Delete release |
| POST | `/api/v1/releases/{release_id}/archive` | Archive release |
| POST | `/api/v1/releases/{release_id}/verify` | Launch verification |
| GET | `/api/v1/releases/{release_id}/results` | Verification history |

**POST /api/v1/projects/{project_id}/releases**
```json
{
  "name": "Release v1.0.0",
  "version": "1.0.0",
  "description": "First release",
  "profile_id": "profile-uuid"
}
```

**PATCH /api/v1/releases/{release_id}**
```json
{
  "name": "Release v1.0.1",
  "status": "PENDING"
}
```

**POST /api/v1/releases/{release_id}/verify**
Response (202 Accepted):
```json
{
  "task_id": "task-uuid"
}
```

### 3.6 Artifacts

| Method | Route | Description |
|--------|------|-------------|
| GET | `/api/v1/releases/{release_id}/artifacts` | List artifacts |
| POST | `/api/v1/releases/{release_id}/artifacts` | Add artifact |
| DELETE | `/api/v1/releases/{release_id}/artifacts/{artifact_id}` | Remove artifact |
| POST | `/api/v1/releases/{release_id}/artifacts/import` | Import artifacts (JSON array) |

**POST /api/v1/releases/{release_id}/artifacts**
```json
{
  "connector_instance_id": "uuid",
  "connector_implementation": "JIRA",
  "artifact_type": "TASK",
  "external_ref": "PROJ-123",
  "metadata": {}
}
```

### 3.7 Connectors (`/api/v1/organizations/{org_id}/connectors`)

| Method | Route | Description |
|--------|------|-------------|
| GET | `/api/v1/connectors/types` | List connector types |
| GET | `/api/v1/organizations/{org_id}/connectors` | List connectors |
| POST | `/api/v1/organizations/{org_id}/connectors` | Create connector |
| PATCH | `/api/v1/organizations/{org_id}/connectors/{connector_id}` | Update connector |
| DELETE | `/api/v1/organizations/{org_id}/connectors/{connector_id}` | Delete connector |
| POST | `/api/v1/organizations/{org_id}/connectors/{connector_id}/test` | Test connection |

**POST /api/v1/organizations/{org_id}/connectors**
```json
{
  "connector_type": "TASK_MANAGER",
  "connector_implementation": "JIRA",
  "name": "My JIRA Connector",
  "credentials": {
    "api_token": "jira-token",
    "instance_url": "https://my-company.atlassian.net"
  }
}
```

### 3.8 Profiles (`/api/v1/organizations/{org_id}/profiles`)

| Method | Route | Description |
|--------|------|-------------|
| GET | `/api/v1/organizations/{org_id}/profiles` | List profiles |
| POST | `/api/v1/organizations/{org_id}/profiles` | Create profile |
| PATCH | `/api/v1/profiles/{profile_id}` | Update profile |
| DELETE | `/api/v1/profiles/{profile_id}` | Delete profile |

**POST /api/v1/organizations/{org_id}/profiles**
```json
{
  "name": "Standard Verification Profile",
  "description": "Profile for production releases",
  "is_default": false
}
```

### 3.9 Rules

| Method | Route | Description |
|--------|------|-------------|
| POST | `/api/v1/profiles/{profile_id}/rules` | Add rule |
| PATCH | `/api/v1/rules/{rule_id}` | Update rule |
| DELETE | `/api/v1/rules/{rule_id}` | Delete rule |

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

| Method | Route | Description |
|--------|------|-------------|
| GET | `/api/v1/tasks/{task_id}` | Async task status |

Response:
```json
{
  "task_id": "uuid",
  "status": "SUCCESS",
  "result": "Task result"
}
```

### 3.11 Custom Roles (`/api/v1/organizations/{org_id}/roles`)

| Method | Route | Description |
|--------|------|-------------|
| GET | `/api/v1/organizations/{org_id}/roles` | List roles |
| POST | `/api/v1/organizations/{org_id}/roles` | Create role |
| PATCH | `/api/v1/roles/{role_id}` | Update role |
| DELETE | `/api/v1/roles/{role_id}` | Delete role |

**POST /api/v1/organizations/{org_id}/roles**
```json
{
  "name": "Release Supervisor",
  "permissions": ["VIEW_ORG_PROJECTS", "CREATE_RELEASE", "EXECUTE_VERIFICATION"]
}
```

### 3.12 Dashboard (`/api/v1/dashboard/metrics`)

| Method | Route | Description |
|--------|------|-------------|
| GET | `/api/v1/dashboard/metrics?org_id={org_id}` | Dashboard metrics |

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

| Method | Route | Description |
|--------|------|-------------|
| POST | `/api/v1/users/{user_id}/api-keys` | Create API key |
| GET | `/api/v1/users/{user_id}/api-keys` | List API keys |
| DELETE | `/api/v1/users/{user_id}/api-keys/{key_id}` | Revoke API key |

**POST /api/v1/users/{user_id}/api-keys**
```json
{
  "name": "My CI/CD API Key",
  "expires_in_days": 90
}
```

> The full key is only returned at creation. Save it because it cannot be retrieved later.

### 3.14 Templates (`/api/v1/templates`)

| Method | Route | Description |
|--------|------|-------------|
| POST | `/api/v1/templates` | Create template |
| GET | `/api/v1/templates` | List templates |
| GET | `/api/v1/templates/{template_id}` | Template details |
| PATCH | `/api/v1/templates/{template_id}` | Update template |
| POST | `/api/v1/templates/{template_id}/archive` | Archive template |
| POST | `/api/v1/templates/{template_id}/clone` | Clone template |

### 3.15 Notifications (`/api/v1/notifications`)

| Method | Route | Description |
|--------|------|-------------|
| GET | `/api/v1/notifications/channels` | List channels |
| POST | `/api/v1/notifications/channels` | Configure channel |
| PATCH | `/api/v1/notifications/channels/{channel_id}` | Update channel |
| DELETE | `/api/v1/notifications/channels/{channel_id}` | Delete channel |
| GET | `/api/v1/notifications/preferences` | User preferences |
| PATCH | `/api/v1/notifications/preferences` | Update preferences |
| POST | `/api/v1/notifications/subscriptions` | Subscribe to event |
| DELETE | `/api/v1/notifications/subscriptions/{event_type}` | Unsubscribe |

### 3.16 Admin (`/api/v1/admin`) - U3 Only

| Method | Route | Description |
|--------|------|-------------|
| POST | `/api/v1/admin/rules/reload` | Hot-reload custom rules |
| GET | `/api/v1/admin/users` | List all users |
| POST | `/api/v1/admin/users` | Create global user |
| PATCH | `/api/v1/admin/users/{user_id}/activate` | Activate user |
| PATCH | `/api/v1/admin/users/{user_id}/deactivate` | Deactivate user |
| PATCH | `/api/v1/admin/users/{user_id}/role` | Change global role |

---

## 4. HTTP Status Codes

| Code | Meaning |
|-------|-------------|
| 200 | OK - Successful request |
| 201 | Created - Resource created |
| 202 | Accepted - Request accepted (async) |
| 400 | Bad Request - Invalid data |
| 401 | Unauthorized - Not authenticated |
| 403 | Forbidden - No permissions |
| 404 | Not Found - Resource does not exist |
| 409 | Conflict - Invalid state (e.g., release transition) |
| 422 | Unprocessable Entity - Validation failed |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error - Server error |

---

## 5. Rate Limiting

| Endpoint Type | Limit |
|------------------|--------|
| Auth (`/auth/*`) | 30 requests/min |
| Search | 30 requests/min |
| Connector test | 100 requests/min |
| Default | 100 requests/min |

If you exceed the limit, you will receive `429 Too Many Requests` with a `Retry-After` header.

---

## 6. Import Collection into Postman

### Steps:

1. Open Postman
2. Click **Import** (top left corner)
3. Select **Link** and paste: `https://api.svaes.example.com/openapi.json` (or your environment URL)
4. Or manually: Export the OpenAPI JSON from `/openapi.json` and drag it into Postman

### Configure Environment:

1. Create environment `SVAES Local` or similar
2. Add variables:

| Variable | Initial Value | Current Value |
|----------|---------------|---------------|
| `base_url` | `http://localhost:8000` | `http://localhost:8000` |
| `access_token` | (empty) | (filled after login) |
| `refresh_token` | (empty) | (filled after login) |
| `user_id` | (empty) | (filled after login) |
| `org_id` | (org uuid) | (org uuid) |

3. In the collection's **Authorization** tab, use:
   - Type: `Bearer Token`
   - Token: `{{access_token}}`

---

## 7. Full Flow Example

### Create a Release with Verification:

```
1. POST /api/v1/auth/login
   → Save access_token

2. GET /api/v1/users/me
   → Get organization_ids

3. GET /api/v1/organizations/{org_id}/projects
   → Get project_id

4. POST /api/v1/projects/{project_id}/releases
   Body: {"name": "v1.0.0", "version": "1.0.0"}
   → Get release_id

5. POST /api/v1/releases/{release_id}/artifacts
   Body: {"connector_instance_id": "...", "connector_implementation": "JIRA", "artifact_type": "TASK", "external_ref": "PROJ-1"}
   → Artifact created

6. PATCH /api/v1/releases/{release_id}
   Body: {"status": "PENDING"}

7. POST /api/v1/releases/{release_id}/verify
   → Get task_id

8. GET /api/v1/tasks/{task_id}
   → Check status (SUCCESS/FAILURE)

9. GET /api/v1/releases/{release_id}/results
   → Get verification result
```

---

## 8. Pre-request Scripts (Postman)

To automate the token on every request:

```javascript
// In the collection or folder, use auth/token
if (pm.collectionVariables.get("access_token")) {
    pm.request.headers.add({
        key: "Authorization",
        value: "Bearer " + pm.collectionVariables.get("access_token")
    });
}
```

Or use each request's Authorization tab with **Inherit from parent**.

---

## 9. Checking Service Health

```
GET /health
```

Expected response:
```json
{
  "status": "ok",
  "service": "svaes-api",
  "version": "1.0.0"
}
```

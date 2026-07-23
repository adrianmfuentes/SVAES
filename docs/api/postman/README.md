# Testing the API with Postman

`collection.json` has every endpoint, grouped by router, with example bodies already filled in — that's the source of truth for requests, not this file. `environment.json` supplies the variables it expects.

## Import

1. Postman → **Import** → select both `collection.json` and `environment.json` (or drag them in).
2. Select the **SVAES** environment in the top-right dropdown.
3. Set `base_url` (defaults to `http://localhost:8000`).

## Authenticate

Run **1. Health Check → GET /health** to confirm the API is reachable, then **2. Authentication → POST /auth/login**. Its test script saves `access_token` / `refresh_token` into the environment automatically — every other request in the collection inherits `Authorization: Bearer {{access_token}}` from the collection root, so nothing else to configure.

## Typical flow

Login → `GET /users/me` (get `organization_ids`) → `GET /projects` (get `project_id`) → `POST /projects/{project_id}/releases` → `POST /releases/{release_id}/artifacts` → `POST /releases/{release_id}/verify` → poll `GET /tasks/{task_id}` → `GET /releases/{release_id}/results`.

Full endpoint reference (permissions, status codes, rate limits): [docs/api/reference.md](../reference.md).

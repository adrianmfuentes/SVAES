# SVAES — Software Verification and Audit Engine System

Monorepo for the SVAES platform: automated release verification, multi-tenant audit, external connectors (Jira, GitLab, Confluence), REST API, and web dashboard.

## Structure

```
svaes/
├─ apps/           # Deployable applications (web frontend, API backend)
├─ packages/       # Shared libraries (domain, application, infrastructure, connectors, shared)
├─ workers/        # Background workers (verification engine)
├─ tests/          # Cross-cutting tests (integration, e2e, performance, security)
├─ scripts/        # Dev, DB, and deploy scripts
└─ docs/           # OpenAPI spec, diagrams, ERD
```

## Quick Start

```bash
cp .env.example .env
docker compose up -d
```

## Apps

| App | Description |
|-----|-------------|
| `apps/web` | React frontend — dashboard, projects, releases, verifications |
| `apps/api` | REST API backend — auth, multi-tenant, audit, notifications |

## Packages

| Package | Description |
|---------|-------------|
| `packages/domain` | Pure domain entities: Release, Verification, Rule, Tenant, User |
| `packages/application` | Use cases, ports, DTOs |
| `packages/infrastructure` | DB, queues, security, repositories |
| `packages/connectors` | Jira, GitLab, Confluence, planning, change-management |
| `packages/shared` | Constants, error types, utilities |

## Workers

| Worker | Description |
|--------|-------------|
| `workers/verification-worker` | Async verification job executor |

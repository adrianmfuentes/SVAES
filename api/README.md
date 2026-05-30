# SVAES API

FastAPI backend for the SVAES system (Static Verification and Approval Engine System).

## Description

RESTful API for managing organizations, projects, releases, and artifact verification. Implements hexagonal architecture (Ports & Adapters) with JWT authentication and role-based access control (RBAC).

## Features

- Hexagonal architecture with input/output ports
- JWT authentication with refresh tokens
- RBAC with 4 role levels (U1-U4)
- Multi-tenancy with organization-level isolation
- Rate limiting per endpoint
- Audit logging of operations

## Documentation

Full API documentation: [docs/api/reference.md](../docs/api/reference.md)

Additional guides:
- [Testing](../docs/development/testing.md)
- [Deployment](../docs/deployment.md)
- [Postman](../docs/api/postman/README.md)

## Usage

```bash
cd api
uvicorn src.main:app --reload
```

## Main Endpoints

| Router | Prefix | Description |
|--------|--------|-------------|
| Auth | `/api/v1/auth` | Login, refresh tokens |
| Users | `/api/v1/users` | Profile, user management |
| Organizations | `/api/v1/organizations` | Organizations and projects |
| Releases | `/api/v1/releases` | Release management |
| Connectors | `/api/v1/connectors` | External connectors |
| Profiles | `/api/v1/profiles` | Verification profiles |
| Rules | `/api/v1/rules` | Verification rules |
| Dashboard | `/api/v1/dashboard` | Metrics |

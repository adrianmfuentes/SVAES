# SVAES API

> **TFG terminado** (30/06/2026) — FastAPI backend for the SVAES system (Sistema de Verificación Automática de Entregas de Software).

FastAPI backend for the SVAES system (Static Verification and Approval Engine System).

## Description

RESTful API for managing organizations, projects, releases, and artifact verification. Implements hexagonal architecture (Ports & Adapters) with JWT authentication and role-based access control (RBAC).

## Features

- Hexagonal architecture with input/output ports
- JWT authentication with refresh tokens
- TOTP two-factor authentication (2FA) via pyotp + segno
- RBAC with 3 role levels (OPERATOR, MANAGER, ADMIN) and 20 granular permissions
- Multi-tenancy with organization-level isolation
- Account deletion with automatic ownership transfer
- Rate limiting per endpoint (slowapi)
- GDPR-compliant audit logging (audit_log table)
- PII pseudonymisation in verification pipeline

## Documentation

Full API documentation: [docs/api/reference.md](../docs/api/reference.md)

Additional guides:
- [Testing](../docs/development/testing.md)
- [Deployment](../docs/DEPLOY.md)
- [Postman](../docs/api/postman/README.md)

## Usage

```bash
cd api
uvicorn src.main:app --reload
```

## Main Endpoints

| Router | Prefix | Description |
|--------|--------|-------------|
| Auth | `/api/v1/auth` | Login, 2FA verify, register, refresh, logout |
| Users | `/api/v1/users` | Profile, password, data export, account deletion |
| Organizations | `/api/v1/organizations` | Organizations and projects |
| Releases | `/api/v1/releases` | Release management, artifacts, PDF/CSV export |
| Connectors | `/api/v1/connectors` | External connectors (20 implementations) |
| Profiles | `/api/v1/profiles` | Verification profiles and rules |
| Tasks | `/api/v1/tasks` | Async task status |
| Custom Roles | `/api/v1/roles` | Custom role CRUD |
| Dashboard | `/api/v1/dashboard` | Metrics |
| API Keys | `/api/v1/api-keys` | Programmatic CI/CD access |
| Templates | `/api/v1/templates` | Release templates |
| Notifications | `/api/v1/notifications` | Channel config and preferences |
| Admin | `/api/v1/admin` | User management, rules reload (U4 only) |
| Audit | `/api/v1/audit` | Audit log viewer (MANAGER+) |
| Access Requests | `/api/v1/access-requests` | Access request submissions and approval |

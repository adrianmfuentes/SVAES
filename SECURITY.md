# Security Policy — SVAES

**Sistema de Verificación Automática de Entregas de Software**

---

## Supported Versions

SVAES is an academic project (TFG — Trabajo de Fin de Grado) under active development.
Only the `main` branch receives security updates. Tagged releases are not yet issued.

| Version | Security Support |
|---------|-----------------|
| `main` (development) | Active |
| Tagged releases (`v0.x.x`) | Latest only |
| Older versions | Unsupported |

---

## Supported Scope

### In Scope

The following attack surfaces are relevant to this project:

- **REST API** (`api/`): SQL injection, IDOR, broken authentication, improper RBAC.
- **JWT Authentication**: weak algorithms, missing signature validation, tokens without expiration.
- **Multi-tenant Isolation**: cross-tenant data access, data leakage between organizations.
- **Rust Verification Engine**: vulnerabilities in API → Engine communication channel,
  deserialization attacks, path traversal in artifact handling.
- **Secret Management**: credentials exposed in logs, environment variables, or HTTP responses.
- **Third-party Dependencies**: known CVEs in `pyproject.toml` declared dependencies.

### Out of Scope

- Denial-of-service (DoS/DDoS) attacks.
- Social engineering against maintainers.
- Vulnerabilities in hosting infrastructure (outside the project's control).
- Automated scanner reports without evidence of real exploitability.

---

## How to Report a Vulnerability

This is an academic project with no bug bounty program. We request **responsible disclosure**
following the steps below.

### Option 1 — GitHub Private Vulnerability Reporting (preferred)

1. Go to the **Security** tab of the GitHub repository.
2. Click **"Report a vulnerability"**.
3. Fill in the form with the information described below.

### Option 2 — Email

Send a message to **amf13azul@gmail.com** with subject:

```
[SVAES][SECURITY] <brief description>
```

### Required Information

To expedite analysis, include:

| Field | Description |
|-------|-------------|
| **Affected component** | `api`, Rust engine, infrastructure, etc. |
| **Vulnerability type** | OWASP Top 10, CWE, or free-text description |
| **Estimated severity** | Critical / High / Medium / Low |
| **Steps to reproduce** | Detailed description or minimal PoC |
| **Potential impact** | What data or functionality is exposed |
| **Affected version or commit** | Commit hash or branch |

---

## Response Timeline

| Action | Target SLA |
|--------|------------|
| Acknowledgement of report | 72 hours |
| Confirmation or dismissal of vulnerability | 7 days |
| Fix deployment (if applicable) | 30 days |
| Coordinated public disclosure | Agreed with reporter |

SVAES is maintained individually as an academic project. Timelines are targets and may
shift during examination periods.

---

## Implemented Security Controls

| Mechanism | Status | Location |
|-----------|--------|----------|
| JWT Authentication (HS256) | Implemented | `api/src/infrastructure/primary/middleware/jwt_handler.py` |
| TOTP Two-Factor Authentication (2FA) | Implemented | `api/src/application/use_cases/main/auth_service.py` |
| RBAC on API endpoints | Implemented | `api/src/core/dependencies.py` |
| Multi-tenant isolation (domain layer) | Implemented | `api/src/domain/`, `api/src/core/dependencies.py` |
| Fernet (AES-128-CBC) credential encryption | Implemented | `api/src/core/credential_encryptor.py` |
| Input validation with Pydantic | Implemented | All router schemas |
| Account lockout (5 attempts → 15 min) | Implemented | `api/src/application/use_cases/main/auth_service.py` |
| Rate limiting (slowapi) | Implemented | `api/src/core/rate_limit.py` |
| Audit log persisted to DB (GDPR) | Implemented | `api/src/core/audit.py` + `audit_log` table |
| PII pseudonymisation in verification | Implemented | `api/src/core/pseudonymizer.py` |
| Redis password authentication | Implemented | `docker-compose.yml` (requirepass) |
| Engine API key authentication | Implemented | `engine/src/main.rs` |
| Static analysis (CodeQL) | Active | `.github/workflows/codeql.yml` |
| Dependency updates (Dependabot) | Active | `.github/dependabot.yml` |
| Secrets via environment variables | Active | `.env` (not versioned) |

---

## Security Announcements

No security advisories have been published yet. Once a tagged release is issued,
a `SECURITY.md` table will be maintained in the project root and referenced in
GitHub Security Advisories.

---

## Coordinated Disclosure

Once a vulnerability is fixed, coordinated public disclosure will be performed with
the reporter. Credit will be given in the changelog unless the reporter prefers
anonymity.

---

*Policy in effect as of June 2026. Maintained by [@adrianmfuentes](https://github.com/adrianmfuentes).*

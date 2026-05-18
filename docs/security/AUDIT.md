# Security & Compliance Audit Report — SVAES

**Scope:** Full application (`api/`, `engine/`, `web/`, `tests/`, `docs/`, CI/CD, configuration)  
**Date:** 2026-05-18  
**Status:** Active  

---

## EXECUTIVE SUMMARY

### Previous Security Findings Status

| Severity | Count | Status |
|----------|-------|--------|
| Critical | 1     | ✅ Fixed |
| High     | 7     | ✅ Fixed |
| Medium   | 8     | ✅ Fixed |
| Low      | 4     | ✅ Fixed |

**Total:** 20 findings — all resolved.

### Current Open Concerns

| Severity | Finding | Status |
|----------|---------|--------|
| — | All previously open concerns resolved. | ✅ |

---

## 1. PROJECT OVERVIEW

### Identity
- **Project:** SVAES — Sistema de Verificación Automática de Entregas de Software
- **Purpose:** Quality Gate platform for automated software delivery verification
- **Author:** Adrian Martinez Fuentes (UO295454) — University of Oviedo
- **Context:** Final Degree Project (TFG), Software Engineering, 2025/2026
- **License:** MIT

### Architecture
```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Angular 21 │────▶│  FastAPI 0.136│────▶│  PostgreSQL 16  │
│  (web/)     │     │  (api/)       │     │  Redis 7        │
│  ⏳ Skeleton │     │  ✅ Complete  │     │  ✅ Configured  │
└─────────────┘     └──────┬───────┘     └─────────────────┘
                           │
                    ┌──────▼───────┐
                    │  Rust/Actix  │
                    │  (engine/)   │
                    │  ✅ Complete  │
                    └──────────────┘
```

| Layer | Technology | Version | Status |
|-------|-----------|---------|--------|
| API | FastAPI + SQLAlchemy + Celery | Python 3.12 | Production-ready |
| Engine | Actix-web + Rayon | Rust 2021 | Production-ready |
| Web | Angular | 21.2.0 | Skeleton — no feature modules |
| DB | PostgreSQL | 16-alpine | Configured with auth |
| Cache/Broker | Redis | 7-alpine | Configured with auth |
| Proxy | Nginx | alpine | Configured |

---

## 2. API LAYER (FastAPI Backend)

### Status: ✅ Production-ready

**Entry point:** `api/src/main.py` (162 lines)

### Dependencies
- fastapi 0.136.1, uvicorn 0.46.0, sqlalchemy 2.0.49, alembic 1.18.4
- pyjwt 2.12.0, passlib[bcrypt] 1.7.4, cryptography 46.0.7
- celery 5.4.0, redis 5.0.0, httpx 0.28.1
- slowapi 0.1.9 (rate limiting), email-validator 2.2.0
- Package manager: uv 0.11.11

### Architecture: Clean Architecture / Hexagonal

| Layer | Contents |
|-------|----------|
| `domain/` | 12 entities, 14 enums, domain exceptions |
| `application/ports/input/` | 15 service interfaces |
| `application/ports/output/` | 15+ repository/connector interfaces |
| `application/use_cases/main/` | 17 service implementations |
| `application/use_cases/others/` | 7 auxiliary use cases |
| `infrastructure/primary/` | 13 routers, JWT handler, password hasher, rate limiter |
| `infrastructure/secondary/` | 15 SQLAlchemy models, 14 repositories, 20 connectors, Celery |
| `infrastructure/workers/` | Verification worker (Celery task) |
| `core/` | Config, dependencies, audit, credential encryption, rate limit |

### API Endpoints (65+ across 13 routers)

| Router | Prefix | Key Endpoints |
|--------|--------|---------------|
| `auth.py` | `/api/v1/auth` | POST login, register, refresh, logout |
| `users.py` | `/api/v1/users` | Profile CRUD, password change, data export, org management |
| `organizations.py` | `/api/v1/organizations` | CRUD, project management, transfer, restore |
| `releases.py` | `/api/v1/releases` | CRUD, artifacts, verify, results, PDF/CSV export |
| `connectors.py` | `/api/v1/connectors` | Types listing, register, test, update, delete |
| `profiles.py` | `/api/v1/profiles` | Profile & rule CRUD |
| `tasks.py` | `/api/v1/tasks` | Task status query |
| `custom_roles.py` | `/api/v1/roles` | Custom role CRUD |
| `dashboard.py` | `/api/v1/dashboard` | Metrics |
| `api_keys.py` | `/api/v1/api-keys` | API key create/list/revoke |
| `templates.py` | `/api/v1/templates` | Release templates |
| `notifications.py` | `/api/v1/notifications` | Channel config, preferences, subscriptions |
| `admin.py` | `/api/v1/admin` | User management, rules reload (U3 only) |

### Authentication & Authorization
- **JWT:** HS256 via PyJWT (`jwt_handler.py`)
- **Password hashing:** bcrypt via passlib, cost factor 12
- **RBAC:** 4 roles (U1=VIEWER, U2=OPERATOR, U3=ADMIN, U4=MANAGER)
- **30 granular permissions** defined in `domain/enums.py`
- **Token blacklisting:** In-memory set + Redis with TTL (`jwt_handler.py`)
- **Account lockout:** 5 failed attempts → 15-minute lockout
- **Rate limiting:** 30 requests/minute on auth endpoints (slowapi)

### Database
- PostgreSQL 16-alpine with Alembic migrations
- Migrations run automatically on startup via lifespan handler
- `audit_log` table for GDPR-compliant traceability

---

## 3. ENGINE LAYER (Rust Verification Motor)

### Status: ✅ Production-ready

**Entry point:** `engine/src/main.rs` (73 lines)

### Dependencies (Cargo.toml)
- actix-web 4.4, rayon 1.8 (parallelism), serde 1.0, serde_json
- thiserror 1.0, log 0.4, env_logger 0.11
- Release profile: opt-level=3, LTO=true, codegen-units=1

### Architecture: Stateless parallel evaluator

| File | Purpose |
|------|---------|
| `main.rs` | Actix-web server with API key auth |
| `models.rs` | Artifact, VerificationRule, RuleEvaluation, Verdict |
| `evaluator.rs` | Parallel rule evaluation via Rayon `par_iter()` |
| `aggregator.rs` | Global verdict computation (mandatory/optional rules) |
| `rules/mod.rs` | Module declarations |
| `rules/rv01.rs` | Artifact existence check (with tests) |
| `rules/rv02.rs` | ID coherence / traceability |
| `rules/rv03.rs` | Task state validation |
| `rules/rv04.rs` | Effort estimation validation |
| `rules/rv05.rs` | Document availability |
| `rules/rv06.rs` | Document version coherence |
| `rules/rv07.rs` | Planned release registration |
| `rules/rv08.rs` | Planning coherence |
| `rules/rv09.rs` | Code references (URL/branch format) |
| `rules/rv10.rs` | Test report approval |

### Security
- API key authentication via `X-Engine-Api-Key` header
- Port 8081 NOT exposed in production (`docker-compose.prod.yml`)
- Built as non-root user in Docker
- Warning emitted if API key is empty at startup (dev mode allowance)

### Endpoints
- `GET /health` — Health check (authenticated)
- `POST /api/v1/verify` — Verification endpoint (authenticated)

---

## 4. WEB LAYER (Angular Frontend)

### Status: ⏳ Skeleton — not yet implemented

- Angular 21.2.0, TypeScript 5.9.2, pnpm 10.11.0
- Testing: Vitest 4.0.8 (configured but no feature tests)
- Styling: SCSS

### Current State
- Empty routes (`web/src/app/app.routes.ts`)
- Basic app component and config
- No feature modules, services, or API integration
- README states "Angular 17" but `package.json` has `@angular/core: ^21.2.0` — documentation discrepancy
- Served via nginx:alpine from `./web/dist/web/browser` (requires pre-build)

---

## 5. TESTS

### Status: ⚠️ Low coverage

| Area | Coverage |
|------|----------|
| Unit tests (API) | `test_auth.py` only (AuthService — 161 lines) |
| Integration tests (API) | 2 files: `test_testclient.py`, `test_complete.py` (basic flows) |
| Engine tests | Inline tests in `rv01.rs` (3 cases); other rules likely similar |
| Acceptance tests | Empty directory |
| Performance tests | Empty directory |
| Web tests | 1 basic component test |

### Configuration
- pytest with pytest-asyncio (`asyncio_mode = auto`)
- `pytest.ini` has incorrect `pythonpath = apps/api/src` → actual path is `api/src`
- Coverage output: `coverage.xml` at project root (SonarCloud)

---

## 6. CONFIGURATION

### Environment

| File | Purpose |
|------|---------|
| `.env.example` | Template with 4 variables (weak defaults documented) |
| `.env` | Actual dev environment (gitignored) |
| `api/src/core/config.py` | Pydantic-settings class (72 lines) — validates all vars |
| `sonar-project.properties` | SonarCloud: Python 3.13, sources in `api/src` |
| `api/pyrightconfig.json` | Pyright: `extraPaths: ["src"]` |

### Docker Compose

| File | Purpose |
|------|---------|
| `docker-compose.yml` (125 lines) | Base: postgres, redis, engine, api, celery-worker, web |
| `docker-compose.override.yml` (34 lines) | Dev: hot reload, exposed port 5432, volumes |
| `docker-compose.prod.yml` (58 lines) | Prod: secrets via host env, ports hidden, restart=always |

### Scripts
- `scripts/generate_secrets.py`: Generates `JWT_SECRET_KEY` and `ENCRYPTION_KEY` using `secrets.token_urlsafe(32)` and `Fernet.generate_key()`

---

## 7. CI/CD

### GitHub Actions

| Workflow | Triggers | Purpose |
|----------|----------|---------|
| `sonar.yml` | push/PR on main | SonarCloud quality gate |
| `codeql.yml` | push/PR on main, cron weekly | CodeQL security analysis (Python) |
| `dependabot-automerge.yml` | PR from dependabot | Auto-merge patch/minor deps |

### Issues
- SonarCloud `pytest --cov` step is **commented out** in `sonar.yml` (lines 25-26)
- Dependabot references `/apps/api` (incorrect) instead of `/api` in `dependabot.yml` (line 5)
- Git hook `prepare-commit-msg` sends staged diff content to **external Groq API** (`https://api.groq.com/`) for commit message generation — **potential source code data leakage**

### Supply Chain
- `uv` pinned to 0.11.11 with SHA-256 hashes in `.github/requirements/uv.txt`

---

## 8. SECURITY CONTROLS — IMPLEMENTED

| Control | Location |
|---------|----------|
| JWT authentication (HS256) | `api/src/infrastructure/primary/middleware/jwt_handler.py` |
| RBAC on all endpoints | `api/src/core/dependencies.py` |
| Multi-tenant isolation | `api/src/domain/`, `api/src/core/dependencies.py` |
| Fernet credential encryption | `api/src/core/credential_encryptor.py` |
| Pydantic input validation | All router schemas |
| Rate limiting (slowapi) | `api/src/core/rate_limit.py` |
| Audit log (persisted to DB) | `api/src/core/audit.py` + `audit_log` table |
| Redis password auth | `docker-compose.yml` (requirepass) |
| Engine API key auth | `engine/src/main.rs` |
| CodeQL static analysis | `.github/workflows/codeql.yml` |
| Dependabot dependency updates | `.github/dependabot.yml` |
| Secrets via environment variables | `.env` (gitignored) |
| Account lockout | `auth_service.py` (5 attempts → 15 min) |

---

## 9. PREVIOUS SECURITY FINDINGS (RESOLVED)

### Critical

**1. Privilege Escalation via Registration Endpoint**  
- `api/src/infrastructure/primary/routers/api/v1/auth.py:29-34`  
- ✅ **Fixed:** `role` field removed from `RegisterRequest`. Registration always creates `UserRole.U2`. Role elevation only via `PATCH /api/v1/admin/users/{user_id}/role` (U3 only).

### High

**2. Hardcoded and Weak Database Credentials**  
- `docker-compose.yml:6-8`, `.env:3-4`  
- ✅ **Fixed:** All credentials use `${POSTGRES_USER}` and `${POSTGRES_PASSWORD}` environment variables. Non-trivial dev password with production guidance.

**3. Redis Without Authentication**  
- `docker-compose.yml:21-32`  
- ✅ **Fixed:** Redis starts with `--requirepass ${REDIS_PASSWORD}`. All connection URLs include password.

**4. Refresh Token Generated as Access Token (Auth Logic Bug)**  
- `api/src/application/use_cases/main/auth_service.py:91-97`  
- ✅ **Fixed:** `create_refresh_token()` added to `ITokenService`. Both `authenticate()` and `refresh_access_token()` now use correct token type.

**5. Audit Trail Not Persisted**  
- `api/src/core/audit.py:58-80`  
- ✅ **Fixed:** `audit_log` table created with SQLAlchemy model. `AuditLogger.log()` schedules async persistence to DB. Alembic migration applied.

**6. PostgreSQL Exposed on Host in All Environments**  
- `docker-compose.yml:9-10`  
- ✅ **Fixed:** Port 5432 removed from base config. Dev override retains it. Production explicitly sets `ports: []`.

**7. No Breach Notification Mechanism**  
- ✅ **Fixed:** `SECURITY_BREACH_DETECTED` audit event added. `AuthService` emits breach alert on account lockout. Persisted to `audit_log`.

**8. No Explicit Consent or Privacy Policy Acceptance**  
- ✅ **Fixed:** `accept_terms` and `accept_privacy_policy` required in `RegisterRequest`. Timestamps persisted to `user` table. Legal document links in response.

### Medium

**9. JWT Token Blacklist in Volatile Memory**  
- `api/src/infrastructure/primary/middleware/jwt_handler.py:9`  
- ✅ **Fixed:** Blacklist stored in Redis with TTL derived from JWT `exp`. Falls back to in-memory set when Redis unavailable.

**10. Verification Engine Without Authentication**  
- `engine/src/main.rs:24-41`  
- ✅ **Fixed:** API key authentication via `X-Engine-Api-Key` header. Worker passes key when configured.

**11. Login Endpoint Lacks Rate Limiting**  
- ✅ **Fixed:** `@rate_limit_auth()` added to both `login` and `register` handlers.

**12. Personal Data (Email) in Logs**  
- `api/src/infrastructure/primary/routers/api/v1/auth.py:58,81`  
- ✅ **Fixed:** Email replaced with SHA-256 hash prefix (16 chars) in log messages.

**13. Missing Right to Erasure Export / Data Portability**  
- ✅ **Fixed:** `GET /api/v1/users/me/export` endpoint added. Returns structured JSON with all personal data. `DATA_EXPORT_REQUESTED` audit event.

**14. CORS Potentially Overly Permissive in Production**  
- `docker-compose.yml:67`  
- ✅ **Fixed:** `ALLOWED_ORIGINS` explicitly required in `docker-compose.prod.yml`. Deployment fails if missing.

**15. Weak Password Complexity Validation on Public Registration**  
- `api/src/infrastructure/primary/routers/api/v1/auth.py:32`  
- ✅ **Fixed:** `min_length=8` enforced. Validator requires uppercase, lowercase, and digit.

**16. Storage of Cryptographic Secrets in .env File Without Protection**  
- ✅ **Fixed:** `docker-compose.prod.yml` consumes all secrets from host env vars. Docker secrets pattern documented.

### Low

**17. bcrypt.needs_rehash Incorrectly Implemented**  
- `api/src/infrastructure/primary/middleware/password_hasher.py:11-12`  
- ✅ **Fixed:** Rewritten to check bcrypt hash prefix against current rounds.

**18. Internal Error Details Exposed to User**  
- All router files in `api/src/infrastructure/primary/routers/api/v1/`  
- ✅ **Fixed:** All `HTTPException(status_code=500, detail=str(e))` replaced with `detail="Error interno"`. Domain exceptions retain user-facing messages.

**19. HTTPS Connections to External Connectors Without Explicit Verification**  
- `api/src/infrastructure/secondary/connectors/base_http_connector.py:49-50`  
- ✅ **Fixed:** `verify=True` explicitly set. `httpx.ConnectError` caught and logged.

**20. Lack of Pseudonymization in Verification Data**  
- ✅ **Fixed (2026-05-18):** `core/pseudonymizer.py` created — recursively hashes PII fields (email, displayName, assignee, reporter, author, username, etc.) in artifact metadata using SHA-256 with a `sha256:` prefix. Integrated into `verification_worker.py` via `pseudonymize()` call after `fetch_artifact()` and before engine dispatch. Preserves field uniqueness for verification rules while removing actual personal data.

---

## 10. RESOLVED OPERATIONAL CONCERNS

The following concerns were identified in the audit and resolved on 2026-05-18:

### 10.1 Git Hook Sends Source Code to External AI API

**Severity:** Low (resolved)  
**Location:** `.githooks/prepare-commit-msg`  
**Resolution:** Added `GROQ_AUTO_COMMIT_ENABLED` opt-in guard. The hook now checks for `GROQ_AUTO_COMMIT_ENABLED=true` before sending any diff to the Groq API. Without this variable, the hook exits silently. A comment documents the source-code leakage risk requiring controlled-environment acceptance.

### 10.2 Dependabot References Wrong Paths

**Severity:** Low (resolved)  
**Location:** `.github/dependabot.yml`  
**Resolution:** Changed `/apps/api` to `/api` in both pip and Docker ecosystem entries. Updated comment from Python 3.11 to 3.12.

### 10.3 SonarCloud Test Coverage Disabled in CI

**Severity:** Low (resolved)  
**Location:** `.github/workflows/sonar.yml`  
**Resolution:** Uncommented the `pytest --cov` step. SonarCloud now receives coverage data from `coverage.xml`.

### 10.4 pytest.ini Has Invalid pythonpath

**Severity:** Low (resolved)  
**Location:** `pytest.ini`  
**Resolution:** Changed `pythonpath = apps/api/src` to `pythonpath = api/src`.

### 10.5 Pseudonymization for Verification Data

**Severity:** Low (resolved — see Issue #20 above)  
**Location:** `api/src/core/pseudonymizer.py`, `verification_worker.py`  
**Resolution:** Full pseudonymization filter implemented and integrated into the verification pipeline.

### 10.6 Documentation Discrepancy: Angular Version

**Severity:** Info (open — cosmetic)  
**Location:** README.md, README.en.md, README.fr.md  
**Risk:** Documentation states "Angular 17" but `web/package.json` shows `@angular/core: ^21.2.0`.  
**Recommended fix:** Update README files to reflect Angular 21.

### 10.7 Web Frontend Not Implemented

**Severity:** Info (open — feature gap)  
**Location:** `web/`  
**Risk:** The Angular frontend is a minimal scaffold with no feature modules, services, or API integration.  
**Recommended action:** Implement authentication UI, release management, verification results dashboard.

---

## 11. COMPLIANCE CHECKLIST

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Art. 5.1.c GDPR — Data minimization | ✅ | Email hashed in logs, role removed from registration |
| Art. 5.1.e GDPR — Storage limitation | ⚠️ | Data retention policy not documented |
| Art. 5.1.f GDPR — Integrity/confidentiality | ✅ | JWT + RBAC + encrypted credentials + Redis auth |
| Art. 6 GDPR — Lawful processing (consent) | ✅ | Terms/privacy acceptance on registration |
| Art. 7 GDPR — Conditions for consent | ✅ | Timestamps recorded, revocable |
| Art. 13 GDPR — Information to be provided | ✅ | Legal links in registration response |
| Art. 17 GDPR — Right to erasure | ✅ | `DELETE /api/v1/users/me/account` |
| Art. 20 GDPR — Right to data portability | ✅ | `GET /api/v1/users/me/export` |
| Art. 25 GDPR — Data protection by design | ✅ | Role validation, rate limiting, engine auth |
| Art. 30 GDPR — Records of processing | ✅ | `audit_log` table persisted |
| Art. 32 GDPR — Security of processing | ✅ | bcrypt, JWT, Redis auth, port protection |
| Art. 33 GDPR — Breach notification | ✅ | `SECURITY_BREACH_DETECTED` audit event + syslog |
| Art. 34 GDPR — Communication to data subject | ⚠️ | Alerting infrastructure (email/SMS) not wired |
| ISO 27001 A.9.1.2 — Network access | ✅ | DB port hidden in prod, engine internal |
| ISO 27001 A.9.2.3 — Access privilege | ✅ | RBAC fixed, registration role locked |
| ISO 27001 A.9.4.2 — Secure login | ✅ | Rate limiting, account lockout, token refresh |
| ISO 27001 A.10.1.2 — Key management | ✅ | Docker secrets pattern documented |
| OWASP API Top 10 — Broken Auth | ✅ | Rate limiting + lockout on login/register |
| OWASP ASVS V2.1 — Password security | ✅ | min_length=8, complexity validation |
| OWASP ASVS V7.4 — Error handling | ✅ | Generic 500 messages, domain exceptions preserved |

---

*Last updated: 2026-05-18*  
*Next review due: 2026-08-18 (recommended quarterly review cycle)*

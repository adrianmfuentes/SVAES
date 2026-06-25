# SPECS.md — SVAES Functional Specification

> Quick reference summary of system requirements. The full specification
> can be found in **Chapter 4 (SRS)** of the TFG thesis and in the document
> `docs/SRS_SVAES.pdf`.

---

## 1. System Purpose

SVAES automates software *release* validation against a configurable set
of verification rules. It eliminates manual review, centralizes traceability, and produces
a structured verdict per execution.

The system is **generic**: it is not coupled to any specific external tool.
Any data source can be integrated by implementing the `IConnector` port.

---

## 2. Actors

| ID | Role | Description |
|---|---|---|
| U2 | Operator | Creates and manages releases; launches verifications. |
| U3 | Manager | Configures connectors, profiles, and templates for their organization. |
| U4 | Admin (org) | Manages their own users and organizations. |

Role hierarchy: `OPERATOR < MANAGER < ADMIN`.

---

## 3. Functional Epics

### Epic 1 — Multi-tenancy and Security (FEAT-01, FEAT-02)
- Fully isolated organizations (`organization_id` mandatory on all queries).
- Stateless JWT authentication with refresh token in DB.
- RBAC enforced at the HTTP adapter.
- Fernet (AES-128-CBC) authenticated encryption of connector credentials at rest.
- GDPR and OWASP Top 10 (2021) compliance.

### Epic 2 — Release Management (FEAT-03)
- Lifecycle: `BORRADOR → PENDIENTE → EN_VERIFICACION → VALIDA | NO_VALIDA | CON_ADVERTENCIAS | ARCHIVADA`.
- Typed artifacts: `TASK`, `CODE`, `DOCUMENT`.
- Reusable release templates per organization.

### Epic 3 — Connectors (FEAT-04)
- `IConnector` port with operations: `fetch_artifact`, `list_artifacts`, `test_connection`, `get_metadata`.
- Reference connectors: generic task manager, generic code repository,
  generic documentation system.
- Configurable timeout per connector. Rules on `INACTIVE` connector → `NOT_EVALUATED`.

### Epic 4 — Verification Profiles (FEAT-05)
- Profile = set of rule instances (RV-01…RV-10) with level `MANDATORY | OPTIONAL`.
- Default profile non-deletable; available in all organizations.
- Profile assigned to project; release inherits from project (modifiable in `DRAFT`).
- Immutable profile snapshot per execution (historical traceability).

### Epic 5 — Verification Engine (FEAT-06)
- Async execution: backend responds `202 Accepted`; frontend polls for status.
- Rust engine runs in `engine/` as a separate microservice, communicates via HTTP.
- Verdict aggregation policy (see section 4).
- Custom rules via structured configuration file.
- **Current status:** Implemented — `engine/src/` with parallel evaluator (Rayon), verdict aggregator, and 10 rules RV-01…RV-10

### Epic 6 — Results and Traceability (FEAT-07)
- `verification_result` is **immutable** after creation.
- Per rule: individual result, evidence, queried connector, timestamp.
- Dashboard with success rate, average time, and temporal evolution.

### Epic 7 — Notifications and Public API (FEAT-08, FEAT-09)
- REST API documented with OpenAPI 3.x; Angular client auto-generated.
- Rate limiting (sliding window, Redis).
- Notifications via configurable channel (extensible without modifying the core).

---

## 4. Verdict Aggregation Policy

| Condition | Global Verdict |
|---|---|
| Any `MANDATORY` rule → `ERROR` | `INVALID` |
| All `MANDATORY` → `OK` and any `OPTIONAL` → `WARNING` | `WITH_WARNINGS` |
| All active rules → `OK` | `VALID` |

If at least one `NOT_EVALUATED` rule exists, the `_WITH_INCIDENTS` suffix is appended
as a secondary indicator.

---

## 5. Verification Rule Catalog (RV-01 to RV-10)

| ID | Name | Default Severity | Description |
|---|---|---|---|
| RV-01 | Artifact Existence | BLOCKING | Artifact list must not be empty |
| RV-02 | Artifact Traceability | BLOCKING | Code artifacts (`CODIGO`) must reference existing tasks (`TAREA`) |
| RV-03 | Artifact State | BLOCKING | All artifacts of a given type must have an allowed status (e.g. `DONE`, `CLOSED`) |
| RV-04 | Numeric Field Integrity | BLOCKING | Numeric fields (e.g. `effort`, `estimation`) must be non-null and ≥ 0 |
| RV-05 | Document Accessibility | BLOCKING | At least one artifact of a given type must have an accessibility flag set to `true` |
| RV-06 | Attribute Coherence | NON_BLOCKING | Compares a metadata attribute (e.g. `version`) across artifacts of the same type against an expected value |
| RV-07 | External Registration | BLOCKING | A marker artifact indicating external registration is complete must be present |
| RV-08 | List Alignment | BLOCKING | IDs declared in a master artifact must match actual artifact IDs in the payload |
| RV-09 | Reference Validation | NON_BLOCKING | Validates URL and branch name format correctness |
| RV-10 | Final Approval | BLOCKING | At least one artifact must have an approval status (e.g. `APPROVED`, `VALIDATED`) |

Severity levels: `BLOCKING` (mandatory — failure → `INVALID`), `NON_BLOCKING` (optional — failure → `WITH_WARNINGS`), `EXCLUDED` (skipped → `NOT_EVALUATED`).

---

## 6. Key Non-Functional Requirements

| ID | Requirement |
|---|---|
| NFR-01 | Usable user interface without specific training. |
| NFR-03 | API documented with OpenAPI; auto-generated client. |
| NFR-04 | JWT authentication + RBAC + rate limiting. |
| NFR-05 | GDPR compliance; Fernet (AES-128-CBC) credential encryption. |
| NFR-06 | Verification time < 5 s for standard profiles (10 rules, 3 connectors). |
| NFR-07 | Reliability: engine must not produce false negatives in deterministic rules. |
| NFR-08 | Reproducible deployment with Docker Compose. |
| NFR-33 | Rule extensibility without modifying the engine. |
| NFR-35 | Complete traceability per verification (source, resource, result, timestamp). |
| NFR-36 | Immutable snapshot of profile and artifacts per verification. |
| NFR-38 | GDPR compliance in storage and access to personal data. |
| NFR-39 | OWASP Top 10 (2021) risk mitigation. |
| NFR-40 | Machine-readable REST API (OpenAPI 3.x). |

---

## 7. Main Use Cases

| ID | Name | Primary Actor |
|---|---|---|
| UC-01 | System authentication | U1–U5 |
| UC-02 | Full release lifecycle | U2–U3 |

The expanded detail (preconditions, main flow, alternatives, postconditions)
can be found in section 4.8 of the SRS.

---

## 8. Applicable Standards and Regulations

- **IEEE 830:1998** — Software Requirements Specification.
- **UNE 157801:2007** — Information Systems Projects.
- **ISO/IEC 25010:2011** — Software quality model (basis for NFRs).
- **OpenAPI Specification 3.x** — REST API contract.
- **GDPR (EU) 2016/679** — Personal data processing.
- **OWASP Top 10 (2021)** — Web application security.

---

## 9. Implementation Status

| Component | Status | Notes |
|---|---|---|
| FastAPI Backend | Implemented | `api/src/` — domain, application, infrastructure complete |
| Celery Worker | Implemented | `api/src/infrastructure/workers/verification_worker.py` — real worker |
| Rust Engine | Implemented | `engine/src/` — evaluator, aggregator, 10 rules (RV-01…RV-10), parallel evaluation with Rayon |
| Angular Frontend | Implemented | `web/` — auth (2FA), dashboard, releases, connectors, profiles, admin, i18n ES/EN |
| Unit Tests | Implemented | `tests/unit/` — 200+ cases (12 files): services branch coverage, connectors CE+VL, endpoints Base Choice, DI factories, structural gaps. Cobertura total: 70% |
| Integration Tests | Implemented | `tests/integration/` — 16 Python cases (TC-INT-*) + 8 Rust HTTP tests (tc_int_http_*) |
| Acceptance Tests | Implemented | `tests/acceptance/` — 10 Cypress E2E cases (TC-ACP-CU/UI/FRM/USA) |
| Performance Tests | Implemented | `tests/performance/` — 4 Locust cases (TC-PER-*) + 3 Rust benchmarks (tc_per_pf_*) |
| Security Tests | Implemented | `tests/security/` — 5 cases (TC-SEC-AUT/INY/CIF): brute force, JWT, SQLi, XSS, encryption |

All tests follow the **Plan de Pruebas** structured according to **ISO 29119-4** with unique test case identifiers. See `docs/development/testing.md` for the complete test case catalog.

**Connected Routers (15 total):**
- auth, organizations, releases, connectors, profiles, tasks, users, custom_roles, dashboard, api_keys, templates, notifications, admin, audit, access_requests

**Endpoints per router:** 65+ endpoints implemented

---

*Last updated: June 2026 — Adrian Martinez Fuentes (UO295454)*

# SVAES Verification Engine — Technical Reference

The **Verification Engine** is the computational core of SVAES, implemented in **Rust** and exposed as a standalone HTTP microservice. It receives a payload of artifacts and verification rules, evaluates all rules in parallel, and returns a global verdict with detailed per-rule results.

---

## Architecture

The engine follows a **stateless, parallel** design:

| Technology | Role |
|---|---|
| **Actix-web 4** | HTTP server (port 8081 by default) |
| **Rayon** | Parallel rule evaluation via `par_iter()` |
| **Serde** | JSON serialization/deserialization |
| **thiserror** | Typed error handling |
| **log / env_logger** | Structured logging |

The engine has **no database access** and **no network I/O** beyond serving HTTP — it performs pure in-memory computation, making it deterministic and highly testable.

### Module Map

| Module | Purpose |
|---|---|
| `main.rs` | Entry point. Starts the Actix-web HTTP server. |
| `lib.rs` | Library root. Defines `AppState`, API key middleware, and handlers for `GET /health` and `POST /api/v1/verify`. |
| `models.rs` | Data structures: `Artifact`, `VerificationRule`, `VerificationPayload`, `RuleStatus`, `RuleEvaluation`, `Verdict`, `EngineResult`. |
| `evaluator.rs` | Core evaluation logic: dispatches each rule to its implementation function based on `rule_id`, runs them in parallel via Rayon. |
| `aggregator.rs` | Computes the global verdict from individual rule results (mandatory/optional/excluded policy). |
| `rules/rv01.rs`–`rules/rv10.rs` | Individual rule implementations (see below). |

---

## Verification Rules (RV-01 → RV-10)

Each rule receives configurable parameters via the `params` JSON object in the request payload and operates with documented defaults in its implementation.

| ID | Name | Default Severity | Description |
|---|---|---|---|
| RV-01 | Artifact Existence | BLOCKING | Artifact list must not be empty. |
| RV-02 | Artifact Traceability | BLOCKING | Code artifacts (`CODIGO`) must reference existing tasks (`TAREA`). |
| RV-03 | Artifact State | BLOCKING | All artifacts of a given type must have a status in the allowed set (e.g. `DONE`, `CLOSED`). |
| RV-04 | Numeric Field Integrity | BLOCKING | Numeric fields (`effort`, `estimation`) must be non-null, numeric, and ≥ 0. |
| RV-05 | Document Accessibility | BLOCKING | At least one artifact of a given type must have an accessibility flag set to `true`. |
| RV-06 | Attribute Coherence | NON_BLOCKING | Compares a metadata attribute (e.g. `version`) across artifacts of the same type against an expected value. |
| RV-07 | External Registration | BLOCKING | Looks for a marker artifact indicating external registration is complete (e.g. `PLAN` with `external_registered`). |
| RV-08 | List Alignment | BLOCKING | Compares IDs declared in a master artifact against actual artifact IDs in the payload. |
| RV-09 | Reference Validation | NON_BLOCKING | Validates URL and branch name formats. |
| RV-10 | Final Approval | BLOCKING | At least one artifact of a given type must have an approval status (e.g. `APPROVED`, `VALIDATED`). |

Each rule returns a `RuleEvaluation` with status `PASS`, `FAIL`, or `WARNING`.

---

## API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | None | Health check. Returns `{"status": "healthy", "service": "svaes-engine", "version": "1.0.0"}`. |
| `POST` | `/api/v1/verify` | API key | Evaluates a batch of rules against a set of artifacts. |

### Authentication

If `ENGINE_API_KEY` is configured, requests to `/api/v1/verify` must include the header:

```
X-Engine-Api-Key: <key>
```

If no key is configured, authentication is disabled (development mode). In production, the engine port is not exposed externally — only the API backend communicates with it.

---

## Data Structures

### Request (`POST /api/v1/verify`)

```json
{
  "artifacts": [
    {
      "id": "TASK-001",
      "artifact_type": "TAREA",
      "metadata": {
        "status": "DONE",
        "effort": 8
      }
    }
  ],
  "rules": [
    {
      "id": "RV-03",
      "severity": "BLOCKING",
      "params": {
        "artifact_type": "TAREA",
        "status_field": "status",
        "allowed_states": ["DONE", "CLOSED"]
      }
    }
  ]
}
```

### Response

```json
{
  "verdict": "VALID",
  "rule_results": [
    {
      "rule_id": "RV-03",
      "status": "PASS",
      "message": "All TAREA artifacts have a valid status."
    }
  ],
  "summary": "Verification completed: all mandatory rules passed.",
  "duration_ms": 12
}
```

---

## Verdict Aggregation Logic

| Condition | Global Verdict |
|---|---|
| Any `BLOCKING` rule returns `FAIL` | **INVALID** |
| All `BLOCKING` → `PASS`, any `NON_BLOCKING` → `WARNING` | **WITH_WARNINGS** |
| All active rules → `PASS` or `NOT_EVALUATED` | **VALID** |

If at least one rule returns `NOT_EVALUATED`, the suffix `_WITH_INCIDENTS` is appended as a secondary indicator.

**Precedence:** BLOCKING failures > NON_BLOCKING warnings > success.

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `ENGINE_HOST` | `0.0.0.0` | Bind address |
| `ENGINE_PORT` | `8081` | HTTP port |
| `ENGINE_API_KEY` | _(empty)_ | API key for authentication (empty = no auth) |
| `RUST_LOG` | `info` | Logging level (`info`, `debug`, `warn`, `error`) |

### Compilation Profile

The `Cargo.toml` release profile is configured for maximum performance:

```toml
[profile.release]
opt-level = 3
lto = true
codegen-units = 1
```

---

## Integration with the Backend

The FastAPI backend communicates with the engine via HTTP:

1. The Celery worker (`verification_worker.py`) receives a task from the queue.
2. It fetches artifact data from configured connectors.
3. It applies **pseudonymization** to artifact metadata (`core/pseudonymizer.py`).
4. It sends a `POST /api/v1/verify` request to the engine with artifacts and rules.
5. The engine evaluates all rules in parallel and returns the verdict.
6. The worker persists the `VerificationResult` and updates the release status.

---

## Running

### Local Development

```bash
cd engine
cargo run
```

### Docker

```bash
docker build -t svaes-engine -f engine/Dockerfile .
docker run -p 8081:8081 -e ENGINE_API_KEY=my-secret-key svaes-engine
```

### Docker Compose (full stack)

```bash
docker compose up --build
```

The engine service is included in all compose files and communicates internally with the API and worker services.

---

## Testing

Unit tests are embedded in each source file under `#[cfg(test)]`, following the **Plan de Pruebas** (ISO 29119-4):

| File | Test Count | Coverage |
|---|---|---|
| `src/aggregator.rs` | 7 tests | Verdict aggregation edge cases |
| `src/rules/rv01.rs`–`rv10.rs` | 3–7 each | Per-rule logic validation |

HTTP integration tests (8 cases: `tc_int_http_01`–`tc_int_http_08`) and performance benchmarks (3 cases: `tc_per_pf_01`–`tc_per_pf_03`) live in `engine/tests/`.

### Python Integration Tests

Python-level integration tests in `tests/integration/` cover the full verification flow, release lifecycle, rate limiting, resilience, and release migration (16 cases: TC-INT-*). These run against the FastAPI app via ASGI transport with ephemeral PostgreSQL + Redis containers.

```powershell
# Windows (PowerShell 7+) — full automation
.\scripts\run_integration_tests.ps1
```

### Run Commands (Rust)

```bash
cargo test                              # All unit tests
cargo test --test http_pipeline          # 8 HTTP integration tests
cargo test --test performance            # 3 performance benchmarks
cargo test -- --nocapture                # With stdout/stderr output
```

---

*Last updated: June 2026 — Adrian Martinez Fuentes*

# Performance Tests — Plan de Pruebas

Validates RNF-07 (verification engine processes 10 rules in under 500ms) plus a broader set of non-functional requirements (reliability, usability, maintainability, portability, extensibility, traceability, GDPR) and security-focused NFRs.

## Structure

```
performance/
├── conftest.py                  # PERF_API_BASE_URL, PERF_API_TOKEN, default headers
├── locustfile.py                # 4 Locust user classes — load tests (TC-PER-VL-*)
├── test_coverage_threshold.py   # 4 cases: traceability checks (Locust classes exist, coverage.xml >= 70%)
├── test_rnf_coverage.py         # 19 cases: functional NFRs (performance, reliability, usability, maintainability, portability, extensibility, traceability, GDPR)
└── test_rnf_security_rf.py      # 24 cases: security NFRs (password hashing, HTTPS, API key storage, audit logging, notification security)
```

## Locust load tests (`locustfile.py`)

| Class | Test ID | Description | Criteria |
|---|---|---|---|
| `E2EVerificationUser` | TC-PER-VL-01 | End-to-end flow: `GET /health` → `GET /releases` | p95 ≤ 5s |
| `RustEngineUser` | TC-PER-VL-02 | Engine latency via `GET /health` | p95 < 500ms |
| `ConcurrentVerifyUser` | TC-PER-VL-03 | 50 concurrent `POST /verify` | All return 202 (or 409 if already running) |
| `WebLoadUser` | TC-PER-RNF02-01 | 20 concurrent users hitting `/dashboard/metrics` and `/health` | Latency ≤ 3s |

```bash
# Web UI (http://localhost:8089)
locust -f tests/performance/locustfile.py --host=http://localhost:8000

# Headless
locust -f tests/performance/locustfile.py --host=http://localhost:8000 --users 50 --spawn-rate 10 --headless --run-time 60s

# A specific user class
locust -f tests/performance/locustfile.py WebLoadUser --users 20 --spawn-rate 20 --headless --run-time 30s
```

## pytest suites

```bash
pytest tests/performance/ -v -m performance             # everything
pytest tests/performance/test_coverage_threshold.py -v  # 4 cases, no server needed
pytest tests/performance/test_rnf_coverage.py -v        # 19 cases, needs api/src importable
pytest tests/performance/test_rnf_security_rf.py -v     # 24 cases
```

`test_rnf_security_rf.py` covers `TestPasswordHashing` (bcrypt), `TestHttpsEnforcement`, `TestApiKeyStorage`, `TestAuditLogging`, `TestNotificationSecurity`.

## Environment

| Variable | Default | Description |
|---|---|---|
| `PERF_API_BASE_URL` | `http://localhost:8000` | API base URL |
| `PERF_API_TOKEN` | _(empty)_ | JWT for authenticated requests |
| `ENGINE_URL` | `http://localhost:8081` | Rust engine URL (tests that call it directly) |

`test_rnf_coverage.py` and `test_rnf_security_rf.py` import `api/src` directly, so they also need the same env vars the API itself needs (`DATABASE_URL`, `JWT_SECRET_KEY`, `ENCRYPTION_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, ...) — see [.env.example](../../.env.example).

## Note on the Rust engine

There's no separate Rust performance-benchmark binary (`engine/tests/`) — engine-side timing is exercised indirectly through `RustEngineUser` (TC-PER-VL-02) hitting the running engine over HTTP. Engine unit tests live inline in `engine/src/` under `#[cfg(test)]` — see [engine/README.md](../../engine/README.md#tests-del-motor).

## Prerequisites

- API server running at `http://localhost:8000` (`cd api && uvicorn main:app --reload`)
- Engine running at `http://localhost:8081` for engine-latency cases
- `pip install -e ".[dev]"` from `api/` (installs `locust`, `pytest`, `respx`, ...)

## Troubleshooting

| Problem | Fix |
|---|---|
| `locust: command not found` | `pip install -e ".[dev]"` from `api/` |
| `ModuleNotFoundError: No module named 'core'` | Ensure `pytest.ini` has `pythonpath = api/src` |
| `respx not installed` | `pip install respx` |
| `Connection refused` in Locust | API isn't running at `PERF_API_BASE_URL` |
| RNF tests fail on import | Missing env vars — see [Environment](#environment) above |

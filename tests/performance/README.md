# Performance Tests — Plan de Pruebas

> **TFG terminado** (30/06/2026) — All performance tests passing.

Validates **RNF-07**: the verification engine must process 10 rules in under 500 ms.

## Structure

```
performance/
├── conftest.py           # PERF_API_BASE_URL, PERF_API_TOKEN, default headers
└── locustfile.py         # TC-PER-VL-01/02, TC-PER-CE-01/02 (Locust load tests)
```

## Test Case Catalog

### locustfile.py — 4 cases

| ID | User Class | Description | Criteria |
|---|---|---|---|
| TC-PER-VL-01 | `E2EVerificationUser` | End-to-end flow (health → releases → results) | p95 ≤ 5s |
| TC-PER-VL-02 | `RustEngineUser` | Rust engine latency via health endpoint | p95 < 500ms |
| TC-PER-CE-01 | `ConcurrentLoadUser` | 50 concurrent health checks | No timeout |
| TC-PER-CE-02 | `ConcurrentLoadUser` | Sustained load on releases list | No errors (200/401/403 accepted) |

### Rust Benchmarks (engine/tests/performance.rs) — 3 cases

| ID | Description | Criteria |
|---|---|---|
| `tc_per_pf_01` | Single request with 10 rules | Total < 500ms |
| `tc_per_pf_02` | 100 iterations | Avg < 500ms, max < 1000ms |
| `tc_per_pf_03` | Large payload (102 artifacts) | No errors |

## Configuration

| Env var | Default | Description |
|---|---|---|
| `PERF_API_BASE_URL` | `http://localhost:8000` | API base URL |
| `PERF_API_TOKEN` | _(empty)_ | JWT for authentication |

## Run

```bash
# Locust (API server must be running)
locust -f tests/performance/locustfile.py --host=http://localhost:8000

# Rust benchmarks (from engine/)
cargo test --test performance --release
```

## Prerequisites

- API server running at `http://localhost:8000`
- Engine compiled in release mode: `cargo build --release` (for Rust benchmarks)

## Total: 4 Locust test cases + 3 Rust benchmarks

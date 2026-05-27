# Performance Tests

Validates **RNF-07**: the verification engine must process 10 rules in under 500 ms.

## Structure

```
performance/
├── conftest.py           # API_BASE_URL, API_TOKEN, default headers
├── engine/
│   └── performance.rs    # 3 Rust benchmarks for RNF-07
└── locustfile.py         # STUB — Locust load tests
```

## Rust tests (engine/performance.rs)

| ID | Test | Criteria |
|----|------|----------|
| `tc_per_pf_01` | Single request with 10 rules | Total < 500 ms |
| `tc_per_pf_02` | 100 iterations | Avg < 500 ms, max < 1000 ms |
| `tc_per_pf_03` | Large payload (102 artifacts) | No errors |

## Configuration

| Env var | Default | Description |
|---------|---------|-------------|
| `PERF_API_BASE_URL` | `http://localhost:8000` | API base URL |
| `PERF_API_TOKEN` | *(empty)* | JWT for authentication |

## Run

```bash
# Rust (engine must be reachable)
cargo test --test performance --release

# Locust (pending)
locust -f tests/performance/locustfile.py --host=http://localhost:8000
```

## Prerequisites

- API server running at `http://localhost:8000`
- Engine compiled in release mode: `cargo build --release`

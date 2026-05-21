# Integration Tests

Black-box tests for the SVAES Rust verification engine, hitting the HTTP API to validate the full pipeline and measure performance.

## Files

| File | Tests | Purpose |
|------|-------|---------|
| `http_pipeline.rs` | 8 | HTTP interface and pipeline validation |
| `performance.rs` | 3 | Performance and concurrency under load |

## Running

All commands from the `engine/` directory.

```bash
# All integration tests
cargo test --test http_pipeline --test performance

# HTTP pipeline only
cargo test --test http_pipeline
cargo test --test http_pipeline -- --nocapture

# Performance (release mode required for meaningful timings)
cargo test --test performance --release
cargo test --test performance --release -- --nocapture

# Single test by name
cargo test --test http_pipeline tc_int_http_02
cargo test --test performance tc_per_vl_02_loop
```

## Test Catalog

### `http_pipeline.rs`

| ID | Function | Method | Description |
|----|----------|--------|-------------|
| TC-INT-HTTP-01 | `tc_int_http_01_health_endpoint_returns_healthy` | `GET /health` | Health endpoint responds OK |
| TC-INT-HTTP-02 | `tc_int_http_02_verify_valid_payload_returns_engine_result` | `POST /api/v1/verify` | Valid payload yields `Valida` with 10 rules |
| TC-INT-HTTP-03 | `tc_int_http_03_verify_error_payload_returns_no_valida` | `POST /api/v1/verify` | Invalid data yields `NoValida` |
| TC-INT-HTTP-04 | `tc_int_http_04_excluida_rules_are_skipped` | `POST /api/v1/verify` | EXCLUDED rules → `NoEvaluada` |
| TC-INT-HTTP-05 | `tc_int_http_05_unknown_rule_id_returns_no_evaluada` | `POST /api/v1/verify` | Unknown rule ID → `NoEvaluada` |
| TC-INT-HTTP-06 | `tc_int_http_06_engine_result_structure_is_complete` | `POST /api/v1/verify` | JSON structure and enum casing |
| TC-INT-HTTP-07 | `tc_int_http_07_empty_artifacts_with_rules_produces_errors` | `POST /api/v1/verify` | No artifacts → `NoValida` |
| TC-INT-HTTP-08 | `tc_int_http_08_pipeline_respects_optional_severity` | `POST /api/v1/verify` | Optional rule without match stays `Valida` |

### `performance.rs`

| ID | Function | Requirement | Description |
|----|----------|-------------|-------------|
| TC-PER-VL-02 | `tc_per_vl_02_ten_rules_execution_under_500ms` | RNF-07 | 10 rules < 500 ms |
| TC-PER-VL-02 | `tc_per_vl_02_loop_100_iterations_average_under_500ms` | RNF-07 | 100 iterations, avg < 500 ms |
| TC-PER-VL-02 | `tc_per_vl_02_large_payload_still_under_500ms` | RNF-07 | 102 artifacts + 10 rules < 500 ms |

## Conventions

- **Test IDs**: `TC-{TYPE}-{MODULE}-{NUM}` — `INT` = integration, `PER` = performance.
- `tests/` contains only black-box tests consuming the crate via `POST /api/v1/verify` and `GET /health`.
- Unit tests live in `src/` alongside their implementation files.

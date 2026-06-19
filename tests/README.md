# Tests — Plan de Pruebas (ISO 29119-4)

All tests follow a structured **Plan de Pruebas** with unique test case identifiers.

```
unit/           Unit tests — 150+ cases (TC-UNI-*): services, connectors, endpoints, domain, factories, gaps
integration/    Integration tests — 16 cases (TC-INT-*): full flow, rate limit, resilience, state transitions
security/       Security tests — 5 cases (TC-SEC-*): brute force, JWT, SQLi, XSS, credential encryption
performance/    Performance tests — 4 Locust cases (TC-PER-*) + 3 Rust benchmarks (tc_per_pf_*)
acceptance/     E2E acceptance tests — 10 Cypress cases (TC-ACP-*): visual, multi-res, forms, usability
```

| Level | Cases | Technique |
|---|---|---|
| TC-UNI | 150+ | Branch Coverage, CE+VL, Base Choice |
| TC-INT | 16 | Flow, Limit, Resilience, State Transition, Migration |
| TC-SEC | 5 | Auth, Injection, Encryption |
| TC-PER | 4 + 3 | Locust load + Rust benchmarks |
| TC-ACP | 10 | Cypress E2E + Usability |
| Engine | 8 HTTP + inline | Rust `#[cfg(test)]` in all 11 source files |

## Run

### Python

```bash
# Unit tests
pytest tests/unit/ -v -m unit

# Security tests
pytest tests/security/ -v -m security

# Full suite with coverage
pytest tests/unit/ tests/integration/ tests/security/ --cov=api/src --cov-report=term --cov-report=xml
```

### Integration tests (recommended: one-command script)

```powershell
.\scripts\run_integration_tests.ps1
```

The script spins up ephemeral PostgreSQL + Redis containers via `docker-compose.test.yml`, runs all integration tests, and tears down automatically.

Manual alternative:

```bash
pytest tests/integration/ -v -m integration
```

### E2E (acceptance)

```bash
npx cypress run --config-file tests/acceptance/cypress.config.js
```

### Engine (Rust)

```bash
cargo test                          # All inline unit tests (rules + aggregator)
cargo test --test http_pipeline     # 8 HTTP integration tests
cargo test --test performance --release  # 3 performance benchmarks

# Cobertura Rust
.\scripts\run_rust_coverage.ps1     # cargo llvm-cov con exclusiones configuradas
```

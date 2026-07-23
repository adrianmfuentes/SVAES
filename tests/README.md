# Tests — Plan de Pruebas (ISO 29119-4)

> **TFG terminado** (30/06/2026) — All test suites passing as of final delivery.

All tests follow a structured **Plan de Pruebas** with unique test case identifiers.

```
unit/           Unit tests — 1,238 cases (TC-UNI-*): services, connectors, endpoints, domain, factories, gaps
integration/    Integration tests — 27 cases (TC-INT-*): full flow, rate limit, resilience, state transitions, API keys
security/       Security tests — 5 cases (TC-SEC-*): brute force, JWT, SQLi, XSS, credential encryption
performance/    Performance tests — 47 pytest cases + 4 Locust user classes
acceptance/     E2E acceptance tests — 12 pytest + 43 Cypress cases (TC-ACP-*): visual, multi-res, forms, usability
```

| Level | Cases | Technique |
|---|---|---|
| TC-UNI | 1,238 | Branch Coverage, CE+VL, Base Choice |
| TC-INT | 27 | Flow, Limit, Resilience, State Transition, Migration, API Key Auth |
| TC-SEC | 5 | Auth, Injection, Encryption |
| TC-PER | 47 + 4 | pytest (RNF/coverage/security) + Locust load |
| TC-ACP | 12 + 43 | Cypress E2E + Usability |
| Engine | 86 | Rust `#[cfg(test)]` inline in `business_rules.rs`, `custom_field_check.rs`, `aggregator.rs` |

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

# Cobertura Rust
.\scripts\run_rust_coverage.ps1     # cargo llvm-cov con exclusiones configuradas
```

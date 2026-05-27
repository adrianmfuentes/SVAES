# Tests

```
unit/           Unit tests (isolated, mocked)
integration/    Integration tests (real DB, ASGI transport)
performance/    Performance tests (Rust benchmarks, Locust)
security/       Security tests (auth, injection, OWASP vectors)
acceptance/     E2E tests (Cypress against Angular frontend)
```

## Run

```bash
pytest tests/unit/ -v -m unit
pytest tests/integration/ -v -m integration
pytest tests/security/ -v -m security
cargo test --test http_pipeline
cargo test --test performance --release
npx cypress run --config-file tests/acceptance/cypress.config.js
```

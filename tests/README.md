# Tests

```
unit/           Unit tests (isolated, mocked)
integration/    Integration tests (real DB + Redis, ASGI transport)
performance/    Performance tests (Rust benchmarks, Locust)
security/       Security tests (auth, injection, OWASP vectors)
acceptance/     E2E tests (Cypress against Angular frontend)
```

## Run

### Python

```bash
pytest tests/unit/ -v -m unit
pytest tests/security/ -v -m security
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

### From engine/ (Rust)

```bash
cargo test --test http_pipeline
cargo test --test performance --release
```

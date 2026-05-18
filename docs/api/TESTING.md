# Testing — FastAPI API

Document for anyone who needs to understand how `api/` components are tested.

---

## Testing Dependencies

The dependencies already present in `pyproject.toml` are:

- `pytest >=8.0` — Test runner
- `pytest-asyncio >=0.24` — Support for `async` functions
- `pytest-cov >=5.0` — Coverage reports
- `httpx >=0.28.1` — Async HTTP client for integration tests

Still to be added:

```toml
pytest-mock       # mock creation
factory-boy       # factories for generating test data
faker             # fake data generation (names, emails, etc.)
testcontainers    # real PostgreSQL in containers for integration tests
```

---

## Test Location

All SVAES system tests live in `tests/` at the repository root:

```
tests/
├── conftest.py              # shared global fixtures
├── unit/                    # unit tests
│   ├── api/
│   │   ├── test_use_cases/
│   │   └── test_services/
│   └── ...                  # other domains if applicable
├── integration/             # integration tests
│   ├── api/
│   │   ├── test_routers/
│   │   └── test_repositories/
│   └── ...
├── performance/             # performance tests
└── acceptance/              # acceptance tests (BDD)
```

---

## Test Types

### Unit
Test **a single unit** (a use case, a service) **without any real I/O**.

- Redis, PostgreSQL, Celery: all mocked
- Very fast execution (under 1 second total)
- Technique: injected dependencies + mocks

### Integration
Test **a set of connected components** (e.g., a full router with its use case and real repository).

- Real PostgreSQL via `testcontainers`
- Data access layers are not mocked
- Slower execution (seconds per suite)

### Performance
Test that specific operations meet performance requirements (response time, throughput).

### Acceptance (BDD)
Test system behavior from the user's perspective, written in natural language.

---

## Key Concepts

### Mocks vs Stubs vs Fakes

- **Mock**: object that verifies interactions (which method was called, with what arguments)
- **Stub**: object that returns predefined responses
- **Fake**: simplified implementation that behaves like the real one but isn't (e.g., in-memory SQLite instead of PostgreSQL)

### Dependency Injection

Use cases and services receive their dependencies (repositories, handlers) as arguments or via FastAPI DI. This allows substituting them with mocks in unit tests without touching production code.

### Fixtures

Setup/teardown functions that provide data or resources to tests. The most important:

- `async_client` — async HTTP client that talks to the real app
- `db_session` — async database session
- `auth_headers` — authentication headers with a valid JWT token
- `postgres_container` — PostgreSQL container for integration tests

---

## Pytest Configuration

`pyproject.toml` already has `asyncio_mode = "auto"` configured, meaning any `async def test_*` function is automatically treated as an async test without the need for extra markers.

Relevant parameters:

| Parameter | Value | Description |
|---|---|---|
| `asyncio_mode` | `auto` | Detects async functions automatically |
| `testpaths` | `["../tests/api"]` | Folder where pytest looks for tests |
| `python_files` | `test_*.py` | File name pattern |
| `addopts` | `-v --cov=src` | Verbose + coverage |

---

## Coverage Targets

| Layer | Target |
|---|---|
| `routers` (api/src/infrastructure/primary/routers/) | 90%+ |
| `use_cases` (api/src/application/use_cases/) | 80%+ |
| `repositories` (api/src/infrastructure/secondary/database/repositories/) | 70%+ |
| `core` (api/src/core/) | 50%+ |

---

## Quick Examples

### Unit Test for a Use Case

```python
# tests/unit/api/test_use_cases/test_auth.py
import pytest
from unittest.mock import AsyncMock
from src.application.use_cases.main.auth import AuthService
from src.domain.entities import User

class TestAuthService:
    def test_login_returns_token_for_valid_user(self):
        mock_repo = AsyncMock()
        mock_repo.get_by_email.return_value = User(
            email="test@example.com",
            password_hash="$2b$12$hashed"
        )

        service = AuthService(user_repo=mock_repo)
        result = service.login("test@example.com", "password123")

        assert result.token is not None
        mock_repo.get_by_email.assert_called_once_with("test@example.com")
```

### Router Integration Test

```python
# tests/integration/api/test_routers/test_auth.py
import pytest
from httpx import AsyncClient

class TestAuthRouter:
    @pytest.mark.asyncio
    async def test_login_returns_200_with_token(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "password123"}
        )

        assert response.status_code == 200
        assert "token" in response.json()
```

---

## External Dependencies in Tests

| Service | Unit test | Integration test |
|---|---|---|
| PostgreSQL | Mocked | `testcontainers` |
| Redis | Mocked with `fakeredis` | Real `fakeredis` or mocked |
| Celery | Mocked | Real tasks in real queue or mocked |
| External HTTP | `httpx.MockTransport` | Real `httpx` or `respx` |

---

## Running Tests

```bash
# All tests
pytest

# Unit only
pytest tests/unit/

# Integration only
pytest tests/integration/

# With coverage
pytest --cov=api/src --cov-report=html

# With coverage and verbose
pytest -v --cov=api/src --cov-report=term-missing
```

---

## Notes for Contributors

1. **No test should be committed if it knowingly lets a bug pass without justification**. Tests exist to catch regressions.
2. **Integration tests touch a real database**. If you need seed data, add it in `conftest.py` via factories — not manually in the DB.
3. **Mocks live in `conftest.py` or in the file that uses them**. Do not hardcode mock logic inside the test.
4. **Coverage is a tool, not a goal in itself**. A test that tests nothing and only increases the percentage is worthless.

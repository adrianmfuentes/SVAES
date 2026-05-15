# Testing — API FastAPI

Documento para cualquier persona que necesite entender cómo se prueban los componentes de `api/`.

---

## Dependencias de testing

Las dependencias ya presentes en `pyproject.toml` son:

- `pytest >=8.0` — Test runner
- `pytest-asyncio >=0.24` — Soporte para funciones `async`
- `pytest-cov >=5.0` — Reportes de cobertura
- `httpx >=0.28.1` — Cliente HTTP async para tests de integración

Faltan por agregar:

```toml
pytest-mock       # creación de mocks
factory-boy       # factories para generar datos de test
faker             # generación de datos falsos (nombres, emails, etc.)
testcontainers    # PostgreSQL real en containers para tests de integración
```

---

## Ubicación de los tests

Todos los tests del sistema SVAES viven en `tests/` en la raíz del repositorio:

```
tests/
├── conftest.py              # fixtures globales compartidas
├── unit/                    # tests unitarios
│   ├── api/
│   │   ├── test_use_cases/
│   │   └── test_services/
│   └── ...                  # otros dominios si aplican
├── integration/             # tests de integración
│   ├── api/
│   │   ├── test_routers/
│   │   └── test_repositories/
│   └── ...
├── performance/             # tests de rendimiento
└── acceptance/              # tests de aceptación (BDD)
```

---

## Tipos de tests

### Unitarios
Prueban **una sola unidad** (un use case, un servicio) **sin ningún I/O real**.

- Redis, PostgreSQL, Celery: todos mockeados
- Ejecución muy rápida (menos de 1 segundo en total)
- Técnica: injected dependencies + mocks

### Integración
Prueban **un conjunto de componentes conectados** (por ejemplo, un router completo con su use case y repositorio real).

- PostgreSQL real via `testcontainers`
- No se mockean las capas de acceso a datos
- Ejecución más lenta (segundos por suite)

### Performance
Prueban que operaciones concretas cumplan requisitos de rendimiento (tiempo de respuesta, throughput).

### Aceptación (BDD)
Prueban el comportamiento del sistema desde el punto de vista del usuario, escritas en lenguaje natural.

---

## Conceptos clave

### Mocks vs Stubs vs Fakes

- **Mock**: objeto que verifica interacciones (qué método se llamó, con qué argumentos)
- **Stub**: objeto que devuelve respuestas predefinidas
- **Fake**: implementación simplificada que se comporta como la real pero no es la real (ej: SQLite en memoria en lugar de PostgreSQL)

### Inyección de dependencias

Los use cases y servicios reciben sus dependencias (repositorios, handlers) como argumentos o vía FastAPI DI. Esto permite sustituirlos por mocks en tests unitarios sin tocar el código de producción.

### Fixtures

Son funciones de setup/teardown que proporcionan datos o recursos a los tests. Las más importantes:

- `async_client` — cliente HTTP async que habla con la app real
- `db_session` — sesión de base de datos async
- `auth_headers` — headers de autenticación con un token JWT válido
- `postgres_container` — container de PostgreSQL para tests de integración

---

## Configuración de pytest

En `pyproject.toml` ya está configurado `asyncio_mode = "auto"`, lo que significa que cualquier función `async def test_*` se trata automáticamente como un test asíncrono sin necesidad de marcadores extra.

Parámetros relevantes:

| Parámetro | Valor | Descripción |
|---|---|---|
| `asyncio_mode` | `auto` | Detecta funciones async automáticamente |
| `testpaths` | `["../tests/api"]` | Carpeta donde pytest busca tests |
| `python_files` | `test_*.py` | Patrón para文件名 |
| `addopts` | `-v --cov=src` | Verbose + coverage |

---

## Cobertura objetivo

| Capa | Objetivo |
|---|---|
| `routers` (api/ src/infrastructure/primary/routers/) | 90%+ |
| `use_cases` (api/ src/application/use_cases/) | 80%+ |
| `repositories` (api/ src/infrastructure/secondary/database/repositories/) | 70%+ |
| `core` (api/ src/core/) | 50%+ |

---

## Ejemplos rápidos

### Test unitario de un use case

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

### Test de integración de un router

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

## Dependencias externas en tests

| Servicio | Unit test | Integración test |
|---|---|---|
| PostgreSQL | Mockeado | `testcontainers` |
| Redis | Mockeado con `fakeredis` | `fakeredis` real o mockeado |
| Celery | Mockeado | Tareas reales en cola real o mockeadas |
| HTTP externo | `httpx.MockTransport` | `httpx` real o `respx` |

---

## Ejecutar los tests

```bash
# Todos los tests
pytest

# Solo unitarios
pytest tests/unit/

# Solo integración
pytest tests/integration/

# Con coverage
pytest --cov=api/src --cov-report=html

# Con coverage y verbose
pytest -v --cov=api/src --cov-report=term-missing
```

---

## Notas para quienes contributean

1. **Ningún test puede hacer commit si deja pasar un bug已知 sin justificacion**. Los tests existen para atrapar regresiones.
2. **Los tests de integración tocan base de datos real**. Si necesitas datos de seed, agrégalos en `conftest.py` via factories — no a mano en la DB.
3. **Los mocks viven en `conftest.py` o en el archivo que los usa**. No hardcodear lógica de mock dentro del test.
4. **El coverage es una herramienta, no un objetivo en sí mismo**. Un test que no testa nada y solo sube el porcentaje no vale nada.
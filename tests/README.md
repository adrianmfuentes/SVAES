# Tests — SVAES

Suite de pruebas del sistema SVAES. Organizada en niveles siguiendo la piramide de testing: unitarias, integracion, rendimiento, seguridad y aceptacion.

## Estructura

```
tests/
├── unit/                    # Pruebas unitarias (Python + Rust)
│   ├── connectors/          # Conectores externos (GitLab, Jira)
│   └── api/                 # Casos de uso y servicios de la API
├── integration/             # Pruebas de integracion (Python + Rust)
│   └── engine/              # Pipeline HTTP del motor de verificacion
├── performance/             # Pruebas de rendimiento (Rust + Locust)
│   └── engine/              # Rendimiento del motor (req. RNF-07)
├── security/                # Pruebas de seguridad (inyeccion, autenticacion)
└── acceptance/              # Pruebas E2E con Cypress
    └── cypress/
        ├── e2e/             # Escenarios de aceptacion
        └── support/         # Comandos y configuracion Cypress
```

## Niveles de Prueba

### 1. Unitarias (`tests/unit/`)

Validan componentes aislados con dependencias mockeadas. No requieren base de datos ni servicios externos.

**Conectores externos:**
- `test_gitlab.py` — GitLabConnector: headers, URLs, `fetch_artifact()`, `list_artifacts()`, `_get()`/`_post()`, manejo de errores HTTP.
- `test_jira.py` — JiraConnector: autenticacion Atlassian, JQL, `fetch_artifact()`, `list_artifacts()`, errores.

**API / Casos de uso:**
- `test_releases.py` — CreateReleaseUseCase: creacion, consulta, actualizacion, cambio de estado, artefactos, eliminacion, restauracion y validacion SemVer (14 validos + 11 invalidos).

**Ejecucion:**

```bash
pytest tests/unit/ -v -m unit
```

### 2. Integracion (`tests/integration/`)

Validan la interaccion entre componentes reales con base de datos de prueba.

**Motor de verificacion (Rust):**
- `engine/http_pipeline.rs` — 8 tests HTTP contra el motor real: health, payload valido, errores, reglas excluidas, reglas desconocidas, estructura de respuesta, artefactos vacios, severidad opcional.

**Pendientes de implementar (stubs):**
- `test_flow.py` — Flujo completo de verificacion
- `test_release_lifecycle.py` — Ciclo de vida de releases
- `test_resilience.py` — Tolerancia a fallos
- `test_rate_limit.py` — Limitacion de tasa

**Ejecucion:**

```bash
# Python
pytest tests/integration/ -v -m integration

# Rust (motor)
cargo test --test http_pipeline
```

### 3. Rendimiento (`tests/performance/`)

Validan el requisito no funcional **RNF-07**: el motor debe procesar 10 reglas en menos de 500 ms.

- `engine/performance.rs` — 3 tests: peticion unica con 10 reglas (< 500 ms), 100 iteraciones (media < 500 ms, max < 1000 ms), payload grande con 102 artefactos.

**Pendiente:**
- `locustfile.py` — Pruebas de carga con Locust

**Ejecucion:**

```bash
cargo test --test performance --release

# Locust (pendiente)
locust -f tests/performance/locustfile.py
```

### 4. Seguridad (`tests/security/`)

Infraestructura preparada con payloads maliciosos y generacion de JWT reales.

**Fixtures disponibles en `conftest.py`:**
- `malicious_payloads` — 9 vectores de ataque: SQL injection, XSS, DROP, SSTI, path traversal, prototype pollution, constructor access, template injection.
- `auth_token` — JWT real con rol U3
- `basic_user_token` — JWT con rol U1
- `unauth_headers` — Token invalido

**Pendientes de implementar:**
- `test_auth.py` — Bypass de autenticacion, escalado de privilegios, tokens expirados
- `test_injection.py` — Inyeccion en endpoints con los payloads maliciosos

**Ejecucion:**

```bash
pytest tests/security/ -v -m security
```

### 5. Aceptacion (`tests/acceptance/`)

Pruebas end-to-end con Cypress contra el frontend Angular.

**Configuracion:**
- Base URL: `http://localhost:4200`
- Viewport: 1280x720
- Timeout: 10 s

**Comandos personalizados:**
- `cy.login(email, password)` — Inicia sesion en la aplicacion
- `cy.logout()` — Cierra sesion

**Pendientes de implementar:**
- `cu01_verificar.cy.js` — Caso de uso: verificacion de release
- `form_validation.cy.js` — Validacion de formularios

**Ejecucion:**

```bash
npx cypress run --config-file tests/acceptance/cypress.config.js
```

## Marcadores de Pytest

Configurados en `pytest.ini`:

| Marcador | Uso |
|----------|-----|
| `unit` | Tests unitarios |
| `integration` | Tests de integracion |
| `security` | Tests de seguridad |
| `e2e` | Tests end-to-end |
| `slow` | Tests lentos (excluibles con `-m "not slow"`) |

```bash
# Ejecutar solo unitarios e integracion
pytest -v -m "unit or integration"

# Excluir tests lentos
pytest -v -m "not slow"

# Ejecutar todo
pytest -v
```

## Convenciones

- **IDs de caso de prueba**: Cada test documenta su identificador en docstring (ej: `TC-UNI-AGG-01`, `tc_int_http_01`, `tc_per_vl_02`).
- **Mocking**: Los tests unitarios en Python usan `unittest.mock.AsyncMock` para repositorios y `httpx.AsyncClient`. Los conectores mockean las respuestas HTTP.
- **TestDatabase**: Los tests de integracion y seguridad crean/eliminan tablas por sesion con `SQLAlchemy`.
- **Rust inline tests**: Las reglas del motor contienen sus tests unitarios en el mismo archivo fuente con `#[cfg(test)]`.

## Requisitos

```bash
# Python
pip install pytest pytest-asyncio httpx

# Rust
cargo build

# Cypress (para tests de aceptacion)
npm install cypress
```

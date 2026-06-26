# Guia de Pruebas de Rendimiento — SVAES

> **ISO 29119-4** | Rendimiento + Cobertura RNF + Seguridad + Locust

---

## 1. Estructura de archivos

```
tests/performance/
├── GUIA.md                      ← este archivo
├── README.md                    ← documentacion original (catalogo de casos)
├── conftest.py                  ← variables de entorno y configuracion base
├── locustfile.py                ← 4 casos de carga con Locust (web UI)
├── test_coverage_threshold.py   ← 4 pruebas estructurales de trazabilidad
├── test_rnf_coverage.py         ← 18 pruebas RNF (pytest)
└── test_rnf_security_rf.py      ← 16 pruebas de seguridad RNF (pytest)
```

---

## 2. Prerrequisitos

### 2.1 Dependencias Python

Instalar desde `api/pyproject.toml`:

```powershell
# Desde la raiz del proyecto
cd api
pip install -e ".[dev]"
```

Paquetes clave necesarios:
| Paquete | Version | Proposito |
|---|---|---|
| `locust` | `>=2.44.4` | Pruebas de carga HTTP |
| `pytest` | `>=9.1.1` | Ejecutor de pruebas |
| `pytest-asyncio` | `>=1.4.0` | Soporte async/await |
| `pytest-cov` | `>=7.1.0` | Informes de cobertura |
| `httpx` | `>=0.28.1` | Cliente HTTP para ASGI |
| `respx` | _(recomendado)_ | Mock HTTP del motor Rust |

### 2.2 Servidores necesarios

| Servicio | URL por defecto | Variable de entorno | Obligatorio |
|---|---|---|---|
| **API (FastAPI)** | `http://localhost:8000` | `PERF_API_BASE_URL` | Si (Locust + algunos pytest) |
| **Motor Rust** | `http://localhost:8081` | `ENGINE_URL` | Si (para pruebas que llaman al motor) |

### 2.3 Variables de entorno

```powershell
# Variables requeridas para las pruebas
$env:PERF_API_BASE_URL = "http://localhost:8000"     # URL de la API
$env:PERF_API_TOKEN = ""                              # JWT token (opcional)
$env:DATABASE_URL = "sqlite+aiosqlite:///:memory:"    # BD en memoria
$env:ENVIRONMENT = "test"                             # Modo test
$env:JWT_SECRET_KEY = "rnf-coverage-test-secret-key-32ch!"
$env:JWT_ALGORITHM = "HS256"
$env:JWT_EXPIRE_MINUTES = "60"
$env:ALLOWED_ORIGINS = "*"
$env:ENCRYPTION_KEY = "HnVk8Q2xLm9pR4sT6wYzA1bC3dF5gJ7kN="
$env:REDIS_URL = "redis://localhost:6379/0"
$env:CELERY_BROKER_URL = "redis://localhost:6379/0"
$env:CELERY_RESULT_BACKEND = "redis://localhost:6379/0"
$env:ENGINE_URL = "http://localhost:8081"
$env:ENGINE_API_KEY = "test-engine-api-key"
$env:ADMIN_EMAIL = "admin@test.local"
$env:ADMIN_PASSWORD = "AdminPass1"
$env:API_KEY_PEPPER = "test-pepper-value"
```

---

## 3. Como ejecutar cada tipo de prueba

### 3.1 Pruebas Locust (carga HTTP con interfaz web)

**Prerrequisito:** El servidor API debe estar corriendo en `http://localhost:8000`.

```powershell
# Opcion A — Interfaz web (recomendado para desarrollo)
locust -f tests/performance/locustfile.py --host=http://localhost:8000

# Opcion B — Headless (sin interfaz, para CI/CD)
locust -f tests/performance/locustfile.py --host=http://localhost:8000 `
  --users 50 --spawn-rate 10 --headless --run-time 60s

# Opcion C — WebLoadUser (20 usuarios web, latencia <= 3s)
locust -f tests/performance/locustfile.py WebLoadUser `
  --users 20 --spawn-rate 20 --headless --run-time 30s
```

Al abrir la interfaz web: navega a `http://localhost:8089`, configura:
- **Number of users:** 50
- **Spawn rate:** 10
- **Host:** `http://localhost:8000`

Haz click en **Start swarming**.

### 3.2 Pruebas pytest de rendimiento (todas a la vez)

```powershell
# Ejecutar TODAS las pruebas de rendimiento
pytest tests/performance/ -v -m performance

# Solo las de cobertura estructural (4 pruebas rapidas, sin servidor)
pytest tests/performance/test_coverage_threshold.py -v

# Solo las de RNF (18 pruebas, requieren imports de api/src)
pytest tests/performance/test_rnf_coverage.py -v

# Solo las de seguridad (16 pruebas)
pytest tests/performance/test_rnf_security_rf.py -v
```

---

## 4. Catalogo completo de casos de prueba

### 4.1 Locust — Pruebas de carga (4 casos)

| ID | Archivo | User Class | Descripcion | Criterio |
|---|---|---|---|---|
| `TC-PER-VL-01` | `locustfile.py` | `E2EVerificationUser` | Flujo E2E: GET /health -> GET /releases | p95 <= 5s |
| `TC-PER-VL-02` | `locustfile.py` | `RustEngineUser` | Latencia del motor Rust via GET /health | p95 < 500ms |
| `TC-PER-VL-03` | `locustfile.py` | `ConcurrentVerifyUser` | 50 POST /verify simultaneos | Todas retornan 202 |
| `TC-PER-CE-04` | — | — | Cobertura >= 70% via SonarCloud | Validado en CI/CD |

### 4.2 pytest — Trazabilidad (4 casos)

| ID | Archivo | Descripcion |
|---|---|---|
| `TC-PER-VL-01` | `test_coverage_threshold.py` | Verifica que existe `E2EVerificationUser` con umbral p95 <= 5s |
| `TC-PER-VL-02` | `test_coverage_threshold.py` | Verifica que existe `RustEngineUser` con umbral < 500ms |
| `TC-PER-VL-03` | `test_coverage_threshold.py` | Verifica `ConcurrentVerifyUser` con 50 usuarios |
| `TC-PER-CE-04` | `test_coverage_threshold.py` | Valida que `coverage.xml` existe y line-rate >= 70% (RNF-27) |

### 4.3 pytest — No Funcionales RNF (18 casos)

**Rendimiento:**
| ID | Descripcion | Criterio |
|---|---|---|
| `TC-PER-RNF01-01` | 10 reglas procesadas por el motor | <= 30s (mock respx) |
| `TC-PER-RNF02-01` | Clase WebLoadUser con 20 usuarios | Latencia <= 3s |
| `TC-PER-RNF04-01` | Dashboard con 1000 verificaciones | <= 3s |
| `TC-PER-RNF05-01` | Consultas simples a la API | < 500ms |

**Fiabilidad:**
| ID | Descripcion | Criterio |
|---|---|---|
| `TC-FIA-RNF09-01` | Falla de un conector no aborta verificacion global | Continua procesando |
| `TC-FIA-RNF10-01` | Errores criticos se registran en el log | <= 5s |
| `TC-FIA-RNF11-01` | Tasa de fallo en 1000 iteraciones | < 0.1% |

**Usabilidad:**
| ID | Descripcion |
|---|---|
| `TC-USA-RNF22-01` | Viewport responsive en 4 breakpoints (index.html + SCSS media queries) |

**Mantenibilidad:**
| ID | Descripcion |
|---|---|
| `TC-MNT-RNF25-01` | Capa de dominio sin imports de infraestructura (AST scan) |
| `TC-MNT-RNF26-01` | Nuevo conector registrable sin cambios en el motor |
| `TC-MNT-RNF28-01` | >= 50% de endpoints del router tienen docstrings |

**Portabilidad:**
| ID | Descripcion |
|---|---|
| `TC-POR-RNF31-01` | README.md contiene pasos de despliegue (docker, docker compose, pip/npm) |

**Extensibilidad:**
| ID | Descripcion |
|---|---|
| `TC-EXT-RNF32-01` | /openapi.json incluye paths de conectores |
| `TC-EXT-RNF33-01` | Reglas actuan como plugins sin modificar el motor |
| `TC-EXT-RNF34-01` | Nuevo canal de notificacion sin modificar el core |

**Trazabilidad:**
| ID | Descripcion |
|---|---|
| `TC-TRZ-RNF35-01` | Log de verificacion tiene origen, recurso, resultado y timestamp |
| `TC-TRZ-RNF37-01` | Todos los requisitos funcionales trazan a casos de uso o reglas |

**Organizacionales/RGPD:**
| ID | Descripcion |
|---|---|
| `TC-ORG-RNF38-01` | Endpoints GDPR de exportacion y eliminacion de cuenta funcionales |
| `TC-ORG-RNF40-01` | /openapi.json retorna especificacion OpenAPI 3.x valida |

### 4.4 pytest — Seguridad (16 casos)

| Clase | Tests | RNF | Descripcion |
|---|---|---|---|
| `TestPasswordHashing` | 6 | RNF-12 | bcrypt hashing, salt, verificacion, no reversible |
| `TestHttpsEnforcement` | 3 | RNF-15 | Redirect HTTPS, header HSTS |
| `TestApiKeyStorage` | 4 | RNF-16 | Columna key_hash, prefijo, hash antes de guardar, credenciales cifradas |
| `TestAuditLogging` | 6 | RNF-17 | Enum AuditEvent, logger de auditoria, campos, persistencia |
| `TestNotificationSecurity` | 5 | RNF-18 | Sin exposicion de credenciales, sanitizacion, sin texto claro, auth requerida |

---

## 5. Flujo de trabajo recomendado

### Paso 1 — Arrancar la API

```powershell
cd api
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Paso 2 — Ejecutar pruebas rapidas (sin servidor)

```powershell
# Estas NO requieren servidor corriendo
pytest tests/performance/test_coverage_threshold.py -v
pytest tests/performance/test_rnf_security_rf.py -v
```

### Paso 3 — Ejecutar pruebas RNF (algunas requieren servidor)

```powershell
pytest tests/performance/test_rnf_coverage.py -v -m performance
```

### Paso 4 — Ejecutar pruebas de carga Locust

```powershell
locust -f tests/performance/locustfile.py --host=http://localhost:8000
```

### Paso 5 — Todo junto

```powershell
# Todas las pruebas de rendimiento (pytest + Locust headless)
pytest tests/performance/ -v
locust -f tests/performance/locustfile.py --host=http://localhost:8000 --users 50 --spawn-rate 10 --headless --run-time 60s
```

---

## 6. Pruebas Rust (benchmarks del motor)

Estos benchmarks estan documentados pero el archivo `engine/tests/performance.rs` **no existe aun** en disco. Casos previstos:

| ID | Descripcion | Criterio |
|---|---|---|
| `TC-PER-PF-01` | 1 peticion con 10 reglas | Total < 500ms |
| `TC-PER-PF-02` | 100 iteraciones | Media < 500ms, max < 1000ms |
| `TC-PER-PF-03` | Carga grande (102 artefactos) | Sin errores |

Cuando se implemente, se ejecuta con:

```powershell
cd engine
cargo test --test performance --release
```

---

## 7. Troubleshooting

| Problema | Solucion |
|---|---|
| `locust: command not found` | `pip install locust` o reinstalar con `pip install -e ".[dev]"` desde `api/` |
| `ModuleNotFoundError: No module named 'core'` | Asegurar que `pytest.ini` tiene `pythonpath = api/src` |
| `respx not installed` | `pip install respx` (necesario para `test_tc_per_rnf01_01`) |
| `coverage.xml no encontrado` | Generarlo: `pytest tests/unit/ tests/security/ --cov=api/src --cov-report=xml` |
| `Connection refused` en Locust | Verificar que la API esta corriendo en `http://localhost:8000` |
| Tests de RNF fallan por imports | Verificar variables de entorno (`DATABASE_URL`, `ENVIRONMENT`, etc.) |
| El motor Rust no responde | `cd engine && cargo run` en puerto 8081 |

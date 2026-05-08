# Suite de Pruebas — SVAES

Este directorio contiene la infraestructura de pruebas del sistema **SVAES**
(*Sistema de Verificación y Aprobación de Entregas de Software*). Las pruebas
están organizadas por nivel de aislamiento siguiendo la pirámide de testing
clásica, lo que permite balancear velocidad de ejecución, fidelidad al entorno
de producción y granularidad diagnóstica.

---

## Índice

1. [Filosofía de testing](#1-filosofía-de-testing)
2. [Estructura de directorios](#2-estructura-de-directorios)
3. [Cobertura unitaria actual](#3-cobertura-unitaria-actual)
4. [Convenciones de nomenclatura y estilo](#4-convenciones-de-nomenclatura-y-estilo)
5. [Ejecución de pruebas](#5-ejecución-de-pruebas)
6. [Configuración de pytest](#6-configuración-de-pytest)
7. [Dobles de prueba y estrategia de aislamiento](#7-dobles-de-prueba-y-estrategia-de-aislamiento)
8. [Cobertura de código](#8-cobertura-de-código)
9. [Niveles pendientes de implementación](#9-niveles-pendientes-de-implementación)

---

## 1. Filosofía de testing

SVAES adopta una arquitectura hexagonal (Ports & Adapters) que separa
estrictamente el dominio, la capa de aplicación y la infraestructura. Esta
separación tiene una implicación directa sobre la estrategia de pruebas:

- **La lógica de negocio** (entidades de dominio y casos de uso) puede y debe
  probarse en completo aislamiento de bases de datos, colas de mensajes y
  servicios externos.
- **Los adaptadores de infraestructura** (repositorios SQLAlchemy, cliente JWT,
  etc.) se prueban con sesiones mockeadas para verificar el mapeo de entidades
  sin requerir una conexión real.
- **Los flujos de extremo a extremo** se validan en pruebas E2E que levantan
  la aplicación completa contra entornos efímeros.

Este diseño maximiza la velocidad del ciclo de retroalimentación durante el
desarrollo: las 177 pruebas unitarias se ejecutan en menos de 3 segundos sin
requerir ninguna dependencia de infraestructura real.

---

## 2. Estructura de directorios

```
tests/
├── README.md                        ← este documento
│
├── unit/                            ← pruebas de aislamiento total (sin I/O real)
│   ├── conftest.py                  ← sys.path y DATABASE_URL dummy para imports
│   │
│   ├── api/
│   │   ├── test_dependencies.py     ← get_current_user (FastAPI dependency)
│   │   └── test_routers.py          ← handlers de auth, orgs, projects, profiles,
│   │                                   releases y connectors
│   │
│   ├── application/
│   │   └── use_cases/
│   │       ├── test_auth_use_cases.py
│   │       ├── test_organization_use_cases.py
│   │       ├── test_project_use_cases.py
│   │       ├── test_create_release.py
│   │       ├── test_launch_verification.py
│   │       ├── test_configure_connector.py
│   │       ├── test_manage_profile.py
│   │       └── test_get_verification_history.py
│   │
│   ├── domain/
│   │   └── test_entities.py         ← entidades, enums y excepciones de dominio
│   │
│   └── infrastructure/
│       ├── test_repositories.py     ← repositorios SQLAlchemy (sesión mockeada)
│       └── test_security.py         ← JWT, Fernet, MockTaskQueue, ConnectorRegistry,
│                                       logging y Settings
│
├── integration/                     ← pruebas con base de datos y servicios reales
│   └── .gitkeep
│
├── e2e/                             ← pruebas de extremo a extremo (aplicación completa)
│   └── .gitkeep
│
├── performance/                     ← benchmarks y pruebas de carga
│   └── .gitkeep
│
└── security/                        ← pruebas de seguridad automatizadas (SAST/DAST)
    └── .gitkeep
```

---

## 3. Cobertura unitaria actual

### `test_dependencies.py` — `TestGetCurrentUser`

| Test | Escenario |
|------|-----------|
| `test_valid_token_returns_user` | Token válido → usuario devuelto por el repositorio |
| `test_invalid_token_raises_401` | `InvalidTokenError` → HTTP 401 con cabecera `WWW-Authenticate` |
| `test_missing_sub_claim_raises_401` | Payload sin campo `sub` → HTTP 401 |
| `test_invalid_uuid_in_sub_raises_401` | `sub` con UUID malformado → HTTP 401 |
| `test_user_not_found_raises_401` | Token válido pero usuario inexistente → HTTP 401 |

---

### `test_routers.py` — handlers de la capa API

#### `TestAuthRouter`

| Test | Escenario |
|------|-----------|
| `test_login_success_returns_token` | Credenciales correctas → `access_token` y `token_type = "bearer"` |
| `test_login_exception_raises_401` | `ValueError` del caso de uso → HTTP 401 |
| `test_login_generic_exception_raises_401` | `RuntimeError` inesperado → HTTP 401 |

#### `TestOrganizationsRouter`

| Test | Escenario |
|------|-----------|
| `test_create_org_returns_organization` | Handler devuelve la instancia del repositorio |
| `test_create_org_passes_plan` | Campo `plan` del request se propaga al comando |
| `test_list_orgs_returns_list` | Lista con elementos devuelta sin transformación |
| `test_list_orgs_empty_list` | Lista vacía devuelta sin excepción |

#### `TestProjectsRouter`

| Test | Escenario |
|------|-----------|
| `test_create_project_success` | Handler devuelve el proyecto del caso de uso |
| `test_create_project_passes_correct_command` | `organization_id`, `name` y `description` se mapean al comando |

#### `TestProfilesRouter`

| Test | Escenario |
|------|-----------|
| `test_create_profile_success` | `create_profile` invocado una vez; resultado devuelto |

#### `TestReleasesRouter`

| Test | Escenario |
|------|-----------|
| `test_create_release_success` | Release devuelta por el caso de uso |
| `test_create_release_passes_creator` | `created_by` propagado desde el usuario autenticado |
| `test_get_results_success` | Diccionario de resultados devuelto con campo `verdict` |
| `test_get_results_not_found_raises_404` | `EntityNotFoundError` → HTTP 404 |
| `test_verify_release_success` | `task_id` y mensaje de confirmación en la respuesta |
| `test_verify_release_not_found_raises_404` | `EntityNotFoundError` → HTTP 404 |
| `test_verify_release_invalid_state_raises_409` | `ReleaseInvalidStateError` → HTTP 409 |
| `test_verify_release_runtime_error_raises_500` | `RuntimeError` → HTTP 500 |
| `test_verify_release_value_error_raises_500` | `ValueError` → HTTP 500 |

#### `TestConnectorsRouter`

| Test | Escenario |
|------|-----------|
| `test_create_connector_success` | Conector del caso de uso devuelto directamente |
| `test_create_connector_connection_failed_raises_400` | `ConnectorConnectionFailedError` → HTTP 400 |
| `test_create_connector_runtime_error_raises_500` | `RuntimeError` → HTTP 500 |
| `test_create_connector_value_error_raises_500` | `ValueError` → HTTP 500 |

---

### `test_auth_use_cases.py` — `LoginUseCase`

| Test | Escenario |
|------|-----------|
| `test_valid_credentials_return_token` | Credenciales correctas → JWT con `user_id` y `role` |
| `test_user_not_found_raises_value_error` | Email inexistente → `ValueError` genérico |
| `test_wrong_password_raises_value_error` | Contraseña errónea → `ValueError` genérico |
| `test_token_not_issued_when_user_not_found` | Fallo de auth → `ITokenService` no invocado |

**Invariante de seguridad:** mensaje de error idéntico para email inexistente y
contraseña incorrecta, impidiendo la enumeración de usuarios.

---

### `test_organization_use_cases.py` — `CreateOrganizationUseCase` / `ListOrganizationsUseCase`

| Test | Escenario |
|------|-----------|
| `test_creates_and_returns_organization` | Resultado es la instancia devuelta por el repositorio |
| `test_passes_correct_slug_to_repo` | `name` y `slug` del comando se transfieren fielmente |
| `test_default_plan_is_free` | Plan por defecto es `"free"` sin especificarlo |
| `test_returns_active_organizations` | Listado llama a `list_all(active_only=True)` |
| `test_returns_empty_list_when_no_orgs` | Sin organizaciones activas → lista vacía, sin excepción |

---

### `test_project_use_cases.py` — `CreateProjectUseCase`

| Test | Escenario |
|------|-----------|
| `test_creates_project_with_correct_fields` | `organization_id`, `name` y `description` preservados |
| `test_delegates_persistence_to_repo` | Resultado es el objeto del repositorio; `create` llamado una vez |
| `test_default_description_is_empty` | `description` omitida → cadena vacía, no error |

---

### `test_create_release.py` — `CreateReleaseUseCase`

| Test | Escenario |
|------|-----------|
| `test_release_created_with_borrador_status` | Estado inicial siempre `BORRADOR` |
| `test_release_has_correct_project_and_profile` | `project_id` y `profile_id` sin modificación |
| `test_release_has_correct_version_and_creator` | `version` y `created_by` preservados |
| `test_delegates_persistence_to_release_repo` | `release_repo.create` llamado exactamente una vez |

---

### `test_launch_verification.py` — `LaunchVerificationUseCase`

| Test | Escenario |
|------|-----------|
| `test_release_not_found_raises_entity_not_found` | Release inexistente → `EntityNotFoundError` |
| `test_release_not_pendiente_raises_invalid_state` | BORRADOR / EN_VERIFICACION / COMPLETADA → `ReleaseInvalidStateError` |
| `test_happy_path_updates_status_to_en_verificacion` | Release PENDIENTE → estado actualizado a EN_VERIFICACION |
| `test_happy_path_enqueues_task_and_returns_task_id` | Task ID propagado; `enqueue_verification_task` invocado con `release.id` |
| `test_repo_update_called_before_enqueue` | `repo.update` precede a `enqueue_verification_task` (orden garantizado) |

**Invariante de consistencia:** la transición de estado se persiste *antes* de
encolar la tarea, eliminando la posibilidad de que un worker consuma un mensaje
cuya release aún figura como `PENDIENTE`.

---

### `test_configure_connector.py` — `ConfigureConnectorUseCase`

| Test | Escenario |
|------|-----------|
| `test_successful_connection_saved_as_activo` | Conexión exitosa → instancia persistida con `ACTIVO` |
| `test_connection_returns_false_raises_error` | `test_connection` retorna `False` → `ConnectorConnectionFailedError` |
| `test_connection_false_does_not_save` | Fallo con `False` → sin persistencia |
| `test_runtime_error_saved_as_inactivo` | `RuntimeError` en cliente → persistido como `INACTIVO` |
| `test_value_error_saved_as_inactivo` | `ValueError` en cliente → persistido como `INACTIVO` |
| `test_credentials_are_encrypted_and_stored` | `ICredentialEncryptor.encrypt` invocado; credenciales en claro no almacenadas |
| `test_unregistered_connector_type_raises_key_error` | Tipo no registrado → `KeyError` sin I/O |

---

### `test_manage_profile.py` — `ManageProfileUseCase`

| Test | Escenario |
|------|-----------|
| `test_create_profile_with_correct_org_and_name` | `organization_id` y `name` reflejados en el perfil |
| `test_create_profile_generates_unique_id` | Mismo comando ejecutado dos veces → IDs distintos |
| `test_delegates_persistence_to_repo` | `repo.create` invocado exactamente una vez |

---

### `test_get_verification_history.py` — `GetVerificationHistoryUseCase`

| Test | Escenario |
|------|-----------|
| `test_release_not_found_raises_entity_not_found` | Release inexistente → `EntityNotFoundError` |
| `test_returns_dict_with_release_id` | Resultado contiene `release_id` como cadena |
| `test_result_contains_expected_keys` | Claves de contrato: `verdict`, `duration_ms`, `rules_evaluated` |

---

### `test_entities.py` — dominio

#### `TestEnums`

| Test | Escenario |
|------|-----------|
| `test_release_status_string_values` | BORRADOR / PENDIENTE / EN_VERIFICACION / COMPLETADA son strings |
| `test_verdict_type_values` | VALID / VALID_WITH_WARNINGS / INVALID |
| `test_connector_status_values` | ACTIVO / INACTIVO / ERROR |
| `test_severity_type_values` | INFO / LOW / MEDIUM / HIGH / CRITICAL |
| `test_user_role_values` | VIEWER / OPERATOR / MANAGER / ADMIN |
| `test_release_status_enum_from_string` | `ReleaseStatus("BORRADOR") is ReleaseStatus.BORRADOR` |
| `test_verdict_type_is_string_subclass` | Todos los enums son subclases de `str` |

#### `TestUserEntity` / `TestOrganizationEntity` / `TestProjectEntity` / `TestReleaseEntity`

Verifican: campos almacenados correctamente, IDs auto-generados únicos, timestamps
auto-asignados, valores por defecto (`is_active=True`, `status=BORRADOR`,
`description=""`), y construcción con ID explícito.

#### `TestArtifactEntity` / `TestConnectorInstanceEntity` / `TestVerificationProfileEntity` / `TestVerificationResultEntity` / `TestVerificationRuleEntity`

Verifican: campos requeridos, defaults de colecciones (`metadata={}`,
`rules=[]`, `rule_results={}`, `profile_snapshot={}`), timestamps automáticos
y configuración explícita de reglas y configuración.

#### `TestDomainExceptions`

| Test | Escenario |
|------|-----------|
| `test_domain_exception_message_and_str` | `message` y `str()` coinciden |
| `test_entity_not_found_error_inherits` | Hereda de `DomainException` |
| `test_release_invalid_state_error_message_contains_state` | Mensaje incluye estado actual, esperado y `release_id` |
| `test_connector_connection_failed_error` | Mensaje propagado correctamente |
| `test_invalid_connector_configuration_error` | Mensaje propagado correctamente |
| `test_user_not_belongs_to_organization_error` | Hereda de `DomainException` |
| `test_verification_profile_not_active_error` | Hereda de `DomainException` |
| `test_all_exceptions_are_catchable_as_domain_exception` | Todas capturables como `DomainException` |

---

### `test_repositories.py` — adaptadores SQLAlchemy

Todos los repositorios usan sesiones mockeadas (`AsyncMock` / `MagicMock`);
no se require conexión real a PostgreSQL.

| Repositorio | Tests |
|-------------|-------|
| `SqlOrganizationRepository` | `create`, `get_by_id` (found/not found), `get_by_slug`, `list_all`, `update` (found/not found) |
| `SqlUserRepository` | `create`, `get_by_id`, `get_by_email`, `list_all`, `update` |
| `SqlProjectRepository` | `create`, `get_by_id`, `list_by_organization`, fallback de `description=None` |
| `SqlReleaseRepository` | `create`, `get_by_id`, `list_by_project`, `update` (found/not found) |
| `SqlConnectorRepository` | `save` (nuevo/existente), `get_by_id`, `list_by_organization` (active_only/all) |
| `SqlProfileRepository` | `create`, `get_by_id`, `get_default_for_organization` (found/not found) |
| `SqlArtifactRepository` | `save` (nuevo/existente), `find_by_id`, `find_by_release` |
| `SqlVerificationResultRepository` | `save` (nuevo/existente — skip add en update), `find_by_id`, `find_by_release` |

---

### `test_security.py` — infraestructura de seguridad

#### `TestJwtHandler`

| Test | Escenario |
|------|-----------|
| `test_create_access_token_returns_non_empty_string` | Token no vacío devuelto |
| `test_decode_returns_correct_sub_and_role` | `sub` y `role` round-trip correctamente |
| `test_decode_invalid_token_raises` | Token malformado → `InvalidTokenError` |
| `test_token_from_different_secret_rejected` | Token firmado con secreto A → rechazado por secreto B |
| `test_custom_algorithm_stored` | `sub` round-trip con algoritmo y expiración explícitos |
| `test_decoded_payload_has_iat_and_exp` | Payload contiene `iat` y `exp`; `exp > iat` |

#### `TestFernetCredentialEncryptor`

| Test | Escenario |
|------|-----------|
| `test_encrypt_returns_bytes` | Ciphertext ≠ plaintext, tipo `bytes` |
| `test_roundtrip_preserves_data` | `decrypt(encrypt(x)) == x` |
| `test_accepts_bytes_key` | Clave como `bytes` funciona igual |
| `test_different_keys_produce_different_ciphertext` | Dos claves distintas → ciphertexts distintos |

#### `TestMockTaskQueue`

| Test | Escenario |
|------|-----------|
| `test_enqueue_returns_uuid_string` | Task ID es string UUID válido |
| `test_enqueue_returns_unique_ids_each_call` | IDs únicos por llamada |
| `test_get_task_status_returns_pending` | Estado siempre `"PENDING"` |
| `test_get_task_status_any_id` | Acepta cualquier ID sin error |

#### `TestConnectorRegistry` / `TestLogging` / `TestSettings`

Verifican: registro y recuperación de conectores, idempotencia del logger,
caché de instancias, auto-generación de clave Fernet cuando está vacía, y
defaults de configuración JWT.

---

## 4. Convenciones de nomenclatura y estilo

### Archivos de test

- Un archivo por módulo bajo prueba: `test_<nombre_del_módulo>.py`.
- Prefijo `test_` obligatorio para que pytest los descubra automáticamente.

### Clases de test

- Una clase por unidad bajo prueba: `class Test<NombreDeLaUnidad>`.
- No heredan de `unittest.TestCase`; pytest gestiona el ciclo de vida.

### Métodos de test

Los nombres siguen el patrón:

```
test_<condición_o_escenario>_<resultado_esperado>
```

### Helpers y factories

Las funciones auxiliares para construir entidades o mocks de ORM usan el
prefijo `_make_` o `_<tipo>_model`:

```python
def _make_release(status: ReleaseStatus = ReleaseStatus.PENDIENTE) -> Release: ...
def _release_model(version="1.0.0", status="BORRADOR", **kwargs): ...
```

---

## 5. Ejecución de pruebas

### Requisitos previos

```bash
pip install pytest pytest-asyncio pytest-cov
```

### Ejecutar todas las pruebas unitarias

```bash
pytest tests/unit/ -v
```

### Ejecutar un paquete específico

```bash
# Sólo la capa API
pytest tests/unit/api/ -v

# Sólo casos de uso
pytest tests/unit/application/ -v

# Sólo infraestructura
pytest tests/unit/infrastructure/ -v
```

### Ejecutar un módulo específico

```bash
pytest tests/unit/application/use_cases/test_auth_use_cases.py -v
```

### Ejecutar con salida detallada de fallos

```bash
pytest tests/unit/ -v --tb=short
```

---

## 6. Configuración de pytest

`pytest.ini` (raíz del repositorio):

```ini
[pytest]
asyncio_mode = auto
testpaths = tests/unit
pythonpath = apps/api/src
```

`tests/unit/conftest.py` establece la variable `DATABASE_URL` con un valor
dummy **antes** de cualquier import, evitando que `session.py` falle por
variable no configurada. El engine SQLAlchemy se inicializa de forma lazy
(primera llamada real), por lo que nunca se intenta cargar el driver `psycopg`
durante las pruebas unitarias.

---

## 7. Dobles de prueba y estrategia de aislamiento

| Tipo | Uso habitual |
|------|-------------|
| `AsyncMock` | Repositorios async, cola de tareas, casos de uso |
| `MagicMock` | Servicios síncronos (JWT, encriptador), modelos ORM |

```python
# Repositorio que refleja el argumento recibido:
repo.create.side_effect = lambda entity: entity

# Servicio que simula un fallo:
connector_client.test_connection.side_effect = RuntimeError("timeout")

# Modelo ORM sintético:
model = MagicMock()
model.id = uuid.uuid4()
model.name = "Acme"
```

Las entidades de dominio y los comandos de aplicación **nunca** se mockean;
se instancian con sus constructores reales para detectar regresiones.

---

## 8. Cobertura de código

### Ver cobertura en terminal (fuente completa)

```bash
pytest tests/unit/ --cov=apps/api/src --cov-report=term-missing
```

### Ver cobertura por capa

```bash
# Sólo capa de aplicación
pytest tests/unit/ --cov=apps/api/src/application --cov-report=term-missing

# Sólo capa de dominio
pytest tests/unit/ --cov=apps/api/src/domain --cov-report=term-missing

# Sólo infraestructura
pytest tests/unit/ --cov=apps/api/src/infrastructure --cov-report=term-missing
```

### Generar informe HTML

```bash
pytest tests/unit/ \
  --cov=apps/api/src \
  --cov-report=html:htmlcov/unit \
  --cov-report=term-missing
```

El informe se genera en `htmlcov/unit/index.html`.

### Forzar umbral mínimo (falla el build si no se alcanza)

```bash
pytest tests/unit/ --cov=apps/api/src --cov-fail-under=80
```

El objetivo de cobertura para las capas de aplicación e infraestructura es
**≥ 80 %** de sentencias. Los flujos de error y ramas condicionales se prueban
explícitamente para evitar cobertura sólo de caminos felices.

---

## 9. Niveles pendientes de implementación

| Directorio | Propósito | Estado |
|------------|-----------|--------|
| `integration/` | Repositorios contra PostgreSQL real en Docker | Pendiente |
| `e2e/` | Flujos completos via HTTP contra instancia local de la API | Pendiente |
| `performance/` | Benchmarks de endpoints críticos (Locust / k6) | Pendiente |
| `security/` | SAST con Bandit y pruebas de autenticación automatizadas | Pendiente |

Las pruebas de integración requerirán un `conftest.py` propio con fixtures de
sesión que gestionen el ciclo de vida de la base de datos de pruebas (creación
de tablas, datos de seed y limpieza entre tests).

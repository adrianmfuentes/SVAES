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
3. [Nivel unitario — cobertura actual](#3-nivel-unitario--cobertura-actual)
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
  etc.) se prueban en pruebas de integración donde se ejercita la interacción
  real con los sistemas externos.
- **Los flujos de extremo a extremo** se validan en pruebas E2E que levantan
  la aplicación completa contra entornos efímeros.

Este diseño maximiza la velocidad del ciclo de retroalimentación durante el
desarrollo: las pruebas unitarias se ejecutan en milisegundos sin requerir
ninguna dependencia de infraestructura.

---

## 2. Estructura de directorios

```
tests/
├── README.md                  ← este documento
│
├── unit/                      ← pruebas de aislamiento total (sin I/O real)
│   ├── conftest.py            ← configuración de sys.path para imports
│   └── application/
│       └── use_cases/
│           ├── test_auth_use_cases.py
│           ├── test_organization_use_cases.py
│           ├── test_project_use_cases.py
│           ├── test_create_release.py
│           ├── test_launch_verification.py
│           ├── test_configure_connector.py
│           ├── test_manage_profile.py
│           └── test_get_verification_history.py
│
├── integration/               ← pruebas con base de datos y servicios reales
│   └── .gitkeep
│
├── e2e/                       ← pruebas de extremo a extremo (aplicación completa)
│   └── .gitkeep
│
├── performance/               ← benchmarks y pruebas de carga
│   └── .gitkeep
│
└── security/                  ← pruebas de seguridad automatizadas (SAST/DAST)
    └── .gitkeep
```

---

## 3. Nivel unitario — cobertura actual

Todos los casos de uso de la capa de aplicación disponen de suite unitaria
completa. La tabla siguiente resume el módulo bajo prueba, la clase de test
correspondiente y los escenarios cubiertos.

### `test_auth_use_cases.py` — `LoginUseCase`

| Test | Escenario |
|------|-----------|
| `test_valid_credentials_return_token` | Credenciales correctas → JWT emitido con `user_id` y `role` correctos |
| `test_user_not_found_raises_value_error` | Email inexistente → `ValueError` con mensaje genérico |
| `test_wrong_password_raises_value_error` | Contraseña errónea → `ValueError` con mensaje genérico |
| `test_token_not_issued_when_user_not_found` | Fallo de auth → `ITokenService` no invocado |

**Invariante de seguridad:** el mensaje de error es idéntico para email inexistente
y contraseña incorrecta, impidiendo la enumeración de usuarios registrados.

---

### `test_organization_use_cases.py` — `CreateOrganizationUseCase` / `ListOrganizationsUseCase`

| Test | Escenario |
|------|-----------|
| `test_creates_and_returns_organization` | El resultado es la instancia devuelta por el repositorio |
| `test_passes_correct_slug_to_repo` | `name` y `slug` del comando se transfieren fielmente |
| `test_default_plan_is_free` | Plan por defecto es `"free"` sin especificarlo |
| `test_returns_active_organizations` | Listado filtra con `active_only=True` |
| `test_returns_empty_list_when_no_orgs` | Sin organizaciones activas → lista vacía, sin excepción |

---

### `test_project_use_cases.py` — `CreateProjectUseCase`

| Test | Escenario |
|------|-----------|
| `test_creates_project_with_correct_fields` | `organization_id`, `name` y `description` se preservan |
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
| `test_release_not_pendiente_raises_invalid_state` | Estados BORRADOR / EN_VERIFICACION / COMPLETADA → `ReleaseInvalidStateError` |
| `test_happy_path_updates_status_to_en_verificacion` | Release PENDIENTE → estado actualizado a EN_VERIFICACION |
| `test_happy_path_enqueues_task_and_returns_task_id` | Task ID propagado; `enqueue_verification_task` invocado con `release.id` |
| `test_repo_update_called_before_enqueue` | `repo.update` precede a `enqueue_verification_task` (orden garantizado) |

**Invariante de consistencia:** la transición de estado se persiste *antes* de
encolar la tarea, eliminando la posibilidad de que un worker consuma un mensaje
cuya release aún figura como `PENDIENTE` en la base de datos.

---

### `test_configure_connector.py` — `ConfigureConnectorUseCase`

| Test | Escenario |
|------|-----------|
| `test_successful_connection_saved_as_activo` | Conexión exitosa → instancia con `ACTIVO` persistida |
| `test_connection_returns_false_raises_error` | `test_connection` retorna `False` → `ConnectorConnectionFailedError` |
| `test_connection_false_does_not_save` | Fallo con `False` → sin persistencia |
| `test_runtime_error_saved_as_inactivo` | `RuntimeError` en cliente → instancia persistida con `INACTIVO` |
| `test_value_error_saved_as_inactivo` | `ValueError` en cliente → instancia persistida con `INACTIVO` |
| `test_credentials_are_encrypted_and_stored` | `ICredentialEncryptor.encrypt` invocado; credenciales en claro no almacenadas |
| `test_unregistered_connector_type_raises_key_error` | Tipo no registrado → `KeyError` sin I/O |

**Política de tolerancia a fallos:** los errores de infraestructura transitorios
(`RuntimeError`, `ValueError`) persisten el conector como `INACTIVO` para
permitir la corrección posterior de credenciales sin recrear el recurso.

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

## 4. Convenciones de nomenclatura y estilo

### Archivos de test

- Un archivo por caso de uso: `test_<nombre_del_caso_de_uso>.py`.
- Prefijo `test_` obligatorio para que pytest los descubra automáticamente.

### Clases de test

- Una clase por caso de uso bajo prueba: `class Test<NombreDelCasoDeUso>`.
- No heredan de `unittest.TestCase`; pytest gestiona el ciclo de vida.

### Métodos de test

Los nombres de los métodos siguen el patrón:

```
test_<condición_o_escenario>_<resultado_esperado>
```

Ejemplos:
- `test_valid_credentials_return_token`
- `test_release_not_found_raises_entity_not_found`
- `test_credentials_are_encrypted_and_stored`

### Docstrings de métodos

Cada método de test incluye una docstring con estructura **Given / When / Then**:

```python
async def test_example(self):
    """
    Descripción breve del escenario.

    Given:  Precondiciones del sistema bajo prueba.
    When:   Acción ejecutada.
    Then:   Resultado esperado y su justificación de negocio.
    """
```

### Helpers y factories

Las funciones auxiliares para construir entidades de prueba siguen la convención
de nombre privado con prefijo `_make_`:

```python
def _make_release(status: ReleaseStatus = ReleaseStatus.PENDIENTE) -> Release:
    ...
```

---

## 5. Ejecución de pruebas

### Requisitos previos

```bash
pip install pytest pytest-asyncio pytest-cov
```

### Ejecutar únicamente las pruebas unitarias

```bash
pytest tests/unit/ -v
```

### Ejecutar un módulo específico

```bash
pytest tests/unit/application/use_cases/test_auth_use_cases.py -v
```

### Ejecutar con informe de cobertura

```bash
pytest tests/unit/ --cov=apps/api/src/application --cov-report=term-missing
```

### Ejecutar con salida detallada de fallos

```bash
pytest tests/unit/ -v --tb=short
```

---

## 6. Configuración de pytest

El archivo `tests/unit/conftest.py` inserta `apps/api/src` en `sys.path` al
inicio de la sesión de pruebas. Esto permite importar módulos de la aplicación
por su nombre canónico (`from application.use_cases.auth_use_cases import ...`)
sin necesidad de instalación del paquete ni rutas relativas.

La configuración de pytest-asyncio se aplica globalmente mediante el marcador
`asyncio_mode = "auto"` (definido en `pyproject.toml` o `pytest.ini`), que
permite decorar los tests asíncronos sin `@pytest.mark.asyncio` explícito.

---

## 7. Dobles de prueba y estrategia de aislamiento

Las pruebas unitarias de la capa de aplicación utilizan exclusivamente dobles
de la librería estándar `unittest.mock`:

| Tipo | Uso habitual |
|------|-------------|
| `AsyncMock` | Puertos asíncronos: repositorios, cola de tareas |
| `MagicMock` | Servicios síncronos: hasher de contraseñas, servicio JWT, encriptador |

Los dobles se configuran mediante `return_value` y `side_effect`:

```python
# Repositorio que retorna un objeto fijo:
repo.get_by_email.return_value = sample_user

# Repositorio que refleja el argumento recibido (persistencia transparente):
repo.create.side_effect = lambda entity: entity

# Servicio que simula un fallo:
connector_client.test_connection.side_effect = RuntimeError("timeout")
```

**Nunca** se usan mocks para las entidades de dominio (`User`, `Release`,
`Organization`, etc.) ni para los comandos de aplicación. Estas clases se
instancian con sus constructores reales para detectar regresiones en el
comportamiento del dominio.

---

## 8. Cobertura de código

El objetivo de cobertura para la capa de aplicación (`application/use_cases/`)
es **≥ 90 %** de sentencias. Los casos límite y los flujos de error de dominio
(excepciones, estados inválidos) se prueban explícitamente para asegurar que las
ramas condicionales no queden sin ejercitar.

Para generar un informe HTML:

```bash
pytest tests/unit/ \
  --cov=apps/api/src/application \
  --cov-report=html:htmlcov/unit
```

El informe se genera en `htmlcov/unit/index.html`.

---

## 9. Niveles pendientes de implementación

| Directorio | Propósito | Estado |
|------------|-----------|--------|
| `integration/` | Pruebas de repositorios contra base de datos real (PostgreSQL en Docker) | Pendiente |
| `e2e/` | Flujos completos via HTTP contra instancia local de la API | Pendiente |
| `performance/` | Benchmarks de endpoints críticos (Locust / k6) | Pendiente |
| `security/` | Análisis estático de seguridad (Bandit) y pruebas de autenticación | Pendiente |

Las pruebas de integración requerirán un `conftest.py` propio con fixtures de
sesión que gestionen el ciclo de vida de la base de datos de pruebas (creación
de tablas, datos de seed y limpieza entre tests).

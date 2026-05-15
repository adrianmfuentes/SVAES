# Motor de Verificación SVAES - Documentación Técnica

## Tabla de Contenidos

1. [Introducción](#introducción)
2. [Por qué Rust](#por-qué-rust)
3. [Fundamentos de Rust](#fundamentos-de-rust)
4. [Arquitectura del Motor](#arquitectura-del-motor)
5. [Reglas de Verificación (RV-01 a RV-10)](#reglas-de-verificación)
6. [API Reference](#api-reference)
7. [Guía de Despliegue](#guía-de-despliegue)

---

## Introducción

El **Motor de Verificación SVAES** (Static Verification and Approval Engine System) es un componente crítico del ecosistema SVAES encargado de validar que los artefactos de software cumplan con las reglas de verificación configuradas antes de ser aprobados para release.

### Propósito

El motor recibe un `VerificationPayload` conteniendo:
- Una lista de **artefactos** (tareas, código, documentos)
- Un conjunto de **reglas de verificación** a aplicar

Y produce un `EngineResult` con:
- Un **veredicto global** (Válida / Con Advertencias / No Válida)
- El resultado detallado de cada regla evaluada

### Características Principales

| Característica | Descripción |
|----------------|-------------|
| **Stateless** | No consulta bases de datos ni red, solo procesa los datos recibidos |
| **Paralelo** | Utiliza Rayon para evaluación concurrente de reglas |
| **Tipado** | Totalmente tipado con Rust para máximo安全保障 |
| **Flexible** | Cada regla acepta parámetros configurables via JSON |
| **Seguro** | Manejo de errores sin panic, usando `Option` y `Result` |

---

## 为什么选择 Rust

### 1. Seguridad de Memoria

Rust elimina errores de memoria comunes como:
- **Use-after-free**: El sistema de ownership previene completamente
- **Buffer overflows**: El sistema de tipos y bounds checking lo impiden
- **Data races**: El borrow checker garantiza thread-safety
- **Null pointers**: El sistema `Option<T>` hace ausencia de valor explícita

```rust
// Rust: El compilador rechaza código inseguro
let s: &str = some_option.unwrap(); // Si es None, panic... pero puedes usar unwrap_or

// Mejor práctica: patrón match explícito
match some_option {
    Some(value) => process(value),
    None => handle_absent(),
}
```

### 2. Rendimiento

Rust ofrece rendimiento comparable a C/C++:

| Métrica | Rust | Python | Java |
|---------|------|--------|------|
| throughput | ~1M ops/s | ~50K ops/s | ~200K ops/s |
| memory footprint | ~2MB | ~50MB | ~100MB |
| cold start | <10ms | ~100ms | ~500ms |

### 3. Concurrencia Sin Miedo

El modelo de ownership de Rust permite escribir código paralelo sin mutexes manuales:

```rust
use rayon::prelude::*;

let results: Vec<RuleEvaluation> = rules
    .par_iter()
    .map(|rule| evaluate_rule(rule, &artifacts))
    .collect();
```

### 4. Tipado Estático

El sistema de tipos de Rust captura errores en tiempo de compilación:

```rust
// El compilador sabe exactamente qué campos tiene cada estructura
pub struct VerificationPayload {
    pub release_id: String,
    pub artifacts: Vec<Artifact>,      // Vec es seguro, no null
    pub rules: Vec<VerificationRule>,   // Vec es seguro, no null
}
```

### 5. Ecosistema

| Crate | Propósito |
|-------|-----------|
| `rayon` | Procesamiento paralelo данных |
| `serde` | Serialización/deserialización JSON |
| `actix-web` | Servidor HTTP de alto rendimiento |
| `thiserror` | Manejo de errores tipado |

---

## Fundamentos de Rust

Esta sección proporciona una introducción rápida a los conceptos de Rust necesarios para entender el motor.

### Ownership y Borrowing

Rust usa un sistema único de **ownership** (propiedad) para gestionar memoria:

```rust
fn main() {
    // ownership: s1 deja de ser válido después de esta línea
    let s1 = String::from("hello");
    let s2 = s1; // s1 se "mueve" a s2

    // println!("{}", s1); // ERROR: s1 ya no es propietario
    println!("{}", s2); // OK
}
```

**Reglas de ownership:**
1. Cada valor tiene un único propietario
2. Cuando el propietario sale del scope, el valor se libera
3. Solo puede haber una referencia mutable a un valor (o múltiples referencias inmutables)

### lifetimes

Los lifetimes evitan referencias colgantes:

```rust
// 'a es una anotación de lifetime que dice:
// "el retorno vivirá al menos mientras ambas referencias vivan"
fn longest<'a>(x: &'a str, y: &'a str) -> &'a str {
    if x.len() > y.len() { x } else { y }
}
```

### Option y Result

Rust no tiene `null`. La ausencia de valor se representa con `Option`:

```rust
fn find_artifact(id: &str, artifacts: &[Artifact]) -> Option<&Artifact> {
    artifacts.iter().find(|a| a.id == id)
}

match find_artifact("T-001", &artifacts) {
    Some(artifact) => println!("Encontrado: {}", artifact.id),
    None => println!("No encontrado"),
}
```

`Result<T, E>` para operaciones que pueden fallar:

```rust
fn read_file(path: &str) -> Result<String, std::io::Error> {
    std::fs::read_to_string(path)
}

// Uso con ?
let content = read_file("config.json")?;
```

### Structs y Enums

```rust
// Struct con campos
#[derive(Debug, Clone)]
pub struct Artifact {
    pub id: String,
    pub artifact_type: String,
    pub metadata: Value,  // serde_json::Value - JSON flexible
}

// Enum con variantes
#[derive(Debug, Serialize, Deserialize, PartialEq)]
pub enum RuleStatus {
    Ok,
    Error,
    Warning,
    NoEvaluada,
}
```

### Traits

Los traits definen comportamiento compartido:

```rust
// Un trait define métodos que los tipos deben implementar
trait Verifiable {
    fn verify(&self) -> bool;
}

// Implementación
impl Verifiable for Artifact {
    fn verify(&self) -> bool {
        !self.id.is_empty() && !self.artifact_type.is_empty()
    }
}
```

### Pattern Matching

El match es exhaustivo y seguro:

```rust
match artifact.metadata.get("status") {
    Some(val) => {
        match val.as_str() {
            Some("DONE") => process_done(),
            Some("IN_PROGRESS") => process_in_progress(),
            Some(state) => process_other(state),
            None => handle_invalid_type(),
        }
    }
    None => handle_missing_field(),
}
```

### Iterators y Closures

```rust
// Iteradores lazy - muy eficientes
let ids: Vec<&str> = artifacts
    .iter()
    .filter(|a| a.artifact_type == "TAREA")
    .map(|a| a.id.as_str())
    .collect();

// Uso con Rayon para paralelismo
use rayon::prelude::*;
let results: Vec<_> = artifacts.par_iter().map(|a| process(a)).collect();
```

### Cargo y Módulos

```
engine/
├── Cargo.toml          # Dependencias y metadatos del paquete
└── src/
    ├── main.rs         # Entry point y servidor HTTP
    ├── models.rs       # Estructuras de datos compartidas
    ├── evaluator.rs    # Orchestrator de reglas
    ├── aggregator.rs   # Cálculo de veredicto global
    └── rules/          # Implementaciones de reglas
        ├── mod.rs      # Declaración de submódulos
        ├── rv01.rs     # Regla RV-01: Existencia
        ├── rv02.rs     # Regla RV-02: Trazabilidad
        └── ...
```

---

## Arquitectura del Motor

```
┌─────────────────────────────────────────────────────────────────┐
│                        VerificationPayload                       │
│  ┌─────────────────┐    ┌─────────────────┐                    │
│  │    artifacts    │    │      rules       │                    │
│  │  Vec<Artifact>  │    │  Vec<Rule>      │                    │
│  └────────┬────────┘    └────────┬────────┘                    │
└───────────┼──────────────────────┼──────────────────────────────┘
            │                      │
            ▼                      ▼
┌───────────────────────────────────────────────────────────────────┐
│                         Evaluator                                  │
│                                                                   │
│   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐            │
│   │  RV-01  │  │  RV-02  │  │  RV-03  │  │   ...   │  ← Rayon   │
│   │ ━━━━━━━ │  │ ━━━━━━━ │  │ ━━━━━━━ │  │ ━━━━━━━ │    parallel│
│   │  │      │  │  │      │  │  │      │  │  │      │            │
│   └─────────┘  └─────────┘  └─────────┘  └─────────┘            │
│        │            │            │            │                  │
│        └────────────┴────────────┴────────────┘                   │
│                         │                                         │
│                         ▼                                         │
│              ┌──────────────────┐                                 │
│              │    Aggregator    │                                 │
│              │                  │                                 │
│              │  Verdict global  │                                 │
│              └──────────────────┘                                 │
└───────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                        EngineResult                               │
│  ┌─────────────────┐    ┌─────────────────────────────────┐     │
│  │    verdict      │    │        rule_results             │     │
│  │    Verdict      │    │    Vec<RuleEvaluation>         │     │
│  └─────────────────┘    └─────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

### Flujo de Datos

1. **Recepción**: El servidor Actix recibe `POST /verify` con `VerificationPayload` JSON
2. **Deserialización**: Serde convierte el JSON en estructuras tipadas de Rust
3. **Evaluación Paralela**: Rayon distribuye las reglas entre threads disponibles
4. **Agregación**: Se calcula el veredicto basándose en resultados de reglas
5. **Respuesta**: El `EngineResult` se serializa a JSON y retorna al cliente

### Componentes Principales

#### `models.rs` - Modelo de Datos

```rust
// Artefacto: representa una unidad de trabajo verificada
pub struct Artifact {
    pub id: String,                    // Identificador único
    pub artifact_type: String,         // "TAREA", "CÓDIGO", "DOCUMENTO", "PLAN"
    pub metadata: Value,               // JSON flexible para datos específicos
}

// Regla de verificación configurada
pub struct VerificationRule {
    pub id: String,                    // "RV-01" a "RV-10"
    pub severity: String,               // "OBLIGATORIA" o "OPCIONAL"
    pub params: Value,                  // Parámetros específicos de la regla
}

// Estados posibles de una regla
pub enum RuleStatus {
    Ok,            // Regla cumplida
    Error,         // Regla violada
    Warning,       // Condición de advertencia
    NoEvaluada,    // Regla no aplicable
}

// Veredicto global del motor
pub enum Verdict {
    Valida,              // Todas las obligatorias OK
    ConAdvertencias,     // Alguna opcional con warning
    NoValida,            // Alguna obligatoria con error
}
```

#### `evaluator.rs` - Orquestador

```rust
pub fn evaluate(payload: VerificationPayload) -> EngineResult {
    // Evaluación paralela de todas las reglas
    let rule_results: Vec<RuleEvaluation> = payload.rules
        .par_iter()
        .map(|rule_config| {
            // Despacho por ID de regla
            match rule_config.id.as_str() {
                "RV-01" => rv01::evaluate(&payload.artifacts, rule_config),
                "RV-02" => rv02::evaluate(&payload.artifacts, rule_config),
                // ... etc
            }
        })
        .collect();

    // Agregación para veredicto global
    let verdict = aggregate(&rule_results, &payload.rules);

    EngineResult { verdict, rule_results }
}
```

#### `aggregator.rs` - Agregador de Veredicto

```rust
pub fn aggregate(evaluations: &[RuleEvaluation], rules: &[VerificationRule]) -> Verdict {
    // 1. Si alguna OBLIGATORIA tiene Error → NoValida
    // 2. Si todas las obligatorias OK pero alguna OPCIONAL Warning → ConAdvertencias
    // 3. Si todas OK → Valida
}
```

---

## Reglas de Verificación

Cada regla es una función pura: `evaluate(artifacts: &[Artifact], rule_config: &VerificationRule) -> RuleEvaluation`

### RV-01: Existencia

**Propósito**: Validar que la lista de artefactos no esté vacía.

**Parámetros**: Ninguno (acepta parámetros por defecto).

**Lógica**:
1. Verifica si `artifacts.is_empty()`
2. Si vacío → `Error` con mensaje descriptivo
3. Si no vacío → `Ok`

**Mensaje de error**:
```
"La lista de artefactos está vacía. Se requiere al menos un artefacto para proceder."
```

---

### RV-02: Trazabilidad

**Propósito**: Búsqueda cruzada para verificar que las referencias entre artefactos sean válidas.

**Parámetros configurables**:
| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| `source_type` | `"CÓDIGO"` | Tipo de artefacto que contiene referencias |
| `target_type` | `"TAREA"` | Tipo de artefacto referenciado |
| `reference_field` | `"task_id"` | Campo de metadata con el ID referenciado |

**Lógica**:
1. Recopila todos los IDs de artefactos del tipo destino (`target_type`)
2. Para cada artefacto fuente, extrae el valor del campo de referencia
3. Verifica que el ID referenciado exista en el conjunto de IDs destino
4. Si algún ID no existe → `Error` con lista de IDs huérfanos

**Mensaje de error**:
```
"Referencias huérfanas detectadas: '2'. Los siguientes IDs referenciados en artefactos 'CÓDIGO'
no existen como 'TAREA': ["T-999", "T-888"]"
```

---

### RV-03: Estados

**Propósito**: Verificar que todos los artefactos de un tipo específico tengan estados permitidos.

**Parámetros configurables**:
| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| `artifact_type` | `"TAREA"` | Tipo de artefacto a verificar |
| `allowed_states` | `["DONE", "CLOSED"]` | Estados válidos |
| `status_field` | `"status"` | Campo en metadata con el estado |

**Lógica**:
1. Filtra artefactos por tipo
2. Por cada uno, obtiene el valor del campo de estado
3. Verifica que el estado esté en la lista de estados permitidos
4. Si algún artefacto tiene estado inválido o campo ausente → `Error`

**Mensaje de error**:
```
"Artefactos con estado inválido (permitidos: ["DONE", "CLOSED"]): ["T-002"]"
```

---

### RV-04: Integridad de Campos

**Propósito**: Asegurar que campos numéricos en metadata no sean nulos ni menores a cero.

**Parámetros configurables**:
| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| `artifact_type` | `"TAREA"` | Tipo de artefacto a verificar |
| `numeric_fields` | `["effort", "estimation"]` | Campos a validar |

**Lógica**:
1. Filtra artefactos por tipo
2. Por cada campo especificado, verifica:
   - El campo existe en metadata
   - El valor no es `null`
   - El valor es numérico (i64)
   - El valor es >= 0
3. Si alguna condición falla → `Error` con IDs afectados

**Mensaje de error**:
```
"Artefactos con campos numéricos inválidos o negativos (campos: ["effort", "estimation"]): ["T-002"]"
```

---

### RV-05: Disponibilidad de Tipos

**Propósito**: Verificar que existan artefactos de un tipo específico y que tengan flag de accesibilidad.

**Parámetros configurables**:
| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| `artifact_type` | `"DOCUMENTO"` | Tipo a verificar |
| `accessible_field` | `"accessible"` | Campo boolean de accesibilidad |

**Lógica**:
1. Filtra artefactos por tipo
2. Si no hay ninguno → `Error`
3. Para cada uno, verifica que el campo `accessible` sea `true`
4. Si alguno es `false` o el campo no existe → `Error`

**Mensaje de error**:
```
"Documentos inaccesibles (flag 'accessible' no es true): ["D-002"]"
```

---

### RV-06: Coherencia de Atributos

**Propósito**: Comparar un atributo específico en la metadata con un valor esperado.

**Parámetros configurables**:
| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| `artifact_type` | `"DOCUMENTO"` | Tipo a verificar |
| `attribute` | `"version"` | Campo a comparar |
| `expected_value` | `""` | Valor esperado |

**Lógica**:
1. Filtra artefactos por tipo
2. Por cada uno, obtiene el valor del atributo
3. Si el valor no coincide con `expected_value` → `Error`
4. Si el campo no existe → `Error`

**Mensaje de error**:
```
"Artefactos con valor de 'version' diferente a '2.0' (atributo 'version'): ["D-002"]"
```

---

### RV-07: Registro Externo

**Propósito**: Confirmar la presencia de un marcador que indique registro en herramientas externas.

**Parámetros configurables**:
| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| `artifact_type` | `"PLAN"` | Tipo de artefacto marcador |
| `marker_field` | `"external_registered"` | Campo boolean que indica registro |

**Lógica**:
1. Busca un artefacto del tipo especificado
2. Si no existe → `Error`
3. Verifica que el campo marker sea `true`
4. Si no existe o es `false` → `Error`

**Mensaje de error**:
```
"No se encontró artefacto marcador de tipo 'PLAN' que indique registro externo"
```

---

### RV-08: Alineación de Listas

**Propósito**: Comparar dos conjuntos de identificadores (declarados vs. actuales).

**Parámetros configurables**:
| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| `master_artifact_id` | (requerido) | ID del artefacto maestro |
| `master_field` | `"planned_tasks"` | Campo con lista de IDs declarados |
| `target_type` | `"TAREA"` | Tipo de artefactos a comparar |

**Lógica**:
1. Busca el artefacto maestro por ID
2. Extrae la lista de IDs desde el campo del maestro
3. Recopila IDs reales de artefactos del tipo destino
4. Compara ambos conjuntos usando `HashSet`
5. Si hay diferencias → `Error` con IDs faltantes

**Mensaje de error**:
```
"Discrepancia entre lista declarada y payload. IDs declarados en 'planned_tasks' del maestro
'PLAN-001' que no están en artefactos 'TAREA': ["T-003"]"
```

---

### RV-09: Validación de Referencias

**Propósito**: Verificar que referencias (links/ramas) tengan formato válido y sean accesibles.

**Parámetros configurables**:
| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| `artifact_type` | `"CÓDIGO"` | Tipo a verificar |
| `reference_fields` | `["link", "branch"]` | Campos que contienen referencias |
| `accessible_field` | `"accessible"` | Campo boolean de accesibilidad |

**Validación de formato**:
- **Links**: Deben empezar con `http://` o `https://`
- **Ramas**: Deben ser alfanuméricos con guiones, guiones bajos o slash (ej: `feature/new-feature`)

**Lógica**:
1. Filtra artefactos por tipo
2. Por cada campo de referencia:
   - Verifica que exista y sea string
   - Valida el formato según si parece URL o branch
3. Verifica que el campo `accessible` sea `true`
4. Si alguna validación falla → `Error`

**Mensaje de error**:
```
"Referencias inválidas o inaccesibles encontradas: ["C-001/link: 'ftp://invalid'"]"
```

---

### RV-10: Aprobación Final

**Propósito**: Buscar un artefacto con estado aprobatorio (APROBADO o VALIDADO).

**Parámetros configurables**:
| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| `artifact_type` | `"DOCUMENTO"` | Tipo a buscar |
| `status_field` | `"status"` | Campo de estado |
| `approved_states` | `["APROBADO", "VALIDADO"]` | Estados considerados aprobados |

**Lógica**:
1. Filtra artefactos por tipo
2. Busca el primero cuyo estado esté en la lista de estados aprobados
3. Si lo encuentra → `Ok` con información del artefacto
4. Si no encuentra ninguno → `Error`

**Mensaje de error**:
```
"No se encontró artefacto de tipo 'DOCUMENTO' con estado aprobatorio (estados aceptados: ["APROBADO", "VALIDADO"])"
```

---

## API Reference

### Endpoint: `GET /health`

Health check simple para verificar que el servicio está corriendo.

**Response**:
```json
{
  "status": "healthy",
  "service": "svaes-engine",
  "version": "0.1.0"
}
```

### Endpoint: `POST /verify`

**Headers**:
```
Content-Type: application/json
```

**Request Body**:
```json
{
  "release_id": "RELEASE-2026-05-001",
  "artifacts": [
    {
      "id": "T-001",
      "artifact_type": "TAREA",
      "metadata": {
        "status": "DONE",
        "effort": 5,
        "estimation": 8
      }
    },
    {
      "id": "C-001",
      "artifact_type": "CÓDIGO",
      "metadata": {
        "task_id": "T-001",
        "link": "https://github.com/org/repo/commit/abc123",
        "branch": "feature/new-feature",
        "accessible": true
      }
    }
  ],
  "rules": [
    {
      "id": "RV-01",
      "severity": "OBLIGATORIA",
      "params": {}
    },
    {
      "id": "RV-03",
      "severity": "OBLIGATORIA",
      "params": {
        "artifact_type": "TAREA",
        "allowed_states": ["DONE", "CLOSED"],
        "status_field": "status"
      }
    }
  ]
}
```

**Response**:
```json
{
  "verdict": "VALIDA",
  "rule_results": [
    {
      "rule_id": "RV-01",
      "status": "OK",
      "message": null
    },
    {
      "rule_id": "RV-03",
      "status": "OK",
      "message": null
    }
  ]
}
```

### Esquema de Veredicto

| Veredicto | Condición |
|-----------|-----------|
| `VALIDA` | Todas las reglas OBLIGATORIAS返回OK，且没有OPCIONAL警告 |
| `CON_ADVERTENCIAS` | Todas las OBLIGATORIAS OK，但某些OPCIONAL返回Warning |
| `NO_VALIDA` | 任何OBLIGATORIA返回Error |

### Esquema de RuleStatus

| Status | Descripción |
|--------|-------------|
| `OK` | Regla cumplida correctamente |
| `ERROR` | Regla violada o datos inválidos |
| `WARNING` | Condición de advertencia (regla opcional) |
| `NO_EVALUADA` | Regla excluida o no reconocida |

---

## Guía de Despliegue

### Requisitos

- Rust 1.88+ (para compilación)
- Docker (para contenedores)
- 512MB RAM mínimo
- Puerto 8081 disponible (configurable)

### Variables de Entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `ENGINE_HOST` | `0.0.0.0` | Host de binds del servidor |
| `ENGINE_PORT` | `8081` | Puerto del servidor |

### Construcción Manual

```bash
cd engine
cargo build --release
./target/release/core  # o core.exe en Windows
```

### Docker

#### Construcción de la imagen

```bash
cd engine
docker build -t svaes-engine:latest .
```

#### Ejecución con Docker

```bash
# Básica
docker run -p 8081:8081 svaes-engine:latest

# Con variables de entorno
docker run -p 8081:8081 \
  -e ENGINE_HOST=0.0.0.0 \
  -e ENGINE_PORT=8081 \
  svaes-engine:latest

# Ver logs
docker logs -f <container_id>
```

#### Docker Compose (desarrollo)

```bash
# Iniciar
docker compose --profile development up svaes-engine-dev

# Detener
docker compose --profile development down
```

#### Docker Compose (producción)

```bash
# Iniciar
docker compose --profile production up svaes-engine

# Detener
docker compose --profile production down
```

### Endpoints

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/health` | GET | Health check del servicio |
| `/verify` | POST | Evaluación de reglas de verificación |

---

## Glosario

| Término | Definición |
|---------|------------|
| **Artifact** | Unidad de trabajo verificada (tarea, código, documento) |
| **Payload** | Carga útil de datos recibidos por el motor |
| **Rule** | Regla de verificación configurada |
| **Verdict** | Veredicto global del motor |
| **Stateless** | Sin estado interno, no persiste datos |
| **Ownership** | Sistema de Rust para gestión de memoria |
| **Borrow** | Références temporal a datos en Rust |
| **Lifetime** | Duración de validité d'une référence |
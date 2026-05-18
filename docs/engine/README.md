# SVAES Verification Engine - Technical Documentation

## Table of Contents

1. [Introduction](#introduction)
2. [Why Rust](#why-rust)
3. [Rust Fundamentals](#rust-fundamentals)
4. [Engine Architecture](#engine-architecture)
5. [Verification Rules (RV-01 to RV-10)](#verification-rules-rv-01-to-rv-10)
6. [API Reference](#api-reference)
7. [Deployment Guide](#deployment-guide)

---

## Introduction

The **SVAES Verification Engine** (Static Verification and Approval Engine System) is a critical component of the SVAES ecosystem responsible for validating that software artifacts comply with the configured verification rules before being approved for release.

### Purpose

The engine receives a `VerificationPayload` containing:
- A list of **artifacts** (tasks, code, documents)
- A set of **verification rules** to apply

And produces an `EngineResult` with:
- A **global verdict** (Valid / With Warnings / Not Valid)
- The detailed result of each evaluated rule

### Key Features

| Feature | Description |
|---------|-------------|
| **Stateless** | Does not query databases or network, only processes received data |
| **Parallel** | Uses Rayon for concurrent rule evaluation |
| **Typed** | Fully typed with Rust for maximum safety |
| **Flexible** | Each rule accepts configurable parameters via JSON |
| **Safe** | Error handling without panic, using `Option` and `Result` |

---

## Why Rust

### 1. Memory Safety

Rust eliminates common memory errors such as:
- **Use-after-free**: The ownership system prevents it completely
- **Buffer overflows**: The type system and bounds checking prevent them
- **Data races**: The borrow checker guarantees thread-safety
- **Null pointers**: The `Option<T>` system makes value absence explicit

```rust
// Rust: The compiler rejects unsafe code
let s: &str = some_option.unwrap(); // If None, panic... but you can use unwrap_or

// Best practice: explicit match pattern
match some_option {
    Some(value) => process(value),
    None => handle_absent(),
}
```

### 2. Performance

Rust offers performance comparable to C/C++:

| Metric | Rust | Python | Java |
|--------|------|--------|------|
| throughput | ~1M ops/s | ~50K ops/s | ~200K ops/s |
| memory footprint | ~2MB | ~50MB | ~100MB |
| cold start | <10ms | ~100ms | ~500ms |

### 3. Fearless Concurrency

Rust's ownership model allows writing parallel code without manual mutexes:

```rust
use rayon::prelude::*;

let results: Vec<RuleEvaluation> = rules
    .par_iter()
    .map(|rule| evaluate_rule(rule, &artifacts))
    .collect();
```

### 4. Static Typing

Rust's type system catches errors at compile time:

```rust
// The compiler knows exactly which fields each structure has
pub struct VerificationPayload {
    pub release_id: String,
    pub artifacts: Vec<Artifact>,      // Vec is safe, not null
    pub rules: Vec<VerificationRule>,   // Vec is safe, not null
}
```

### 5. Ecosystem

| Crate | Purpose |
|-------|---------|
| `rayon` | Parallel data processing |
| `serde` | JSON serialization/deserialization |
| `actix-web` | High-performance HTTP server |
| `thiserror` | Typed error handling |

---

## Rust Fundamentals

This section provides a quick introduction to the Rust concepts needed to understand the engine.

### Ownership and Borrowing

Rust uses a unique **ownership** system for memory management:

```rust
fn main() {
    // ownership: s1 is no longer valid after this line
    let s1 = String::from("hello");
    let s2 = s1; // s1 is "moved" to s2

    // println!("{}", s1); // ERROR: s1 is no longer the owner
    println!("{}", s2); // OK
}
```

**Ownership rules:**
1. Each value has a single owner
2. When the owner goes out of scope, the value is freed
3. There can only be one mutable reference to a value (or multiple immutable references)

### Lifetimes

Lifetimes prevent dangling references:

```rust
// 'a is a lifetime annotation that says:
// "the return will live at least as long as both references live"
fn longest<'a>(x: &'a str, y: &'a str) -> &'a str {
    if x.len() > y.len() { x } else { y }
}
```

### Option and Result

Rust has no `null`. Value absence is represented with `Option`:

```rust
fn find_artifact(id: &str, artifacts: &[Artifact]) -> Option<&Artifact> {
    artifacts.iter().find(|a| a.id == id)
}

match find_artifact("T-001", &artifacts) {
    Some(artifact) => println!("Found: {}", artifact.id),
    None => println!("Not found"),
}
```

`Result<T, E>` for operations that can fail:

```rust
fn read_file(path: &str) -> Result<String, std::io::Error> {
    std::fs::read_to_string(path)
}

// Usage with ?
let content = read_file("config.json")?;
```

### Structs and Enums

```rust
// Struct with fields
#[derive(Debug, Clone)]
pub struct Artifact {
    pub id: String,
    pub artifact_type: String,
    pub metadata: Value,  // serde_json::Value - flexible JSON
}

// Enum with variants
#[derive(Debug, Serialize, Deserialize, PartialEq)]
pub enum RuleStatus {
    Ok,
    Error,
    Warning,
    NoEvaluada,
}
```

### Traits

Traits define shared behavior:

```rust
// A trait defines methods that types must implement
trait Verifiable {
    fn verify(&self) -> bool;
}

// Implementation
impl Verifiable for Artifact {
    fn verify(&self) -> bool {
        !self.id.is_empty() && !self.artifact_type.is_empty()
    }
}
```

### Pattern Matching

Match is exhaustive and safe:

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

### Iterators and Closures

```rust
// Lazy iterators - very efficient
let ids: Vec<&str> = artifacts
    .iter()
    .filter(|a| a.artifact_type == "TAREA")
    .map(|a| a.id.as_str())
    .collect();

// Usage with Rayon for parallelism
use rayon::prelude::*;
let results: Vec<_> = artifacts.par_iter().map(|a| process(a)).collect();
```

### Cargo and Modules

```
engine/
├── Cargo.toml          # Package dependencies and metadata
└── src/
    ├── main.rs         # Entry point and HTTP server
    ├── models.rs       # Shared data structures
    ├── evaluator.rs    # Rule orchestrator
    ├── aggregator.rs   # Global verdict calculation
    └── rules/          # Rule implementations
        ├── mod.rs      # Submodule declarations
        ├── rv01.rs     # Rule RV-01: Existence
        ├── rv02.rs     # Rule RV-02: Traceability
        └── ...
```

---

## Engine Architecture

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
│              │  Global verdict  │                                 │
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

### Data Flow

1. **Reception**: The Actix server receives `POST /verify` with a JSON `VerificationPayload`
2. **Deserialization**: Serde converts the JSON into typed Rust structures
3. **Parallel Evaluation**: Rayon distributes rules across available threads
4. **Aggregation**: The verdict is calculated based on rule results
5. **Response**: The `EngineResult` is serialized to JSON and returned to the client

### Core Components

#### `models.rs` - Data Model

```rust
// Artifact: represents a verified work unit
pub struct Artifact {
    pub id: String,                    // Unique identifier
    pub artifact_type: String,         // "TAREA", "CÓDIGO", "DOCUMENTO", "PLAN"
    pub metadata: Value,               // Flexible JSON for specific data
}

// Configured verification rule
pub struct VerificationRule {
    pub id: String,                    // "RV-01" to "RV-10"
    pub severity: String,               // "OBLIGATORIA" or "OPCIONAL"
    pub params: Value,                  // Rule-specific parameters
}

// Possible rule states
pub enum RuleStatus {
    Ok,            // Rule satisfied
    Error,         // Rule violated
    Warning,       // Warning condition
    NoEvaluada,    // Rule not applicable
}

// Global engine verdict
pub enum Verdict {
    Valida,              // All mandatory rules OK
    ConAdvertencias,     // Some optional rule with warning
    NoValida,            // Some mandatory rule with error
}
```

#### `evaluator.rs` - Orchestrator

```rust
pub fn evaluate(payload: VerificationPayload) -> EngineResult {
    // Parallel evaluation of all rules
    let rule_results: Vec<RuleEvaluation> = payload.rules
        .par_iter()
        .map(|rule_config| {
            // Dispatch by rule ID
            match rule_config.id.as_str() {
                "RV-01" => rv01::evaluate(&payload.artifacts, rule_config),
                "RV-02" => rv02::evaluate(&payload.artifacts, rule_config),
                // ... etc
            }
        })
        .collect();

    // Aggregation for global verdict
    let verdict = aggregate(&rule_results, &payload.rules);

    EngineResult { verdict, rule_results }
}
```

#### `aggregator.rs` - Verdict Aggregator

```rust
pub fn aggregate(evaluations: &[RuleEvaluation], rules: &[VerificationRule]) -> Verdict {
    // 1. If any MANDATORY has Error → NoValida
    // 2. If all mandatory OK but some OPTIONAL Warning → ConAdvertencias
    // 3. If all OK → Valida
}
```

---

## Verification Rules

Each rule is a pure function: `evaluate(artifacts: &[Artifact], rule_config: &VerificationRule) -> RuleEvaluation`

### RV-01: Existence

**Purpose**: Validate that the artifact list is not empty.

**Parameters**: None (accepts default parameters).

**Logic**:
1. Checks if `artifacts.is_empty()`
2. If empty → `Error` with descriptive message
3. If not empty → `Ok`

**Error message**:
```
"The artifact list is empty. At least one artifact is required to proceed."
```

---

### RV-02: Traceability

**Purpose**: Cross-search to verify that references between artifacts are valid.

**Configurable parameters**:
| Parameter | Default | Description |
|-----------|---------|-------------|
| `source_type` | `"CÓDIGO"` | Artifact type containing references |
| `target_type` | `"TAREA"` | Referenced artifact type |
| `reference_field` | `"task_id"` | Metadata field with the referenced ID |

**Logic**:
1. Collects all IDs of target type artifacts (`target_type`)
2. For each source artifact, extracts the reference field value
3. Verifies that the referenced ID exists in the target ID set
4. If any ID does not exist → `Error` with list of orphan IDs

**Error message**:
```
"Orphan references detected: '2'. The following IDs referenced in 'CÓDIGO' artifacts
do not exist as 'TAREA': ["T-999", "T-888"]"
```

---

### RV-03: States

**Purpose**: Verify that all artifacts of a specific type have allowed states.

**Configurable parameters**:
| Parameter | Default | Description |
|-----------|---------|-------------|
| `artifact_type` | `"TAREA"` | Artifact type to verify |
| `allowed_states` | `["DONE", "CLOSED"]` | Valid states |
| `status_field` | `"status"` | Metadata field with the state |

**Logic**:
1. Filters artifacts by type
2. For each one, gets the status field value
3. Verifies that the state is in the allowed states list
4. If any artifact has an invalid state or missing field → `Error`

**Error message**:
```
"Artifacts with invalid state (allowed: ["DONE", "CLOSED"]): ["T-002"]"
```

---

### RV-04: Field Integrity

**Purpose**: Ensure that numeric fields in metadata are not null nor less than zero.

**Configurable parameters**:
| Parameter | Default | Description |
|-----------|---------|-------------|
| `artifact_type` | `"TAREA"` | Artifact type to verify |
| `numeric_fields` | `["effort", "estimation"]` | Fields to validate |

**Logic**:
1. Filters artifacts by type
2. For each specified field, verifies:
   - The field exists in metadata
   - The value is not `null`
   - The value is numeric (i64)
   - The value is >= 0
3. If any condition fails → `Error` with affected IDs

**Error message**:
```
"Artifacts with invalid or negative numeric fields (fields: ["effort", "estimation"]): ["T-002"]"
```

---

### RV-05: Type Availability

**Purpose**: Verify that artifacts of a specific type exist and have the accessibility flag set.

**Configurable parameters**:
| Parameter | Default | Description |
|-----------|---------|-------------|
| `artifact_type` | `"DOCUMENTO"` | Type to verify |
| `accessible_field` | `"accessible"` | Boolean accessibility field |

**Logic**:
1. Filters artifacts by type
2. If none exist → `Error`
3. For each one, verifies that the `accessible` field is `true`
4. If any is `false` or the field does not exist → `Error`

**Error message**:
```
"Inaccessible documents ('accessible' flag is not true): ["D-002"]"
```

---

### RV-06: Attribute Coherence

**Purpose**: Compare a specific attribute in metadata with an expected value.

**Configurable parameters**:
| Parameter | Default | Description |
|-----------|---------|-------------|
| `artifact_type` | `"DOCUMENTO"` | Type to verify |
| `attribute` | `"version"` | Field to compare |
| `expected_value` | `""` | Expected value |

**Logic**:
1. Filters artifacts by type
2. For each one, gets the attribute value
3. If the value does not match `expected_value` → `Error`
4. If the field does not exist → `Error`

**Error message**:
```
"Artifacts with 'version' value different from '2.0' (attribute 'version'): ["D-002"]"
```

---

### RV-07: External Registration

**Purpose**: Confirm the presence of a marker indicating registration in external tools.

**Configurable parameters**:
| Parameter | Default | Description |
|-----------|---------|-------------|
| `artifact_type` | `"PLAN"` | Marker artifact type |
| `marker_field` | `"external_registered"` | Boolean field indicating registration |

**Logic**:
1. Searches for an artifact of the specified type
2. If it does not exist → `Error`
3. Verifies that the marker field is `true`
4. If it does not exist or is `false` → `Error`

**Error message**:
```
"No marker artifact of type 'PLAN' found indicating external registration"
```

---

### RV-08: List Alignment

**Purpose**: Compare two sets of identifiers (declared vs. actual).

**Configurable parameters**:
| Parameter | Default | Description |
|-----------|---------|-------------|
| `master_artifact_id` | (required) | Master artifact ID |
| `master_field` | `"planned_tasks"` | Field with declared ID list |
| `target_type` | `"TAREA"` | Artifact type to compare |

**Logic**:
1. Searches for the master artifact by ID
2. Extracts the ID list from the master's field
3. Collects actual IDs of target type artifacts
4. Compares both sets using `HashSet`
5. If there are differences → `Error` with missing IDs

**Error message**:
```
"Discrepancy between declared list and payload. IDs declared in 'planned_tasks' of master
'PLAN-001' not present in 'TAREA' artifacts: ["T-003"]"
```

---

### RV-09: Reference Validation

**Purpose**: Verify that references (links/branches) have valid format and are accessible.

**Configurable parameters**:
| Parameter | Default | Description |
|-----------|---------|-------------|
| `artifact_type` | `"CÓDIGO"` | Type to verify |
| `reference_fields` | `["link", "branch"]` | Fields containing references |
| `accessible_field` | `"accessible"` | Boolean accessibility field |

**Format validation**:
- **Links**: Must start with `http://` or `https://`
- **Branches**: Must be alphanumeric with dashes, underscores, or slashes (e.g. `feature/new-feature`)

**Logic**:
1. Filters artifacts by type
2. For each reference field:
   - Verifies it exists and is a string
   - Validates the format depending on whether it looks like a URL or branch
3. Verifies that the `accessible` field is `true`
4. If any validation fails → `Error`

**Error message**:
```
"Invalid or inaccessible references found: ["C-001/link: 'ftp://invalid'"]"
```

---

### RV-10: Final Approval

**Purpose**: Search for an artifact with an approved state (APROBADO or VALIDADO).

**Configurable parameters**:
| Parameter | Default | Description |
|-----------|---------|-------------|
| `artifact_type` | `"DOCUMENTO"` | Type to search |
| `status_field` | `"status"` | Status field |
| `approved_states` | `["APROBADO", "VALIDADO"]` | States considered approved |

**Logic**:
1. Filters artifacts by type
2. Finds the first one whose state is in the approved states list
3. If found → `Ok` with artifact information
4. If none found → `Error`

**Error message**:
```
"No artifact of type 'DOCUMENTO' found with approved state (accepted states: ["APROBADO", "VALIDADO"])"
```

---

## API Reference

### Endpoint: `GET /health`

Simple health check to verify the service is running.

**Response**:
```json
{
  "status": "healthy",
  "service": "svaes-engine",
  "version": "1.0.0"
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

### Verdict Schema

| Verdict | Condition |
|---------|-----------|
| `VALIDA` | All MANDATORY rules returned OK, no warnings in OPTIONAL |
| `CON_ADVERTENCIAS` | All MANDATORY OK, but some OPTIONAL returned Warning |
| `NO_VALIDA` | Some MANDATORY returned Error |

### RuleStatus Schema

| Status | Description |
|--------|-------------|
| `OK` | Rule correctly satisfied |
| `ERROR` | Rule violated or invalid data |
| `WARNING` | Warning condition (optional rule) |
| `NO_EVALUADA` | Rule excluded or not recognized |

---

## Deployment Guide

### Requirements

- Rust 1.77+ (for compilation with edition 2021 and Rayon)
- Docker (for containers)
- 512MB minimum RAM
- Port 8081 available (configurable)

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENGINE_HOST` | `0.0.0.0` | Server bind host |
| `ENGINE_PORT` | `8081` | Server port |

### Manual Build

```bash
cd engine
cargo build --release
./target/release/core  # or core.exe on Windows
```

### Docker

#### Image build

```bash
cd engine
docker build -t svaes-engine:latest .
```

#### Running with Docker

```bash
# Basic
docker run -p 8081:8081 svaes-engine:latest

# With environment variables
docker run -p 8081:8081 \
  -e ENGINE_HOST=0.0.0.0 \
  -e ENGINE_PORT=8081 \
  svaes-engine:latest

# View logs
docker logs -f <container_id>
```

#### Docker Compose (development)

```bash
# Start
docker compose --profile development up svaes-engine-dev

# Stop
docker compose --profile development down
```

#### Docker Compose (production)

```bash
# Start
docker compose --profile production up svaes-engine

# Stop
docker compose --profile production down
```

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/verify` | POST | Verification rule evaluation |

---

## Glossary

| Term | Definition |
|------|------------|
| **Artifact** | Verified work unit (task, code, document) |
| **Payload** | Data payload received by the engine |
| **Rule** | Configured verification rule |
| **Verdict** | Global engine verdict |
| **Stateless** | Without internal state, does not persist data |
| **Ownership** | Rust system for memory management |
| **Borrow** | Temporary reference to data in Rust |
| **Lifetime** | Duration of validity of a reference |

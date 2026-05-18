# SVAES Engine

Software artifact verification engine written in Rust.

## Description

The engine receives a payload of artifacts and verification rules, and returns a global verdict (Valid / With Warnings / Invalid) along with detailed results for each evaluated rule.

## Features

- **Stateless**: Does not query databases or the network
- **Parallel**: Concurrent rule evaluation with Rayon
- **Strongly typed**: Fully typed with Rust

## Documentation

Full technical documentation: [docs/engine/README.md](../docs/engine/README.md)

## Verification Rules

| Rule | Description |
|------|-------------|
| RV-01 | Artifact existence |
| RV-02 | Cross-artifact traceability |
| RV-03 | State validation |
| RV-04 | Numeric field integrity |
| RV-05 | Type availability |
| RV-06 | Attribute coherence |
| RV-07 | External registration |
| RV-08 | List alignment |
| RV-09 | Reference validation |
| RV-10 | Final approval |

## Usage

```bash
cd engine
cargo run
```

Endpoints:
- `GET /health` - Health check
- `POST /verify` - Rule evaluation

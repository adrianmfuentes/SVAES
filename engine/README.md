# SVAES Engine

Motor de verificación de artefactos de software written en Rust.

## Descripción

El motor recibe un payload con artefactos y reglas de verificación, y retorna un veredicto global (Válida / Con Advertencias / No Válida) junto con el resultado detallado de cada regla evaluada.

## Características

- **Stateless**: No consulta bases de datos ni red
- **Paralelo**: Evaluación concurrente de reglas con Rayon
- **Tipado**: Totalmente tipado con Rust

## Documentación

Documentación técnica completa: [docs/engine/README.md](../docs/engine/README.md)

## Reglas de Verificación

| Regla | Descripción |
|-------|-------------|
| RV-01 | Existencia de artefactos |
| RV-02 | Trazabilidad entre artefactos |
| RV-03 | Validación de estados |
| RV-04 | Integridad de campos numéricos |
| RV-05 | Disponibilidad de tipos |
| RV-06 | Coherencia de atributos |
| RV-07 | Registro externo |
| RV-08 | Alineación de listas |
| RV-09 | Validación de referencias |
| RV-10 | Aprobación final |

## Uso

```bash
cd engine
cargo run
```

Endpoints:
- `GET /health` - Health check
- `POST /verify` - Evaluación de reglas
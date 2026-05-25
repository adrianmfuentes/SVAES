# SVAES Engine — Motor de Verificacion de Artefactos

Motor de verificacion de artefactos de software escrito en Rust. Recibe un payload JSON con artefactos y reglas de verificacion, evalua todas las reglas en paralelo y devuelve un veredicto global junto con los resultados detallados de cada regla.

## Arquitectura

El motor sigue un diseno **stateless** y **paralelo**:

- **Actix-web** sirve como servidor HTTP (puerto 8081 por defecto).
- **Rayon** ejecuta la evaluacion de reglas en paralelo.
- **Serde/JSON** gestiona la serializacion/deserializacion de los modelos.
- **thiserror** para manejo tipado de errores.
- No accede a bases de datos ni a la red — computacion pura en memoria.

### Modulos

| Modulo | Descripcion |
|--------|-------------|
| `main.rs` | Punto de entrada. Levanta el servidor HTTP Actix-web. |
| `lib.rs` | Raiz de la libreria. Define `AppState`, middleware de API key y los handlers `health_handler` (`GET /health`) y `verify_handler` (`POST /api/v1/verify`). |
| `models.rs` | Estructuras de datos: `Artifact`, `VerificationRule`, `VerificationPayload`, `RuleStatus`, `RuleEvaluation`, `Verdict`, `EngineResult`. |
| `evaluator.rs` | Logica central de evaluacion: itera reglas en paralelo, despacha a la funcion correspondiente segun `rule_id` y agrega resultados. |
| `aggregator.rs` | Determina el veredicto global a partir de los resultados individuales. |
| `rules/` | Implementacion de las 10 reglas de verificacion (RV-01 a RV-10). |

## Reglas de Verificacion

Cada regla recibe parametros configurables via `params` (JSON) en el payload y opera con valores por defecto documentados en su implementacion.

| ID | Nombre | Severidad por defecto | Descripcion |
|----|--------|-----------------------|-------------|
| RV-01 | Existencia de artefactos | OBLIGATORIA | La lista de artefactos no puede estar vacia. |
| RV-02 | Trazabilidad entre artefactos | OBLIGATORIA | Verifica que los artefactos de tipo `CODIGO` referencien tareas (`TAREA`) existentes mediante un campo de referencia. |
| RV-03 | Validacion de estados | OBLIGATORIA | Todos los artefactos de un tipo deben tener un campo de estado con un valor permitido (ej: `DONE`, `CLOSED`). |
| RV-04 | Integridad de campos numericos | OBLIGATORIA | Los campos numericos (ej: `effort`, `estimation`) deben ser no nulos, numericos y >= 0. |
| RV-05 | Disponibilidad de tipo | OBLIGATORIA | Debe existir al menos un artefacto de un tipo dado con un campo de accesibilidad a `true` (ej: `DOCUMENTO` accesible). |
| RV-06 | Coherencia de atributos | OPCIONAL | Compara un atributo de metadatos (ej: `version`) entre artefactos del mismo tipo contra un valor esperado. |
| RV-07 | Registro externo | OBLIGATORIA | Busca un artefacto marcador que indique registro externo completado (ej: `PLAN` con `external_registered`). |
| RV-08 | Alineacion de listas | OBLIGATORIA | Compara los IDs declarados en un artefacto maestro contra los IDs reales de artefactos en el payload. |
| RV-09 | Validacion de referencias | OPCIONAL | Valida el formato de URLs y nombres de rama, y verifica accesibilidad. |
| RV-10 | Aprobacion final | OBLIGATORIA | Al menos un artefacto de un tipo debe tener un estado de aprobacion (ej: `APROBADO`, `VALIDADO`). |

## Estructuras de Datos

### Payload de entrada (`POST /api/v1/verify`)

```json
{
  "artifacts": [
    {
      "id": "TASK-001",
      "artifact_type": "TAREA",
      "metadata": { "status": "DONE", "effort": 8 }
    }
  ],
  "rules": [
    {
      "id": "RV-03",
      "severity": "OBLIGATORIA",
      "params": { "artifact_type": "TAREA", "status_field": "status", "allowed_states": ["DONE", "CLOSED"] }
    }
  ]
}
```

### Respuesta

```json
{
  "verdict": "VALIDA",
  "rule_results": [
    {
      "rule_id": "RV-03",
      "status": "OK",
      "message": "Todos los artefactos tipo TAREA tienen un estado valido."
    }
  ],
  "summary": "Verificacion completada: todas las reglas OBLIGATORIAS pasaron."
}
```

### Niveles de Severidad y Veredicto

| Severidad de regla | Estado `Error` | Estado `Warning` |
|--------------------|----------------|------------------|
| `OBLIGATORIA` | Veredicto `NO_VALIDA` | — |
| `OPCIONAL` | — | Veredicto `CON_ADVERTENCIAS` |
| `EXCLUIDA` | Se omite (marca `NO_EVALUADA`) | Se omite |

El veredicto `VALIDA` se emite solo si no hay errores obligatorios ni advertencias opcionales. Los errores obligatorios tienen precedencia sobre las advertencias opcionales.

## Configuracion

Variables de entorno:

| Variable | Descripcion | Valor por defecto |
|----------|-------------|-------------------|
| `ENGINE_HOST` | Direccion de escucha | `0.0.0.0` |
| `ENGINE_PORT` | Puerto HTTP | `8081` |
| `ENGINE_API_KEY` | Clave API para autenticacion (opcional) | _(vacio — sin auth)_ |
| `RUST_LOG` | Nivel de logging | `info` |

## Uso

### Desarrollo local

```bash
cd engine
cargo run
```

### Docker

```bash
docker build -t svaes-engine -f engine/Dockerfile .
docker run -p 8081:8081 --env ENGINE_API_KEY=mi-clave svaes-engine
```

### Endpoints

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| `GET` | `/health` | Health check del motor |
| `POST` | `/api/v1/verify` | Evaluacion de reglas de verificacion |

### Autenticacion

Si `ENGINE_API_KEY` esta configurada, las peticiones al endpoint `/api/v1/verify` deben incluir la cabecera:

```
X-API-Key: mi-clave
```

Si no se configura, la autenticacion se deshabilita.

## Tests del Motor

Los tests unitarios estan embebidos en cada archivo fuente (`#[cfg(test)]`) dentro de:

- `src/aggregator.rs` — 7 tests de agregacion de veredictos
- `src/rules/rv01.rs` a `rv10.rs` — tests especificos por regla (3–7 tests cada uno)

### Ejecutar tests

```bash
cargo test                          # Unit tests del motor
cargo test --test http_pipeline     # Tests de integracion HTTP
cargo test --test performance       # Tests de rendimiento
cargo test -- --nocapture           # Con salida de logs
```

## Documentacion Tecnica

Documentacion tecnica completa: [docs/engine/README.md](../docs/engine/README.md)

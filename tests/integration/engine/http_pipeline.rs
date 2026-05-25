//! Pruebas de integracion de la Interfaz HTTP y el Pipeline del motor SVAES.
//!
//! Estas pruebas evalúan el motor como caja negra a traves de su API HTTP
//! (`actix-web`), enviando cargas `VerificationPayload` en JSON y comprobando
//! que se retorna un `EngineResult` estructurado.
//!
//! ## Que se valida aquí:
//!     - Deserialización del payload JSON con `serde_json`.
//!     - Resolución del perfil de reglas (OBLIGATORIA, OPCIONAL, EXCLUIDA).
//!     - Ejecución paralela de las 10 reglas del catálogo (RV-01 a RV-10).
//!     - Agregación del veredicto final (`Valida` / `ConAdvertencias` / `NoValida`).
//!
//! ## Ejecución
//! ```bash
//! cargo test --test http_pipeline
//! cargo test --test http_pipeline -- --nocapture
//! ```

use actix_web::{test, web, App};
use svaes_engine::{AppState, health_handler, verify_handler, EngineResult, Verdict, RuleStatus};
use serde_json::json;

fn build_full_payload() -> serde_json::Value {
    json!({
        "artifacts": [
            {"id": "C-001", "artifact_type": "CÓDIGO", "metadata": {"link": "https://github.com/repo/commit/abc123", "branch": "feature/new-feature", "accessible": true, "task_id": "T-001"}},
            {"id": "C-002", "artifact_type": "CÓDIGO", "metadata": {"link": "https://github.com/repo/commit/def456", "branch": "fix/bug", "accessible": true, "task_id": "T-002"}},
            {"id": "T-001", "artifact_type": "TAREA", "metadata": {"status": "DONE", "effort": 5, "estimation": 8}},
            {"id": "T-002", "artifact_type": "TAREA", "metadata": {"status": "CLOSED", "effort": 3, "estimation": 3}},
            {"id": "D-001", "artifact_type": "DOCUMENTO", "metadata": {"accessible": true, "version": "2.0", "status": "APROBADO"}},
            {"id": "D-002", "artifact_type": "DOCUMENTO", "metadata": {"accessible": true, "version": "2.0", "status": "VALIDADO"}},
            {"id": "PLAN-001", "artifact_type": "PLAN", "metadata": {"planned_tasks": ["T-001", "T-002"], "external_registered": true}}
        ],
        "rules": [
            {"id": "RV-01", "severity": "OBLIGATORIA", "params": {}},
            {"id": "RV-02", "severity": "OBLIGATORIA", "params": {"source_type": "CÓDIGO", "target_type": "TAREA", "reference_field": "task_id"}},
            {"id": "RV-03", "severity": "OBLIGATORIA", "params": {"artifact_type": "TAREA", "allowed_states": ["DONE", "CLOSED"], "status_field": "status"}},
            {"id": "RV-04", "severity": "OPCIONAL",    "params": {"artifact_type": "TAREA", "numeric_fields": ["effort", "estimation"]}},
            {"id": "RV-05", "severity": "OBLIGATORIA", "params": {"artifact_type": "DOCUMENTO", "accessible_field": "accessible"}},
            {"id": "RV-06", "severity": "OPCIONAL",    "params": {"artifact_type": "DOCUMENTO", "attribute": "version", "expected_value": "2.0"}},
            {"id": "RV-07", "severity": "OBLIGATORIA", "params": {"artifact_type": "PLAN", "marker_field": "external_registered"}},
            {"id": "RV-08", "severity": "OBLIGATORIA", "params": {"master_artifact_id": "PLAN-001", "master_field": "planned_tasks", "target_type": "TAREA"}},
            {"id": "RV-09", "severity": "OPCIONAL",    "params": {"artifact_type": "CÓDIGO", "reference_fields": ["link", "branch"], "accessible_field": "accessible"}},
            {"id": "RV-10", "severity": "OBLIGATORIA", "params": {"artifact_type": "DOCUMENTO", "status_field": "status", "approved_states": ["APROBADO", "VALIDADO"]}}
        ]
    })
}

fn build_payload_with_error() -> serde_json::Value {
    json!({
        "artifacts": [
            {"id": "C-001", "artifact_type": "CÓDIGO", "metadata": {"link": "https://github.com/repo/commit/abc", "branch": "feature/test", "accessible": true, "task_id": "T-999"}},
            {"id": "T-001", "artifact_type": "TAREA", "metadata": {"status": "IN_PROGRESS", "effort": -1}}
        ],
        "rules": [
            {"id": "RV-01", "severity": "OBLIGATORIA", "params": {}},
            {"id": "RV-02", "severity": "OBLIGATORIA", "params": {"source_type": "CÓDIGO", "target_type": "TAREA", "reference_field": "task_id"}},
            {"id": "RV-03", "severity": "OBLIGATORIA", "params": {"artifact_type": "TAREA", "allowed_states": ["DONE", "CLOSED"], "status_field": "status"}},
            {"id": "RV-04", "severity": "OPCIONAL",    "params": {"artifact_type": "TAREA", "numeric_fields": ["effort", "estimation"]}},
            {"id": "RV-06", "severity": "OPCIONAL",    "params": {"artifact_type": "DOCUMENTO", "attribute": "version", "expected_value": "2.0"}},
            {"id": "RV-10", "severity": "OBLIGATORIA", "params": {"artifact_type": "DOCUMENTO", "status_field": "status", "approved_states": ["APROBADO", "VALIDADO"]}}
        ]
    })
}

/// El endpoint de salud `/health` responde con estado `healthy`, nombre del servicio y version.
///
/// Método `GET /health`
///
/// Resultado esperado
///     - HTTP 200.
///     - JSON `{"status": "healthy", "service": "svaes-engine", "version": "..."}`.
#[actix_web::test]
async fn tc_int_http_01_health_endpoint_returns_healthy() {
    let app = test::init_service(
        App::new()
            .app_data(web::Data::new(AppState { api_key: String::new() }))
            .service(health_handler)
    ).await;
    let req = test::TestRequest::get().uri("/health").to_request();
    let resp = test::call_service(&app, req).await;

    assert!(resp.status().is_success());
    let body = test::read_body(resp).await;
    let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
    assert_eq!(json["status"], "healthy");
    assert_eq!(json["service"], "svaes-engine");
    assert!(json["version"].as_str().is_some());
}

/// Un payload valido con las 10 reglas y artefactos correctos retorna `Valida` con 10 `RuleEvaluation`.
///
/// Método `POST /api/v1/verify`
///
/// Payload 7 artefactos (CODIGO, TAREA, DOCUMENTO, PLAN) + 10 reglas completas.
///
/// Resultado esperado
///     - HTTP 200.
///     - `EngineResult.verdict == Valida`.
///     - `EngineResult.rule_results.len() == 10`.
///     - `EngineResult.summary` no vacío.
#[actix_web::test]
async fn tc_int_http_02_verify_valid_payload_returns_engine_result() {
    let app = test::init_service(
        App::new()
            .app_data(web::Data::new(AppState { api_key: String::new() }))
            .service(verify_handler)
    ).await;
    let payload = build_full_payload();
    let req = test::TestRequest::post()
        .uri("/api/v1/verify")
        .set_json(&payload)
        .to_request();
    let resp = test::call_service(&app, req).await;

    assert!(resp.status().is_success(), "Expected 200 OK, got {}", resp.status());
    let body = test::read_body(resp).await;
    let result: EngineResult = serde_json::from_slice(&body)
        .expect("Failed to deserialize response as EngineResult");

    assert!(matches!(result.verdict, Verdict::Valida),
        "Expected Valida verdict, got {:?}", result.verdict);
    assert_eq!(result.rule_results.len(), 10, "Expected 10 rule results");
    assert!(!result.summary.is_empty());
}

/// Un payload con datos inválidos (referencia huérfana, estado no permitido, campo negativo) retorna `NoValida` con al menos un
/// `RuleStatus::Error`.
///
/// Método `POST /api/v1/verify`
///
/// Errores inyectados
///     - `task_id: "T-999"` que no existe → RV-02 falla.
///     - `status: "IN_PROGRESS"` no permitido → RV-03 falla.
///     - `effort: -1` negativo → RV-04 falla.
///
/// Resultado esperado
///     - HTTP 200.
///     - `EngineResult.verdict == NoValida`.
///     - Al menos un `rule_result` con `status == Error`.
#[actix_web::test]
async fn tc_int_http_03_verify_error_payload_returns_no_valida() {
    let app = test::init_service(
        App::new()
            .app_data(web::Data::new(AppState { api_key: String::new() }))
            .service(verify_handler)
    ).await;
    let payload = build_payload_with_error();
    let req = test::TestRequest::post()
        .uri("/api/v1/verify")
        .set_json(&payload)
        .to_request();
    let resp = test::call_service(&app, req).await;

    assert!(resp.status().is_success());
    let body = test::read_body(resp).await;
    let result: EngineResult = serde_json::from_slice(&body)
        .expect("Failed to deserialize response");

    assert!(matches!(result.verdict, Verdict::NoValida),
        "Expected NoValida, got {:?}", result.verdict);

    let error_count = result.rule_results.iter()
        .filter(|r| r.status == RuleStatus::Error)
        .count();
    assert!(error_count > 0, "Expected at least one Error, got {}", error_count);
}

/// Las reglas con severidad `EXCLUIDA` se omiten durante la evaluación y su `rule_result` se marca como `NoEvaluada`, 
/// sin afectar al veredicto global.
///
/// Método `POST /api/v1/verify`
///
/// Payload 1 regla OBLIGATORIA (RV-01) + 2 reglas EXCLUIDA (RV-02, RV-03).
///
/// Resultado esperado
///     - HTTP 200.
///     - 2 `rule_results` con `status == NoEvaluada`.
///     - Cada mensaje de `NoEvaluada` contiene "excluida".
#[actix_web::test]
async fn tc_int_http_04_excluida_rules_are_skipped() {
    let app = test::init_service(
        App::new()
            .app_data(web::Data::new(AppState { api_key: String::new() }))
            .service(verify_handler)
    ).await;
    let payload = json!({
        "artifacts": [{"id": "A-001", "artifact_type": "TAREA", "metadata": {"status": "DONE"}}],
        "rules": [
            {"id": "RV-01", "severity": "OBLIGATORIA", "params": {}},
            {"id": "RV-02", "severity": "EXCLUIDA", "params": {}},
            {"id": "RV-03", "severity": "EXCLUIDA", "params": {}}
        ]
    });
    let req = test::TestRequest::post()
        .uri("/api/v1/verify")
        .set_json(&payload)
        .to_request();
    let resp = test::call_service(&app, req).await;

    assert!(resp.status().is_success());
    let body = test::read_body(resp).await;
    let result: EngineResult = serde_json::from_slice(&body).unwrap();

    let no_evaluada_count = result.rule_results.iter()
        .filter(|r| r.status == RuleStatus::NoEvaluada)
        .count();
    assert_eq!(no_evaluada_count, 2, "Expected 2 NoEvaluada results for EXCLUIDA rules");

    let excluded_results: Vec<_> = result.rule_results.iter()
        .filter(|r| r.status == RuleStatus::NoEvaluada)
        .collect();
    for r in excluded_results {
        assert!(r.message.as_ref().unwrap().contains("excluida"),
            "Message should mention exclusion: {:?}", r.message);
    }
}

/// Un `rule_id` desconocido (no implementado en el despachador) retorna `NoEvaluada` con un 
/// mensaje indicando que el ID no esta en el catalogo.
///
/// Método `POST /api/v1/verify`
///
/// Payload 1 artefacto + 1 regla con `id: "RV-99"` (inexistente).
///
/// Resultado esperado
///     - HTTP 200.
///     - `rule_results[0].status == NoEvaluada`.
///     - El mensaje contiene "no reconocido".
#[actix_web::test]
async fn tc_int_http_05_unknown_rule_id_returns_no_evaluada() {
    let app = test::init_service(
        App::new()
            .app_data(web::Data::new(AppState { api_key: String::new() }))
            .service(verify_handler)
    ).await;
    let payload = json!({
        "artifacts": [{"id": "A-001", "artifact_type": "TAREA", "metadata": {}}],
        "rules": [
            {"id": "RV-99", "severity": "OBLIGATORIA", "params": {}}
        ]
    });
    let req = test::TestRequest::post()
        .uri("/api/v1/verify")
        .set_json(&payload)
        .to_request();
    let resp = test::call_service(&app, req).await;

    assert!(resp.status().is_success());
    let body = test::read_body(resp).await;
    let result: EngineResult = serde_json::from_slice(&body).unwrap();

    assert_eq!(result.rule_results.len(), 1);
    assert_eq!(result.rule_results[0].status, RuleStatus::NoEvaluada);
    assert!(result.rule_results[0].message.as_ref().unwrap().contains("no reconocido"));
}

/// Validación estructural del `EngineResult` retornado. Comprueba que el JSON contiene todos los campos obligatorios y que los
/// valores de `verdict` y `status` usan el formato SCREAMING_SNAKE_CASE esperado por el backend de Python.
///
/// Método `POST /api/v1/verify`
///
/// Resultado esperado
///     - Campos `verdict` (string), `rule_results` (array), `summary` (string).
///     - `verdict` ∈ {"VALIDA", "NO_VALIDA", "CON_ADVERTENCIAS"}.
///     - Cada `rule_result` tiene `rule_id` (string) y `status` (string).
///     - `status` ∈ {"OK", "ERROR", "WARNING", "NO_EVALUADA"}.
#[actix_web::test]
async fn tc_int_http_06_engine_result_structure_is_complete() {
    let app = test::init_service(
        App::new()
            .app_data(web::Data::new(AppState { api_key: String::new() }))
            .service(verify_handler)
    ).await;
    let payload = build_full_payload();
    let req = test::TestRequest::post()
        .uri("/api/v1/verify")
        .set_json(&payload)
        .to_request();
    let resp = test::call_service(&app, req).await;
    let body = test::read_body(resp).await;

    let json: serde_json::Value = serde_json::from_slice(&body).unwrap();

    assert!(json.get("verdict").is_some(), "Missing 'verdict' field");
    assert!(json.get("rule_results").is_some_and(|v| v.is_array()), "Missing or invalid 'rule_results'");
    assert!(json.get("summary").is_some_and(|v| v.is_string()), "Missing or invalid 'summary'");

    let verdict = json["verdict"].as_str().unwrap();
    assert!(verdict == "VALIDA" || verdict == "NO_VALIDA" || verdict == "CON_ADVERTENCIAS",
        "Unexpected verdict value: {}", verdict);

    let results = json["rule_results"].as_array().unwrap();
    for rr in results {
        assert!(rr.get("rule_id").is_some_and(|v| v.is_string()), "Each result must have rule_id");
        assert!(rr.get("status").is_some_and(|v| v.is_string()), "Each result must have status");

        let status = rr["status"].as_str().unwrap();
        assert!(status == "OK" || status == "ERROR" || status == "WARNING" || status == "NO_EVALUADA",
            "Unexpected status: {}", status);
    }
}

/// Un payload sin artefactos pero con reglas OBLIGATORIA que requieren datos (RV-01, RV-05, RV-07, RV-10) produce `NoValida`.
///
/// Método `POST /api/v1/verify`
///
/// Payload `artifacts: []` + 4 reglas OBLIGATORIA que fallan ante lista vacía.
///
/// Resultado esperado
///     - HTTP 200.
///     - `EngineResult.verdict == NoValida`.
#[actix_web::test]
async fn tc_int_http_07_empty_artifacts_with_rules_produces_errors() {
    let app = test::init_service(
        App::new()
            .app_data(web::Data::new(AppState { api_key: String::new() }))
            .service(verify_handler)
    ).await;
    let payload = json!({
        "artifacts": [],
        "rules": [
            {"id": "RV-01", "severity": "OBLIGATORIA", "params": {}},
            {"id": "RV-05", "severity": "OBLIGATORIA", "params": {}},
            {"id": "RV-07", "severity": "OBLIGATORIA", "params": {}},
            {"id": "RV-10", "severity": "OBLIGATORIA", "params": {}}
        ]
    });
    let req = test::TestRequest::post()
        .uri("/api/v1/verify")
        .set_json(&payload)
        .to_request();
    let resp = test::call_service(&app, req).await;

    assert!(resp.status().is_success());
    let body = test::read_body(resp).await;
    let result: EngineResult = serde_json::from_slice(&body).unwrap();

    assert!(matches!(result.verdict, Verdict::NoValida),
        "Empty artifacts with mandatory rules should produce NoValida, got {:?}", result.verdict);
}

/// Una regla OPCIONAL que no encuentra artefactos de su tipo NO produce `Warning` (solo devuelve `Ok` porque RV-06 retorna `Ok`
/// cuando no hay artefactos que coincidan con `artifact_type`). Por tanto, el veredicto se mantiene `Valida`.
///
/// Método `POST /api/v1/verify`
///
/// Payload 1 artefacto TAREA + RV-01 (OBLIGATORIA) + RV-06 (OPCIONAL, busca DOCUMENTO).
///
/// Resultado esperado
///     - HTTP 200.
///     - `EngineResult.verdict == Valida` (la regla opcional no genera Warning).
#[actix_web::test]
async fn tc_int_http_08_pipeline_respects_optional_severity() {
    let app = test::init_service(
        App::new()
            .app_data(web::Data::new(AppState { api_key: String::new() }))
            .service(verify_handler)
    ).await;
    let payload = json!({
        "artifacts": [
            {"id": "A-001", "artifact_type": "TAREA", "metadata": {"status": "DONE", "effort": 5, "estimation": 10}}
        ],
        "rules": [
            {"id": "RV-01", "severity": "OBLIGATORIA", "params": {}},
            {"id": "RV-06", "severity": "OPCIONAL", "params": {"artifact_type": "DOCUMENTO", "attribute": "version", "expected_value": "2.0"}}
        ]
    });
    let req = test::TestRequest::post()
        .uri("/api/v1/verify")
        .set_json(&payload)
        .to_request();
    let resp = test::call_service(&app, req).await;

    assert!(resp.status().is_success());
    let body = test::read_body(resp).await;
    let result: EngineResult = serde_json::from_slice(&body).unwrap();

    assert!(matches!(result.verdict, Verdict::Valida),
        "Optional rules without Warning should yield Valida, got {:?}", result.verdict);
}

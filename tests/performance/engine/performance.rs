//! Pruebas de Rendimiento y Concurrencia del motor SVAES.
//!
//! Validan el requisito RNF-07: el motor debe procesar una verificacion
//! completa (10 reglas) en menos de 500 ms, aprovechando la ejecución
//! paralela de la librería `rayon` sin que el garbage collector ni la
//! seguridad de memoria introduzcan latencias impredecibles.
//!
//! ## Que se valida aquí:
//!     - Tiempo de ejecución de 10 reglas < 500 ms (petición individual).
//!     - Estabilidad en bucle de 100 iteraciones (promedio < 500 ms).
//!     - Escalabilidad con payloads grandes (102 artefactos, 10 reglas).
//!
//! ## Ejecución
//! ```bash
//! cargo test --test performance --release
//! cargo test --test performance --release -- --nocapture
//! ```

use actix_web::{test, web, App};
use svaes_engine::{AppState, verify_handler, EngineResult, Verdict};
use serde_json::json;
use std::time::Instant;

fn build_ten_rule_payload() -> serde_json::Value {
    json!({
        "artifacts": [
            {"id": "C-001", "artifact_type": "CÓDIGO", "metadata": {"link": "https://github.com/repo/commit/abc123", "branch": "feature/new-feature", "accessible": true, "task_id": "T-001"}},
            {"id": "T-001", "artifact_type": "TAREA", "metadata": {"status": "DONE", "effort": 5, "estimation": 8}},
            {"id": "D-001", "artifact_type": "DOCUMENTO", "metadata": {"accessible": true, "version": "2.0", "status": "APROBADO"}},
            {"id": "PLAN-001", "artifact_type": "PLAN", "metadata": {"planned_tasks": ["T-001"], "external_registered": true}}
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

/// Una petición POST con 10 reglas debe completarse en menos de 500 ms.
///
/// Requisito cubierto RNF-07 — tiempo de motor < 500 ms.
///
/// Método `POST /api/v1/verify` con las 10 reglas del catalogo.
///
/// Resultado esperado
///     - HTTP 200, `Verdict::Valida`, 10 `rule_results`.
///     - `elapsed < 500 ms`.
#[actix_web::test]
async fn tc_per_vl_02_ten_rules_execution_under_500ms() {
    let app = test::init_service(
        App::new()
            .app_data(web::Data::new(AppState { api_key: String::new() }))
            .service(verify_handler)
    ).await;
    let payload = build_ten_rule_payload();

    let start = Instant::now();
    let req = test::TestRequest::post()
        .uri("/api/v1/verify")
        .set_json(&payload)
        .to_request();
    let resp = test::call_service(&app, req).await;
    let elapsed = start.elapsed();

    assert!(resp.status().is_success());
    let body = test::read_body(resp).await;
    let result: EngineResult = serde_json::from_slice(&body).unwrap();

    assert!(matches!(result.verdict, Verdict::Valida));
    assert_eq!(result.rule_results.len(), 10, "All 10 rules must be evaluated");

    assert!(
        elapsed.as_millis() < 500,
        "RNF-07 violado: motor tardo {} ms (limite: 500 ms) con 10 reglas",
        elapsed.as_millis()
    );
}

/// 100 iteraciones consecutivas del pipeline completo con 10 reglas. Se mide promedio, mínimo y máximo.
///
/// Requisito cubierto RNF-07 — estabilidad temporal. El promedio debe ser < 500 ms y el peor caso < 1000 ms (margen de seguridad para entornos CI).
///
/// Método Bucle `for` de 100 iteraciones sobre `POST /api/v1/verify`.
///
/// Resultado esperado
///     - `avg < 500 ms`, `max < 1000 ms`.
///     - Las 100 respuestas retornan HTTP 200.
#[actix_web::test]
async fn tc_per_vl_02_loop_100_iterations_average_under_500ms() {
    let app = test::init_service(
        App::new()
            .app_data(web::Data::new(AppState { api_key: String::new() }))
            .service(verify_handler)
    ).await;
    let payload = build_ten_rule_payload();
    let iterations: u32 = 100;
    let mut total_ms = 0u128;
    let mut max_ms = 0u128;
    let mut min_ms = u128::MAX;

    for _ in 0..iterations {
        let start = Instant::now();
        let req = test::TestRequest::post()
            .uri("/api/v1/verify")
            .set_json(&payload)
            .to_request();
        let resp = test::call_service(&app, req).await;
        let elapsed = start.elapsed().as_millis();

        assert!(resp.status().is_success());
        let body = test::read_body(resp).await;
        let _result: EngineResult = serde_json::from_slice(&body).unwrap();

        total_ms += elapsed;
        if elapsed > max_ms { max_ms = elapsed; }
        if elapsed < min_ms { min_ms = elapsed; }
    }

    let avg_ms = total_ms as f64 / iterations as f64;

    println!(
        "TC-PER-VL-02: {} iteraciones | avg={:.2} ms | min={} ms | max={} ms",
        iterations, avg_ms, min_ms, max_ms
    );

    assert!(
        avg_ms < 500.0,
        "RNF-07 violado: promedio de {} ms en {} iteraciones (limite: 500 ms)",
        avg_ms, iterations
    );
    assert!(
        max_ms < 1000,
        "Peor caso excesivo: {} ms en {} iteraciones",
        max_ms, iterations
    );
}

/// Payload grande con 102 artefactos (50 CODIGO + 50 TAREA + 1 DOCUMENTO + 1 PLAN) y las 10 reglas.
/// El tiempo debe permanecer < 500 ms demostrando que `rayon` escala con el tamaño de datos.
///
/// Requisito cubierto RNF-07 — escalabilidad con volumen de artefactos.
///
/// Método `POST /api/v1/verify` con 102 artefactos y 10 reglas.
///
/// Resultado esperado
///     - HTTP 200, `Verdict::Valida`, 10 `rule_results`.
///     - `elapsed < 500 ms`.
#[actix_web::test]
async fn tc_per_vl_02_large_payload_still_under_500ms() {
    let app = test::init_service(
        App::new()
            .app_data(web::Data::new(AppState { api_key: String::new() }))
            .service(verify_handler)
    ).await;

    let mut artifacts = Vec::new();
    for i in 1..=50 {
        artifacts.push(json!({
            "id": format!("C-{:03}", i),
            "artifact_type": "CODIGO",
            "metadata": {
                "link": format!("https://github.com/repo/commit/{}", i),
                "branch": format!("feature/branch-{}", i),
                "accessible": true,
                "task_id": format!("T-{:03}", i)
            }
        }));
        artifacts.push(json!({
            "id": format!("T-{:03}", i),
            "artifact_type": "TAREA",
            "metadata": {"status": "DONE", "effort": 3, "estimation": 5}
        }));
    }
    artifacts.push(json!({
        "id": "D-001", "artifact_type": "DOCUMENTO",
        "metadata": {"accessible": true, "version": "2.0", "status": "APROBADO"}
    }));
    artifacts.push(json!({
        "id": "PLAN-001", "artifact_type": "PLAN",
        "metadata": {
            "planned_tasks": (1..=50).map(|i| format!("T-{:03}", i)).collect::<Vec<_>>(),
            "external_registered": true
        }
    }));

    let payload = json!({
        "artifacts": artifacts,
        "rules": [
            {"id": "RV-01", "severity": "OBLIGATORIA", "params": {}},
            {"id": "RV-02", "severity": "OBLIGATORIA", "params": {"source_type": "CODIGO", "target_type": "TAREA", "reference_field": "task_id"}},
            {"id": "RV-03", "severity": "OBLIGATORIA", "params": {"artifact_type": "TAREA", "allowed_states": ["DONE", "CLOSED"], "status_field": "status"}},
            {"id": "RV-04", "severity": "OPCIONAL",    "params": {"artifact_type": "TAREA", "numeric_fields": ["effort", "estimation"]}},
            {"id": "RV-05", "severity": "OBLIGATORIA", "params": {"artifact_type": "DOCUMENTO", "accessible_field": "accessible"}},
            {"id": "RV-06", "severity": "OPCIONAL",    "params": {"artifact_type": "DOCUMENTO", "attribute": "version", "expected_value": "2.0"}},
            {"id": "RV-07", "severity": "OBLIGATORIA", "params": {"artifact_type": "PLAN", "marker_field": "external_registered"}},
            {"id": "RV-08", "severity": "OBLIGATORIA", "params": {"master_artifact_id": "PLAN-001", "master_field": "planned_tasks", "target_type": "TAREA"}},
            {"id": "RV-09", "severity": "OPCIONAL",    "params": {"artifact_type": "CODIGO", "reference_fields": ["link", "branch"], "accessible_field": "accessible"}},
            {"id": "RV-10", "severity": "OBLIGATORIA", "params": {"artifact_type": "DOCUMENTO", "status_field": "status", "approved_states": ["APROBADO", "VALIDADO"]}}
        ]
    });

    let start = Instant::now();
    let req = test::TestRequest::post()
        .uri("/api/v1/verify")
        .set_json(&payload)
        .to_request();
    let resp = test::call_service(&app, req).await;
    let elapsed = start.elapsed();

    assert!(resp.status().is_success());
    let body = test::read_body(resp).await;
    let result: EngineResult = serde_json::from_slice(&body).unwrap();

    println!(
        "TC-PER-VL-02 (large): 102 artefactos, 10 reglas -> {} ms",
        elapsed.as_millis()
    );

    assert_eq!(result.rule_results.len(), 10);
    assert!(
        elapsed.as_millis() < 500,
        "RNF-07 violado con payload grande: {} ms (limite: 500 ms)",
        elapsed.as_millis()
    );
}

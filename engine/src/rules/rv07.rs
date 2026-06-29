use serde_json::json;
use crate::models::{Artifact, RuleEvaluation, RuleStatus, VerificationRule};

/// RV-07: Confirma la presencia de un artefacto que actúe como "marcador"
/// de que la operación ha sido registrada en herramientas externas de gestión.
///
/// # Parámetros
/// * `artifacts` - Slice de artefactos a verificar.
/// * `rule_config` - Configuración de la regla con parámetros:
///   - `artifact_type`: Tipo de artefacto marcador a buscar. Opcional — si no se
///     proporciona, busca en todos los tipos de artefacto.
///   - `marker_field`: Campo en metadata que indica registro externo (default: "external_registered").
///
/// # Lógica
/// 1. Si `artifact_type` está configurado, busca solo ese tipo.
/// 2. Si no, busca en todos los tipos de artefacto.
/// 3. Si no encuentra ningún artefacto con el marcador, devuelve Error.
/// 4. Si encuentra y el campo marker es `true`, devuelve Ok.
///
/// # Retorno
/// `RuleEvaluation` con el estado correspondiente indicando si el marcador fue encontrado.
const PERMITIDOS: &[&str] = &["TAREA", "CAMBIO"];

pub fn evaluate(artifacts: &[Artifact], rule_config: &VerificationRule) -> RuleEvaluation {
    let artifact_type = rule_config.params
        .get("artifact_type")
        .and_then(|v| v.as_str());

    if let Some(t) = artifact_type {
        if !PERMITIDOS.contains(&t) {
            return RuleEvaluation {
                rule_id: rule_config.id.clone(),
                status: RuleStatus::Error,
                message: Some("rule_evidence.error.RV-07.tipo_no_permitido".to_string()),
                message_params: Some(json!({
                    "artifact_type": t,
                    "tipos_permitidos": PERMITIDOS,
                })),
            };
        }
    }

    let marker_field = rule_config.params
        .get("marker_field")
        .and_then(|v| v.as_str())
        .unwrap_or("external_registered");

    let marker_artifact = match artifact_type {
        Some(t) => artifacts.iter().find(|a| a.artifact_type == t),
        None => artifacts.iter().find(|a| {
            a.metadata.get(marker_field).and_then(|v| v.as_bool()).unwrap_or(false)
        }),
    };

    match marker_artifact {
        Some(artifact) => {
            let found_type = artifact_type.unwrap_or(&artifact.artifact_type);
            match artifact.metadata.get(marker_field) {
                Some(val) if val.as_bool() == Some(true) => {
                    RuleEvaluation {
                        rule_id: rule_config.id.clone(),
                        status: RuleStatus::Ok,
                        message: Some("rule_evidence.ok.RV-07.found".to_string()),
                        message_params: Some(json!({
                            "artifact_type": found_type,
                            "artifact_id": artifact.id,
                        })),
                    }
                }
                _ => {
                    RuleEvaluation {
                        rule_id: rule_config.id.clone(),
                        status: RuleStatus::Error,
                        message: Some("rule_evidence.error.RV-07.not_true".to_string()),
                        message_params: Some(json!({
                            "artifact_id": artifact.id,
                            "artifact_type": found_type,
                            "marker_field": marker_field,
                        })),
                    }
                }
            }
        }
        None => {
            RuleEvaluation {
                rule_id: rule_config.id.clone(),
                status: RuleStatus::Error,
                message: Some("rule_evidence.error.RV-07.not_found".to_string()),
                message_params: Some(json!({
                    "artifact_type": artifact_type.unwrap_or("any"),
                })),
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn make_artifact(id: &str, artifact_type: &str, metadata: serde_json::Value) -> Artifact {
        Artifact {
            id: id.to_string(),
            artifact_type: artifact_type.to_string(),
            metadata,
        }
    }

    fn make_rule_with_type(id: &str, artifact_type: &str) -> VerificationRule {
        VerificationRule {
            id: id.to_string(),
            severity: "OBLIGATORIA".to_string(),
            params: json!({"artifact_type": artifact_type}),
        }
    }

    fn make_rule_no_params(id: &str) -> VerificationRule {
        VerificationRule {
            id: id.to_string(),
            severity: "OBLIGATORIA".to_string(),
            params: json!({}),
        }
    }

    /// TC-UNI-MOT-07: RV-07 caso base — marcador de registro externo encontrado.
    /// Each Choice: cubre el resultado OK para registro externo.
    #[test]
    fn tc_uni_mot_07_rv07_marker_found_returns_ok() {
        let artifacts = vec![
            make_artifact("T-001", "TAREA", json!({"external_registered": true})),
        ];
        let rule = make_rule_with_type("RV-07", "TAREA");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Ok);
        assert!(result.message.is_some());
    }

    #[test]
    fn no_artifact_type_searches_all_types() {
        let artifacts = vec![
            make_artifact("T-001", "TAREA", json!({"external_registered": true})),
        ];
        let rule = make_rule_no_params("RV-07");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Ok);
    }

    #[test]
    fn no_artifact_type_no_marker_found_returns_error() {
        let artifacts = vec![
            make_artifact("C-001", "CODIGO", json!({})),
        ];
        let rule = make_rule_no_params("RV-07");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
    }

    #[test]
    fn marker_artifact_not_found_returns_error() {
        let artifacts = vec![
            make_artifact("C-001", "CODIGO", json!({})),
        ];
        let rule = make_rule_with_type("RV-07", "TAREA");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
        let msg = result.message.unwrap();
        assert_eq!(msg, "rule_evidence.error.RV-07.not_found");
        let params = result.message_params.unwrap();
        assert!(params["artifact_type"].as_str().unwrap().contains("TAREA"));
    }

    #[test]
    fn marker_field_false_returns_error() {
        let artifacts = vec![
            make_artifact("T-001", "TAREA", json!({"external_registered": false})),
        ];
        let rule = make_rule_with_type("RV-07", "TAREA");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
        let msg = result.message.unwrap();
        assert_eq!(msg, "rule_evidence.error.RV-07.not_true");
        let params = result.message_params.unwrap();
        assert!(params["artifact_id"].as_str().unwrap().contains("T-001"));
    }

    #[test]
    fn marker_field_missing_returns_error() {
        let artifacts = vec![
            make_artifact("T-001", "TAREA", json!({"other_field": true})),
        ];
        let rule = make_rule_with_type("RV-07", "TAREA");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
    }

    #[test]
    fn tipo_no_permitido_devuelve_error() {
        let artifacts = vec![
            make_artifact("D-001", "DOCUMENTO", json!({"external_registered": true})),
        ];
        let rule = make_rule_with_type("RV-07", "DOCUMENTO");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
        let msg = result.message.unwrap();
        assert_eq!(msg, "rule_evidence.error.RV-07.tipo_no_permitido");
    }
}

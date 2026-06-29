use serde_json::json;
use crate::models::{Artifact, RuleEvaluation, RuleStatus, VerificationRule};

/// RV-04: Asegura que campos numéricos o de esfuerzo en la metadata no sean nulos ni menores a cero.
///
/// # Parámetros
/// * `artifacts` - Slice de artefactos a verificar.
/// * `rule_config` - Configuración de la regla con parámetros:
///   - `artifact_type`: Tipo de artefacto a verificar (default: "TAREA").
///   - `numeric_fields`: Array con los nombres de campos a validar (default: ["effort", "estimation"]).
///
/// # Lógica
/// 1. Obtiene el tipo de artefacto y lista de campos a verificar.
/// 2. Por cada artefacto del tipo especificado, verifica que cada campo exista y sea numérico >= 0.
/// 3. Si algún campo es nulo, no numérico, o menor a cero, añade el ID a la lista de errores.
/// 4. Retorna Error con los IDs que tienen campos inválidos.
///
/// # Retorno
/// `RuleEvaluation` con el estado correspondiente y IDs de artefactos con campos inválidos.
pub fn evaluate(artifacts: &[Artifact], rule_config: &VerificationRule) -> RuleEvaluation {
    if artifacts.is_empty() {
        return RuleEvaluation {
            rule_id: rule_config.id.clone(),
            status: RuleStatus::NoEvaluada,
            message: Some("rule_evidence.no_evaluada.empty_artifacts".to_string()),
            message_params: None,
        };
    }

    let artifact_type = rule_config.params
        .get("artifact_type")
        .and_then(|v| v.as_str())
        .unwrap_or("TAREA");

    let numeric_fields: Vec<&str> = rule_config.params
        .get("numeric_fields")
        .and_then(|v| v.as_array())
        .map(|arr| arr.iter().filter_map(|v| v.as_str()).collect())
        .unwrap_or_else(|| vec!["effort", "estimation"]);

    let invalid_artifacts: Vec<&str> = artifacts
        .iter()
        .filter(|a| a.artifact_type == artifact_type)
        .filter(|a| {
            numeric_fields.iter().any(|field| {
                match a.metadata.get(*field) {
                    Some(val) => {
                        if val.is_null() {
                            return true;
                        }
                        match val.as_f64() {
                            Some(n) => n < 0.0,
                            None => true,
                        }
                    }
                    None => true,
                }
            })
        })
        .map(|a| a.id.as_str())
        .collect();

    if invalid_artifacts.is_empty() {
        RuleEvaluation {
            rule_id: rule_config.id.clone(),
            status: RuleStatus::Ok,
            message: None,
            message_params: None,
        }
    } else {
        RuleEvaluation {
            rule_id: rule_config.id.clone(),
            status: RuleStatus::Error,
            message: Some("rule_evidence.error.RV-04".to_string()),
            message_params: Some(json!({
                "numeric_fields": format!("{:?}", numeric_fields),
                "invalid_artifacts": format!("{:?}", invalid_artifacts),
            })),
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

    fn make_rule(id: &str) -> VerificationRule {
        VerificationRule {
            id: id.to_string(),
            severity: "OBLIGATORIA".to_string(),
            params: json!({}),
        }
    }

    /// TC-UNI-MOT-04: RV-04 caso base — campos numéricos válidos (>= 0).
    /// Each Choice: cubre el resultado OK para integridad de campos numéricos.
    #[test]
    fn tc_uni_mot_04_rv04_all_fields_valid_returns_ok() {
        let artifacts = vec![
            make_artifact("T-001", "TAREA", json!({"effort": 5, "estimation": 10})),
            make_artifact("T-002", "TAREA", json!({"effort": 0, "estimation": 0})),
        ];
        let rule = make_rule("RV-04");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Ok);
    }

    #[test]
    fn float_values_are_accepted() {
        let artifacts = vec![make_artifact("T-001", "TAREA", json!({"effort": 2.5, "estimation": 3.75}))];
        let result = evaluate(&artifacts, &make_rule("RV-04"));
        assert_eq!(result.status, RuleStatus::Ok);
    }

    #[test]
    fn negative_value_returns_error() {
        let artifacts = vec![make_artifact("T-001", "TAREA", json!({"effort": -1, "estimation": 5}))];
        let result = evaluate(&artifacts, &make_rule("RV-04"));
        assert_eq!(result.status, RuleStatus::Error);
        let msg = result.message.unwrap();
        assert_eq!(msg, "rule_evidence.error.RV-04");
        let params = result.message_params.unwrap();
        assert!(params["invalid_artifacts"].as_str().unwrap().contains("T-001"));
    }

    #[test]
    fn missing_field_returns_error() {
        let artifacts = vec![make_artifact("T-001", "TAREA", json!({"effort": 3}))];
        let result = evaluate(&artifacts, &make_rule("RV-04"));
        assert_eq!(result.status, RuleStatus::Error);
    }

    #[test]
    fn null_field_returns_error() {
        let artifacts = vec![make_artifact("T-001", "TAREA", json!({"effort": null, "estimation": 5}))];
        let result = evaluate(&artifacts, &make_rule("RV-04"));
        assert_eq!(result.status, RuleStatus::Error);
    }

    #[test]
    fn no_tarea_artifacts_returns_ok() {
        let artifacts = vec![make_artifact("C-001", "CODIGO", json!({}))];
        let result = evaluate(&artifacts, &make_rule("RV-04"));
        assert_eq!(result.status, RuleStatus::Ok);
    }

    #[test]
    fn empty_artifacts_returns_no_evaluada() {
        let artifacts: Vec<Artifact> = vec![];
        let result = evaluate(&artifacts, &make_rule("RV-04"));
        assert_eq!(result.status, RuleStatus::NoEvaluada);
    }
}
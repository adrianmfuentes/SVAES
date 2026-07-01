use serde_json::json;
use crate::models::{Artifact, RuleEvaluation, RuleStatus, VerificationRule};

/// RV-06: Compara un atributo específico (como la versión) presente en los metadatos
/// de los artefactos con un valor global proporcionado en los parámetros de la regla.
///
/// # Parámetros
/// * `artifacts` - Slice de artefactos a verificar.
/// * `rule_config` - Configuración de la regla con parámetros:
///   - `artifact_type`: Tipo de artefacto a verificar (default: "DOCUMENTO").
///   - `attribute`: Nombre del campo en metadata a comparar (default: "version").
///   - `expected_value`: Valor esperado contra el cual comparar.
///
/// # Lógica
/// 1. Obtiene el tipo de artefacto, campo a verificar y valor esperado.
/// 2. Filtra artefactos por tipo.
/// 3. Por cada artefacto, obtiene el valor del campo en su metadata.
/// 4. Si el valor no coincide con el esperado, añade el ID a la lista de discrepancias.
/// 5. Retorna Error si hay discrepancias, Ok si todos coinciden.
///
/// # Retorno
/// `RuleEvaluation` con el estado correspondiente y IDs con valores discrepantes.
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
        .unwrap_or("DOCUMENTO");

    let attribute = rule_config.params
        .get("attribute")
        .and_then(|v| v.as_str())
        .unwrap_or("version");

    let expected_value = rule_config.params
        .get("expected_value")
        .and_then(|v| v.as_str())
        .unwrap_or("");

    if expected_value.is_empty() {
        // Without a configured expected_value there is nothing to compare against
        // - every document would mismatch by construction, which isn't a real
        // data problem, just a rule that hasn't been set up yet.
        return RuleEvaluation {
            rule_id: rule_config.id.clone(),
            status: RuleStatus::NoEvaluada,
            message: Some("rule_evidence.no_evaluada.RV-06.no_expected_value".to_string()),
            message_params: None,
        };
    }

    let target_artifacts: Vec<&Artifact> = artifacts
        .iter()
        .filter(|a| a.artifact_type == artifact_type)
        .collect();

    if target_artifacts.is_empty() {
        return RuleEvaluation {
            rule_id: rule_config.id.clone(),
            status: RuleStatus::NoEvaluada,
            message: Some("rule_evidence.no_evaluada.RV-06".to_string()),
            message_params: Some(json!({
                "artifact_type": artifact_type,
            })),
        };
    }

    let mismatched_artifacts: Vec<&str> = target_artifacts
        .iter()
        .filter(|a| {
            match a.metadata.get(attribute) {
                Some(val) => val.as_str() != Some(expected_value),
                None => true,
            }
        })
        .map(|a| a.id.as_str())
        .collect();

    if mismatched_artifacts.is_empty() {
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
            message: Some("rule_evidence.error.RV-06".to_string()),
            message_params: Some(json!({
                "attribute": attribute,
                "expected_value": expected_value,
                "mismatched_artifacts": format!("{:?}", mismatched_artifacts),
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

    /// TC-UNI-MOT-06: RV-06 caso base — todos los atributos de versión coinciden.
    /// Each Choice: cubre el resultado OK para coherencia de atributos.
    #[test]
    fn tc_uni_mot_06_rv06_all_versions_match_returns_ok() {
        let artifacts = vec![
            make_artifact("D-001", "DOCUMENTO", json!({"version": "2.0"})),
            make_artifact("D-002", "DOCUMENTO", json!({"version": "2.0"})),
        ];
        let rule = VerificationRule {
            id: "RV-06".to_string(),
            severity: "OBLIGATORIA".to_string(),
            params: json!({"expected_value": "2.0"}),
        };

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Ok);
        assert!(result.message.is_none());
    }

    #[test]
    fn no_expected_value_configured_returns_no_evaluada() {
        let artifacts = vec![make_artifact("D-001", "DOCUMENTO", json!({"version": "2.0"}))];
        let rule = VerificationRule {
            id: "RV-06".to_string(),
            severity: "OBLIGATORIA".to_string(),
            params: json!({}),
        };

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::NoEvaluada);
        assert_eq!(result.message.unwrap(), "rule_evidence.no_evaluada.RV-06.no_expected_value");
    }

    #[test]
    fn version_mismatch_returns_error() {
        let artifacts = vec![
            make_artifact("D-001", "DOCUMENTO", json!({"version": "2.0"})),
            make_artifact("D-002", "DOCUMENTO", json!({"version": "1.5"})),
        ];
        let rule = VerificationRule {
            id: "RV-06".to_string(),
            severity: "OBLIGATORIA".to_string(),
            params: json!({"expected_value": "2.0"}),
        };

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
        let msg = result.message.unwrap();
        assert_eq!(msg, "rule_evidence.error.RV-06");
        let params = result.message_params.unwrap();
        assert!(params["mismatched_artifacts"].as_str().unwrap().contains("D-002"));
    }

    #[test]
    fn missing_attribute_returns_error() {
        let artifacts = vec![make_artifact("D-001", "DOCUMENTO", json!({}))];
        let rule = VerificationRule {
            id: "RV-06".to_string(),
            severity: "OBLIGATORIA".to_string(),
            params: json!({"expected_value": "2.0"}),
        };

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
    }

    #[test]
    fn no_matching_artifacts_returns_no_evaluada() {
        let artifacts = vec![make_artifact("T-001", "TAREA", json!({"version": "wrong"}))];
        let rule = VerificationRule {
            id: "RV-06".to_string(),
            severity: "OBLIGATORIA".to_string(),
            params: json!({"expected_value": "2.0"}),
        };

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::NoEvaluada);
    }

    #[test]
    fn empty_artifacts_returns_no_evaluada() {
        let artifacts: Vec<Artifact> = vec![];
        let rule = VerificationRule {
            id: "RV-06".to_string(),
            severity: "OBLIGATORIA".to_string(),
            params: json!({"expected_value": "2.0"}),
        };
        let result = evaluate(&artifacts, &rule);
        assert_eq!(result.status, RuleStatus::NoEvaluada);
    }
}
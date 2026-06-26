use crate::models::{Artifact, RuleEvaluation, RuleStatus, VerificationRule};

/// has_duplicated_code: Verifica que ningún artefacto de código supere el umbral
/// de líneas duplicadas configurado.
///
/// # Parámetros (params)
/// - `artifact_type`: Tipo de artefacto a verificar (default: "CODIGO").
/// - `field`: Campo de metadata con el porcentaje de duplicación (default: "duplicated_lines_density").
/// - `threshold`: Umbral máximo permitido, inclusive (default: 3.0).
pub fn evaluate(artifacts: &[Artifact], rule_config: &VerificationRule) -> RuleEvaluation {
    let artifact_type = rule_config.params
        .get("artifact_type").and_then(|v| v.as_str()).unwrap_or("CODIGO");
    let field = rule_config.params
        .get("field").and_then(|v| v.as_str()).unwrap_or("duplicated_lines_density");
    let threshold = rule_config.params
        .get("threshold").and_then(|v| v.as_f64()).unwrap_or(3.0);

    let matching: Vec<_> = artifacts.iter().filter(|a| a.artifact_type == artifact_type).collect();
    if matching.is_empty() {
        return RuleEvaluation {
            rule_id: rule_config.id.clone(),
            status: RuleStatus::Warning,
            message: Some(format!("No se encontraron artefactos de tipo '{}' para evaluar", artifact_type)),
        };
    }

    let violations: Vec<String> = matching.iter()
        .filter_map(|a| {
            a.metadata.get(field).and_then(|v| v.as_f64())
                .filter(|&val| val > threshold)
                .map(|val| format!("'{}': {:.1}% > {:.1}%", a.id, val, threshold))
        })
        .collect();

    if violations.is_empty() {
        RuleEvaluation {
            rule_id: rule_config.id.clone(),
            status: RuleStatus::Ok,
            message: None,
        }
    } else {
        RuleEvaluation {
            rule_id: rule_config.id.clone(),
            status: RuleStatus::Error,
            message: Some(format!("Artefactos con código duplicado excesivo: {:?}", violations)),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn make_artifact(id: &str, metadata: serde_json::Value) -> Artifact {
        Artifact { id: id.to_string(), artifact_type: "CODIGO".to_string(), metadata }
    }

    fn make_rule(params: serde_json::Value) -> VerificationRule {
        VerificationRule { id: "has_duplicated_code".to_string(), severity: "OBLIGATORIA".to_string(), params }
    }

    #[test]
    fn no_duplication_returns_ok() {
        let artifacts = vec![make_artifact("C-001", json!({"duplicated_lines_density": 1.5}))];
        let result = evaluate(&artifacts, &make_rule(json!({})));
        assert_eq!(result.status, RuleStatus::Ok);
    }

    #[test]
    fn exceeds_threshold_returns_error() {
        let artifacts = vec![make_artifact("C-001", json!({"duplicated_lines_density": 5.0}))];
        let result = evaluate(&artifacts, &make_rule(json!({})));
        assert_eq!(result.status, RuleStatus::Error);
        assert!(result.message.unwrap().contains("C-001"));
    }

    #[test]
    fn custom_threshold_respected() {
        let artifacts = vec![make_artifact("C-001", json!({"duplicated_lines_density": 4.0}))];
        let result = evaluate(&artifacts, &make_rule(json!({"threshold": 5.0})));
        assert_eq!(result.status, RuleStatus::Ok);
    }

    #[test]
    fn no_matching_artifacts_returns_warning() {
        let artifacts = vec![];
        let result = evaluate(&artifacts, &make_rule(json!({})));
        assert_eq!(result.status, RuleStatus::Warning);
    }

    #[test]
    fn missing_field_in_metadata_treated_as_ok() {
        let artifacts = vec![make_artifact("C-001", json!({"other_field": 99.0}))];
        let result = evaluate(&artifacts, &make_rule(json!({})));
        assert_eq!(result.status, RuleStatus::Ok);
    }
}

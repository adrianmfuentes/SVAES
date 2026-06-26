use crate::models::{Artifact, RuleEvaluation, RuleStatus, VerificationRule};

/// has_open_high_priority_issues: Verifica que ningún artefacto supere el número
/// permitido de issues de alta prioridad abiertos.
///
/// # Parámetros (params)
/// - `artifact_type`: Tipo de artefacto (default: "TAREA").
/// - `field`: Campo de metadata (default: "open_issues").
/// - `threshold`: Número máximo permitido, inclusive (default: 0).
pub fn evaluate(artifacts: &[Artifact], rule_config: &VerificationRule) -> RuleEvaluation {
    let artifact_type = rule_config.params
        .get("artifact_type").and_then(|v| v.as_str()).unwrap_or("TAREA");
    let field = rule_config.params
        .get("field").and_then(|v| v.as_str()).unwrap_or("open_issues");
    let threshold = rule_config.params
        .get("threshold").and_then(|v| v.as_f64()).unwrap_or(0.0);

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
                .map(|val| format!("'{}': {} issues abiertos", a.id, val as u64))
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
            message: Some(format!("Artefactos con issues de alta prioridad abiertos: {:?}", violations)),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn make_artifact(id: &str, metadata: serde_json::Value) -> Artifact {
        Artifact { id: id.to_string(), artifact_type: "TAREA".to_string(), metadata }
    }

    fn make_rule(params: serde_json::Value) -> VerificationRule {
        VerificationRule { id: "has_open_high_priority_issues".to_string(), severity: "OBLIGATORIA".to_string(), params }
    }

    #[test]
    fn no_open_issues_returns_ok() {
        let artifacts = vec![make_artifact("T-001", json!({"open_issues": 0}))];
        let result = evaluate(&artifacts, &make_rule(json!({})));
        assert_eq!(result.status, RuleStatus::Ok);
    }

    #[test]
    fn issues_above_threshold_returns_error() {
        let artifacts = vec![make_artifact("T-001", json!({"open_issues": 2}))];
        let result = evaluate(&artifacts, &make_rule(json!({})));
        assert_eq!(result.status, RuleStatus::Error);
    }

    #[test]
    fn no_artifacts_returns_warning() {
        let result = evaluate(&[], &make_rule(json!({})));
        assert_eq!(result.status, RuleStatus::Warning);
    }
}

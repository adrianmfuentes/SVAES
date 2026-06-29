use crate::models::{Artifact, RuleEvaluation, RuleStatus, VerificationRule};
use serde_json::json;

/// has_blocking_issues: Verifica que ningún artefacto tenga issues bloqueantes
/// por encima del umbral permitido.
///
/// # Parámetros (params)
/// - `artifact_type`: Tipo de artefacto (default: "TAREA").
/// - `field`: Campo de metadata (default: "blocking_issues").
/// - `threshold`: Número máximo permitido, inclusive (default: 0).
pub fn evaluate(artifacts: &[Artifact], rule_config: &VerificationRule) -> RuleEvaluation {
    let artifact_type = rule_config.params
        .get("artifact_type").and_then(|v| v.as_str()).unwrap_or("TAREA");
    let field = rule_config.params
        .get("field").and_then(|v| v.as_str()).unwrap_or("blocking_issues");
    let threshold = rule_config.params
        .get("threshold").and_then(|v| v.as_f64()).unwrap_or(0.0);

    let matching: Vec<_> = artifacts.iter().filter(|a| a.artifact_type == artifact_type).collect();
    if matching.is_empty() {
        return RuleEvaluation {
            rule_id: rule_config.id.clone(),
            status: RuleStatus::NoEvaluada,
            message: Some("rule_evidence.no_evaluada.no_artifacts_of_type".to_string()),
            message_params: Some(json!({
                "artifact_type": artifact_type,
            })),
        };
    }

    let violations: Vec<String> = matching.iter()
        .filter_map(|a| {
            a.metadata.get(field).and_then(|v| v.as_f64())
                .filter(|&val| val > threshold)
                .map(|val| format!("'{}': {} issues bloqueantes", a.id, val as u64))
        })
        .collect();

    if violations.is_empty() {
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
            message: Some("rule_evidence.error.has_blocking_issues".to_string()),
            message_params: Some(json!({
                "violations": format!("{:?}", violations),
            })),
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
        VerificationRule { id: "has_blocking_issues".to_string(), severity: "OBLIGATORIA".to_string(), params }
    }

    #[test]
    fn no_blocking_issues_returns_ok() {
        let artifacts = vec![make_artifact("T-001", json!({"blocking_issues": 0}))];
        let result = evaluate(&artifacts, &make_rule(json!({})));
        assert_eq!(result.status, RuleStatus::Ok);
    }

    #[test]
    fn blocking_issues_above_threshold_returns_error() {
        let artifacts = vec![make_artifact("T-001", json!({"blocking_issues": 1}))];
        let result = evaluate(&artifacts, &make_rule(json!({})));
        assert_eq!(result.status, RuleStatus::Error);
    }

    #[test]
    fn no_artifacts_returns_no_evaluada() {
        let result = evaluate(&[], &make_rule(json!({})));
        assert_eq!(result.status, RuleStatus::NoEvaluada);
        assert_eq!(result.message.unwrap(), "rule_evidence.no_evaluada.no_artifacts_of_type");
        assert_eq!(result.message_params.unwrap()["artifact_type"].as_str().unwrap(), "TAREA");
    }
}

use crate::models::{Artifact, RuleEvaluation, RuleStatus, VerificationRule};

/// has_uncovered_code: Verifica que ningún artefacto supere el número
/// de líneas sin cobertura de tests permitido.
///
/// # Parámetros (params)
/// - `artifact_type`: Tipo de artefacto (default: "CODIGO").
/// - `field`: Campo de metadata con líneas sin cubrir (default: "uncovered_lines").
/// - `threshold`: Número máximo de líneas sin cubrir permitido, inclusive (default: 0).
pub fn evaluate(artifacts: &[Artifact], rule_config: &VerificationRule) -> RuleEvaluation {
    let artifact_type = rule_config.params
        .get("artifact_type").and_then(|v| v.as_str()).unwrap_or("CODIGO");
    let field = rule_config.params
        .get("field").and_then(|v| v.as_str()).unwrap_or("uncovered_lines");
    let threshold = rule_config.params
        .get("threshold").and_then(|v| v.as_f64()).unwrap_or(0.0);

    let matching: Vec<_> = artifacts.iter().filter(|a| a.artifact_type == artifact_type).collect();
    if matching.is_empty() {
        return RuleEvaluation {
            rule_id: rule_config.id.clone(),
            status: RuleStatus::NoEvaluada,
            message: Some(format!("No hay artefactos de tipo '{}' en la entrega — regla no aplicable", artifact_type)),
        };
    }

    let violations: Vec<String> = matching.iter()
        .filter_map(|a| {
            a.metadata.get(field).and_then(|v| v.as_f64())
                .filter(|&val| val > threshold)
                .map(|val| format!("'{}': {} líneas sin cobertura", a.id, val as u64))
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
            message: Some(format!("Artefactos con código sin cobertura: {:?}", violations)),
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
        VerificationRule { id: "has_uncovered_code".to_string(), severity: "OBLIGATORIA".to_string(), params }
    }

    #[test]
    fn fully_covered_returns_ok() {
        let artifacts = vec![make_artifact("C-001", json!({"uncovered_lines": 0}))];
        let result = evaluate(&artifacts, &make_rule(json!({})));
        assert_eq!(result.status, RuleStatus::Ok);
    }

    #[test]
    fn uncovered_above_threshold_returns_error() {
        let artifacts = vec![make_artifact("C-001", json!({"uncovered_lines": 10}))];
        let result = evaluate(&artifacts, &make_rule(json!({})));
        assert_eq!(result.status, RuleStatus::Error);
    }

    #[test]
    fn custom_threshold_allows_some_uncovered() {
        let artifacts = vec![make_artifact("C-001", json!({"uncovered_lines": 5}))];
        let result = evaluate(&artifacts, &make_rule(json!({"threshold": 10})));
        assert_eq!(result.status, RuleStatus::Ok);
    }

    #[test]
    fn no_artifacts_returns_no_evaluada() {
        let result = evaluate(&[], &make_rule(json!({})));
        assert_eq!(result.status, RuleStatus::NoEvaluada);
    }
}

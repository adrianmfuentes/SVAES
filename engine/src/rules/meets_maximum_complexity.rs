use crate::models::{Artifact, RuleEvaluation, RuleStatus, VerificationRule};

/// meets_maximum_complexity: Verifica que todos los artefactos de código
/// no superen la complejidad ciclomática máxima configurada.
///
/// # Parámetros (params)
/// - `artifact_type`: Tipo de artefacto (default: "CODIGO").
/// - `field`: Campo de metadata con la complejidad (default: "complexity").
/// - `max_complexity`: Complejidad máxima permitida, inclusive (default: 10.0).
pub fn evaluate(artifacts: &[Artifact], rule_config: &VerificationRule) -> RuleEvaluation {
    let artifact_type = rule_config.params
        .get("artifact_type").and_then(|v| v.as_str()).unwrap_or("CODIGO");
    let field = rule_config.params
        .get("field").and_then(|v| v.as_str()).unwrap_or("complexity");
    let max_complexity = rule_config.params
        .get("max_complexity").and_then(|v| v.as_f64()).unwrap_or(10.0);

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
                .filter(|&val| val > max_complexity)
                .map(|val| format!("'{}': {:.0} > {:.0} máximo", a.id, val, max_complexity))
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
            message: Some(format!("Artefactos que superan la complejidad máxima: {:?}", violations)),
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
        VerificationRule { id: "meets_maximum_complexity".to_string(), severity: "OBLIGATORIA".to_string(), params }
    }

    #[test]
    fn complexity_within_limit_returns_ok() {
        let artifacts = vec![make_artifact("C-001", json!({"complexity": 8.0}))];
        let result = evaluate(&artifacts, &make_rule(json!({})));
        assert_eq!(result.status, RuleStatus::Ok);
    }

    #[test]
    fn complexity_exactly_at_limit_returns_ok() {
        let artifacts = vec![make_artifact("C-001", json!({"complexity": 10.0}))];
        let result = evaluate(&artifacts, &make_rule(json!({})));
        assert_eq!(result.status, RuleStatus::Ok);
    }

    #[test]
    fn complexity_above_limit_returns_error() {
        let artifacts = vec![make_artifact("C-001", json!({"complexity": 15.0}))];
        let result = evaluate(&artifacts, &make_rule(json!({})));
        assert_eq!(result.status, RuleStatus::Error);
        assert!(result.message.unwrap().contains("C-001"));
    }

    #[test]
    fn custom_max_complexity_respected() {
        let artifacts = vec![make_artifact("C-001", json!({"complexity": 20.0}))];
        let result = evaluate(&artifacts, &make_rule(json!({"max_complexity": 25.0})));
        assert_eq!(result.status, RuleStatus::Ok);
    }

    #[test]
    fn no_artifacts_returns_warning() {
        let result = evaluate(&[], &make_rule(json!({})));
        assert_eq!(result.status, RuleStatus::Warning);
    }

    #[test]
    fn missing_complexity_field_treated_as_ok() {
        let artifacts = vec![make_artifact("C-001", json!({"other": 50.0}))];
        let result = evaluate(&artifacts, &make_rule(json!({})));
        assert_eq!(result.status, RuleStatus::Ok);
    }
}

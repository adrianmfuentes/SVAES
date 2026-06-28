use crate::models::{Artifact, RuleEvaluation, RuleStatus, VerificationRule};

/// meets_minimum_test_coverage: Verifica que todos los artefactos de código
/// alcancen el porcentaje mínimo de cobertura de tests configurado.
///
/// # Parámetros (params)
/// - `artifact_type`: Tipo de artefacto (default: "CODIGO").
/// - `field`: Campo de metadata con el porcentaje de cobertura (default: "coverage").
/// - `min_coverage`: Cobertura mínima requerida en porcentaje (default: 80.0).
pub fn evaluate(artifacts: &[Artifact], rule_config: &VerificationRule) -> RuleEvaluation {
    let artifact_type = rule_config.params
        .get("artifact_type").and_then(|v| v.as_str()).unwrap_or("CODIGO");
    let field = rule_config.params
        .get("field").and_then(|v| v.as_str()).unwrap_or("coverage");
    let min_coverage = rule_config.params
        .get("min_coverage").and_then(|v| v.as_f64()).unwrap_or(80.0);

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
                .filter(|&val| val < min_coverage)
                .map(|val| format!("'{}': {:.1}% < {:.1}% mínimo", a.id, val, min_coverage))
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
            message: Some(format!("Artefactos que no alcanzan la cobertura mínima: {:?}", violations)),
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
        VerificationRule { id: "meets_minimum_test_coverage".to_string(), severity: "OBLIGATORIA".to_string(), params }
    }

    #[test]
    fn coverage_above_minimum_returns_ok() {
        let artifacts = vec![make_artifact("C-001", json!({"coverage": 85.0}))];
        let result = evaluate(&artifacts, &make_rule(json!({})));
        assert_eq!(result.status, RuleStatus::Ok);
    }

    #[test]
    fn coverage_exactly_at_minimum_returns_ok() {
        let artifacts = vec![make_artifact("C-001", json!({"coverage": 80.0}))];
        let result = evaluate(&artifacts, &make_rule(json!({})));
        assert_eq!(result.status, RuleStatus::Ok);
    }

    #[test]
    fn coverage_below_minimum_returns_error() {
        let artifacts = vec![make_artifact("C-001", json!({"coverage": 70.0}))];
        let result = evaluate(&artifacts, &make_rule(json!({})));
        assert_eq!(result.status, RuleStatus::Error);
        assert!(result.message.unwrap().contains("C-001"));
    }

    #[test]
    fn custom_min_coverage_respected() {
        let artifacts = vec![make_artifact("C-001", json!({"coverage": 60.0}))];
        let result = evaluate(&artifacts, &make_rule(json!({"min_coverage": 50.0})));
        assert_eq!(result.status, RuleStatus::Ok);
    }

    #[test]
    fn no_artifacts_returns_no_evaluada() {
        let result = evaluate(&[], &make_rule(json!({})));
        assert_eq!(result.status, RuleStatus::NoEvaluada);
    }

    #[test]
    fn missing_coverage_field_treated_as_ok() {
        let artifacts = vec![make_artifact("C-001", json!({"other": 50.0}))];
        let result = evaluate(&artifacts, &make_rule(json!({})));
        assert_eq!(result.status, RuleStatus::Ok);
    }
}

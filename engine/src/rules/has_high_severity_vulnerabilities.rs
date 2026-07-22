use crate::models::{Artifact, RuleEvaluation, RuleStatus, VerificationRule};
use serde_json::json;

/// has_high_severity_vulnerabilities: Verifica que ningún artefacto de código
/// supere el número máximo de vulnerabilidades de alta severidad permitidas.
///
/// # Parámetros (params)
/// - `artifact_type`: Tipo de artefacto (default: "CODIGO").
/// - `field`: Campo de metadata con el contador (default: "vulnerabilities").
/// - `threshold`: Número máximo permitido, inclusive (default: 0).
pub fn evaluate(artifacts: &[Artifact], rule_config: &VerificationRule) -> RuleEvaluation {
    let artifact_type = rule_config.params
        .get("artifact_type").and_then(|v| v.as_str()).unwrap_or("CODIGO");
    let field = rule_config.params
        .get("field").and_then(|v| v.as_str()).unwrap_or("vulnerabilities");
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

    // Un campo ausente o con un tipo no numérico no es "cero vulnerabilidades":
    // es un dato que el conector no reportó o reportó mal - se trata como
    // violación (falla cerrado) en lugar de excluir el artefacto en silencio.
    let violations: Vec<String> = matching.iter()
        .filter_map(|a| match a.metadata.get(field).and_then(|v| v.as_f64()) {
            Some(val) if val > threshold => Some(format!("'{}': {} vulnerabilidades", a.id, val as u64)),
            Some(_) => None,
            None => Some(format!("'{}': campo '{}' ausente o con formato inválido", a.id, field)),
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
            message: Some("rule_evidence.error.has_high_severity_vulnerabilities".to_string()),
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
        Artifact { id: id.to_string(), artifact_type: "CODIGO".to_string(), metadata }
    }

    fn make_rule(params: serde_json::Value) -> VerificationRule {
        VerificationRule { id: "has_high_severity_vulnerabilities".to_string(), severity: "OBLIGATORIA".to_string(), params }
    }

    #[test]
    fn zero_vulnerabilities_returns_ok() {
        let artifacts = vec![make_artifact("C-001", json!({"vulnerabilities": 0}))];
        let result = evaluate(&artifacts, &make_rule(json!({})));
        assert_eq!(result.status, RuleStatus::Ok);
    }

    #[test]
    fn vulnerabilities_above_threshold_returns_error() {
        let artifacts = vec![make_artifact("C-001", json!({"vulnerabilities": 3}))];
        let result = evaluate(&artifacts, &make_rule(json!({})));
        assert_eq!(result.status, RuleStatus::Error);
        assert_eq!(result.message.unwrap(), "rule_evidence.error.has_high_severity_vulnerabilities");
        assert!(result.message_params.unwrap()["violations"].as_str().unwrap().contains("C-001"));
    }

    #[test]
    fn custom_threshold_respected() {
        let artifacts = vec![make_artifact("C-001", json!({"vulnerabilities": 2}))];
        let result = evaluate(&artifacts, &make_rule(json!({"threshold": 5})));
        assert_eq!(result.status, RuleStatus::Ok);
    }

    #[test]
    fn no_artifacts_returns_no_evaluada() {
        let result = evaluate(&[], &make_rule(json!({})));
        assert_eq!(result.status, RuleStatus::NoEvaluada);
        assert_eq!(result.message.unwrap(), "rule_evidence.no_evaluada.no_artifacts_of_type");
        assert_eq!(result.message_params.unwrap()["artifact_type"].as_str().unwrap(), "CODIGO");
    }
}

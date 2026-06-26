use crate::models::{Artifact, RuleEvaluation, RuleStatus, VerificationRule};

/// has_security_hotspots: Verifica que ningún artefacto supere el número
/// permitido de security hotspots sin revisar.
///
/// # Parámetros (params)
/// - `artifact_type`: Tipo de artefacto (default: "CODIGO").
/// - `field`: Campo de metadata (default: "security_hotspots").
/// - `threshold`: Número máximo permitido, inclusive (default: 0).
pub fn evaluate(artifacts: &[Artifact], rule_config: &VerificationRule) -> RuleEvaluation {
    let artifact_type = rule_config.params
        .get("artifact_type").and_then(|v| v.as_str()).unwrap_or("CODIGO");
    let field = rule_config.params
        .get("field").and_then(|v| v.as_str()).unwrap_or("security_hotspots");
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
                .map(|val| format!("'{}': {} hotspots de seguridad", a.id, val as u64))
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
            message: Some(format!("Artefactos con hotspots de seguridad sin revisar: {:?}", violations)),
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
        VerificationRule { id: "has_security_hotspots".to_string(), severity: "OBLIGATORIA".to_string(), params }
    }

    #[test]
    fn no_hotspots_returns_ok() {
        let artifacts = vec![make_artifact("C-001", json!({"security_hotspots": 0}))];
        let result = evaluate(&artifacts, &make_rule(json!({})));
        assert_eq!(result.status, RuleStatus::Ok);
    }

    #[test]
    fn hotspots_above_threshold_returns_error() {
        let artifacts = vec![make_artifact("C-001", json!({"security_hotspots": 1}))];
        let result = evaluate(&artifacts, &make_rule(json!({})));
        assert_eq!(result.status, RuleStatus::Error);
    }

    #[test]
    fn no_artifacts_returns_warning() {
        let result = evaluate(&[], &make_rule(json!({})));
        assert_eq!(result.status, RuleStatus::Warning);
    }
}

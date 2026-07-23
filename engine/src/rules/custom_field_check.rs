use crate::models::{Artifact, RuleEvaluation, RuleStatus, VerificationRule};
use serde_json::{json, Value};

/// custom_field_check: regla genérica y declarativa que evalúa una condición
/// sobre un campo de metadata de los artefactos de un tipo dado. Permite a un
/// manager definir reglas propias de su organización (p. ej. "todo artefacto
/// TAREA debe tener 'epic_id' no vacío") sin necesidad de implementar y
/// desplegar una nueva regla Rust por cada condición.
///
/// # Parámetros (params)
/// - `artifact_type`: Tipo de artefacto a comprobar (obligatorio).
/// - `field`: Nombre del campo de metadata a evaluar (obligatorio).
/// - `operator`: uno de `non_empty`, `equals`, `not_equals`, `contains`,
///   `gt`, `gte`, `lt`, `lte` (default: `non_empty`).
/// - `value`: valor de comparación, requerido por todos los operadores salvo
///   `non_empty`.
pub fn evaluate(artifacts: &[Artifact], rule_config: &VerificationRule) -> RuleEvaluation {
    let artifact_type = rule_config.params.get("artifact_type").and_then(|v| v.as_str());
    let field = rule_config.params.get("field").and_then(|v| v.as_str());
    let operator = rule_config.params.get("operator").and_then(|v| v.as_str()).unwrap_or("non_empty");
    let expected = rule_config.params.get("value");

    let (artifact_type, field) = match (artifact_type, field) {
        (Some(at), Some(f)) if !at.is_empty() && !f.is_empty() => (at, f),
        _ => {
            return RuleEvaluation {
                rule_id: rule_config.id.clone(),
                status: RuleStatus::NoEvaluada,
                message: Some("rule_evidence.no_evaluada.custom_field_check_misconfigured".to_string()),
                message_params: None,
            };
        }
    };

    let matching: Vec<_> = artifacts.iter().filter(|a| a.artifact_type == artifact_type).collect();
    if matching.is_empty() {
        return RuleEvaluation {
            rule_id: rule_config.id.clone(),
            status: RuleStatus::NoEvaluada,
            message: Some("rule_evidence.no_evaluada.no_artifacts_of_type".to_string()),
            message_params: Some(json!({ "artifact_type": artifact_type })),
        };
    }

    let violations: Vec<String> = matching.iter()
        .filter(|a| !field_matches(a.metadata.get(field), operator, expected))
        .map(|a| format!("'{}'", a.id))
        .collect();

    if violations.is_empty() {
        RuleEvaluation {
            rule_id: rule_config.id.clone(),
            status: RuleStatus::Ok,
            message: Some("rule_evidence.ok.custom_field_check".to_string()),
            message_params: None,
        }
    } else {
        RuleEvaluation {
            rule_id: rule_config.id.clone(),
            status: RuleStatus::Error,
            message: Some("rule_evidence.error.custom_field_check".to_string()),
            message_params: Some(json!({
                "field": field,
                "operator": operator,
                "violations": format!("{:?}", violations),
            })),
        }
    }
}

/// Compara el valor de un campo de metadata contra `expected` según `operator`.
/// Un campo ausente o `null` nunca satisface una condición (falla cerrado),
/// salvo para `non_empty` donde eso es precisamente lo que se comprueba.
fn field_matches(actual: Option<&Value>, operator: &str, expected: Option<&Value>) -> bool {
    if operator == "non_empty" {
        return is_non_empty(actual);
    }
    let actual = match actual {
        Some(v) if !v.is_null() => v,
        _ => return false,
    };
    match operator {
        "equals" => Some(actual) == expected,
        "not_equals" => Some(actual) != expected,
        "contains" => match (actual.as_str(), expected.and_then(|v| v.as_str())) {
            (Some(a), Some(e)) => a.contains(e),
            _ => false,
        },
        "gt" | "gte" | "lt" | "lte" => match (actual.as_f64(), expected.and_then(|v| v.as_f64())) {
            (Some(a), Some(e)) => match operator {
                "gt" => a > e,
                "gte" => a >= e,
                "lt" => a < e,
                _ => a <= e,
            },
            _ => false,
        },
        _ => false,
    }
}

fn is_non_empty(value: Option<&Value>) -> bool {
    match value {
        None | Some(Value::Null) => false,
        Some(Value::String(s)) => !s.trim().is_empty(),
        Some(Value::Array(a)) => !a.is_empty(),
        Some(Value::Object(o)) => !o.is_empty(),
        Some(_) => true,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn make_artifact(id: &str, artifact_type: &str, metadata: serde_json::Value) -> Artifact {
        Artifact { id: id.to_string(), artifact_type: artifact_type.to_string(), metadata }
    }

    fn make_rule(params: serde_json::Value) -> VerificationRule {
        VerificationRule { id: "custom_field_check".to_string(), severity: "OBLIGATORIA".to_string(), params }
    }

    #[test]
    fn non_empty_field_present_returns_ok() {
        let artifacts = vec![make_artifact("T-001", "TAREA", json!({"epic_id": "EPIC-1"}))];
        let rule = make_rule(json!({"artifact_type": "TAREA", "field": "epic_id"}));
        let result = evaluate(&artifacts, &rule);
        assert_eq!(result.status, RuleStatus::Ok);
    }

    #[test]
    fn non_empty_field_missing_returns_error() {
        let artifacts = vec![make_artifact("T-001", "TAREA", json!({}))];
        let rule = make_rule(json!({"artifact_type": "TAREA", "field": "epic_id"}));
        let result = evaluate(&artifacts, &rule);
        assert_eq!(result.status, RuleStatus::Error);
        assert_eq!(result.message.unwrap(), "rule_evidence.error.custom_field_check");
    }

    #[test]
    fn equals_operator_matching_value_returns_ok() {
        let artifacts = vec![make_artifact("D-001", "DOCUMENTO", json!({"status": "APPROVED"}))];
        let rule = make_rule(json!({"artifact_type": "DOCUMENTO", "field": "status", "operator": "equals", "value": "APPROVED"}));
        let result = evaluate(&artifacts, &rule);
        assert_eq!(result.status, RuleStatus::Ok);
    }

    #[test]
    fn equals_operator_mismatched_value_returns_error() {
        let artifacts = vec![make_artifact("D-001", "DOCUMENTO", json!({"status": "DRAFT"}))];
        let rule = make_rule(json!({"artifact_type": "DOCUMENTO", "field": "status", "operator": "equals", "value": "APPROVED"}));
        let result = evaluate(&artifacts, &rule);
        assert_eq!(result.status, RuleStatus::Error);
    }

    #[test]
    fn gte_operator_numeric_comparison() {
        let artifacts = vec![
            make_artifact("C-001", "CODIGO", json!({"coverage": 85.0})),
            make_artifact("C-002", "CODIGO", json!({"coverage": 40.0})),
        ];
        let rule = make_rule(json!({"artifact_type": "CODIGO", "field": "coverage", "operator": "gte", "value": 80}));
        let result = evaluate(&artifacts, &rule);
        assert_eq!(result.status, RuleStatus::Error);
        assert!(result.message_params.unwrap()["violations"].as_str().unwrap().contains("C-002"));
    }

    #[test]
    fn contains_operator_substring_match() {
        let artifacts = vec![make_artifact("C-001", "CODIGO", json!({"branch": "feature/svaes-123"}))];
        let rule = make_rule(json!({"artifact_type": "CODIGO", "field": "branch", "operator": "contains", "value": "svaes-"}));
        let result = evaluate(&artifacts, &rule);
        assert_eq!(result.status, RuleStatus::Ok);
    }

    #[test]
    fn no_artifacts_of_type_returns_no_evaluada() {
        let rule = make_rule(json!({"artifact_type": "TAREA", "field": "epic_id"}));
        let result = evaluate(&[], &rule);
        assert_eq!(result.status, RuleStatus::NoEvaluada);
        assert_eq!(result.message.unwrap(), "rule_evidence.no_evaluada.no_artifacts_of_type");
    }

    #[test]
    fn missing_field_or_artifact_type_param_returns_no_evaluada() {
        let artifacts = vec![make_artifact("T-001", "TAREA", json!({"epic_id": "EPIC-1"}))];
        let result = evaluate(&artifacts, &make_rule(json!({"artifact_type": "TAREA"})));
        assert_eq!(result.status, RuleStatus::NoEvaluada);
        assert_eq!(result.message.unwrap(), "rule_evidence.no_evaluada.custom_field_check_misconfigured");
    }

    #[test]
    fn unknown_operator_is_fail_closed() {
        let artifacts = vec![make_artifact("T-001", "TAREA", json!({"epic_id": "EPIC-1"}))];
        let rule = make_rule(json!({"artifact_type": "TAREA", "field": "epic_id", "operator": "bogus", "value": "x"}));
        let result = evaluate(&artifacts, &rule);
        assert_eq!(result.status, RuleStatus::Error);
    }
}

use crate::models::{Artifact, RuleEvaluation, RuleStatus, VerificationRule};

/// RV-03: Comprueba que todos los artefactos de un tipo específico coincidan
/// con un valor de "estado" permitido definido en los parámetros de la regla.
///
/// # Parámetros
/// * `artifacts` - Slice de artefactos a verificar.
/// * `rule_config` - Configuración de la regla con parámetros:
///   - `artifact_type`: Tipo de artefacto a filtrar (default: "TAREA").
///   - `allowed_states`: Array de strings con los estados válidos (default: ["DONE", "CLOSED"]).
///   - `status_field`: Nombre del campo en metadata que contiene el estado (default: "status").
///
/// # Lógica
/// 1. Obtiene el tipo de artefacto a verificar (default: "TAREA").
/// 2. Obtiene la lista de estados permitidos desde los parámetros (default: ["DONE", "CLOSED"]).
/// 3. Filtra los artefactos por tipo y verifica que cada uno tenga un estado permitido.
/// 4. Si algún artefacto tiene estado no permitido o campo ausente, retorna Error.
/// 5. Si todos los estados son válidos, retorna Ok.
///
/// # Retorno
/// `RuleEvaluation` con el estado correspondiente y mensaje detallado si hay estados inválidos.
pub fn evaluate(artifacts: &[Artifact], rule_config: &VerificationRule) -> RuleEvaluation {
    let artifact_type = rule_config.params
        .get("artifact_type")
        .and_then(|v| v.as_str())
        .unwrap_or("TAREA");

    let allowed_states: Vec<&str> = rule_config.params
        .get("allowed_states")
        .and_then(|v| v.as_array())
        .map(|arr| arr.iter().filter_map(|v| v.as_str()).collect())
        .unwrap_or_else(|| vec!["DONE", "CLOSED"]);

    let status_field = rule_config.params
        .get("status_field")
        .and_then(|v| v.as_str())
        .unwrap_or("status");

    let invalid_artifacts: Vec<&str> = artifacts
        .iter()
        .filter(|a| a.artifact_type == artifact_type)
        .filter(|a| {
            match a.metadata.get(status_field) {
                Some(val) => {
                    match val.as_str() {
                        Some(state) => !allowed_states.contains(&state),
                        None => true,
                    }
                }
                None => true,
            }
        })
        .map(|a| a.id.as_str())
        .collect();

    if invalid_artifacts.is_empty() {
        RuleEvaluation {
            rule_id: rule_config.id.clone(),
            status: RuleStatus::Ok,
            message: None,
        }
    } else {
        RuleEvaluation {
            rule_id: rule_config.id.clone(),
            status: RuleStatus::Error,
            message: Some(format!(
                "Artefactos con estado inválido (permitidos: {:?}): {:?}",
                allowed_states,
                invalid_artifacts
            )),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn make_artifact(id: &str, artifact_type: &str, status: &str) -> Artifact {
        Artifact {
            id: id.to_string(),
            artifact_type: artifact_type.to_string(),
            metadata: json!({"status": status}),
        }
    }

    fn make_rule(id: &str, params: serde_json::Value) -> VerificationRule {
        VerificationRule {
            id: id.to_string(),
            severity: "OBLIGATORIA".to_string(),
            params,
        }
    }

    #[test]
    fn rv03_all_states_valid_returns_ok() {
        let artifacts = vec![
            make_artifact("T-001", "TAREA", "DONE"),
            make_artifact("T-002", "TAREA", "CLOSED"),
        ];
        let rule = make_rule("RV-03", json!({"allowed_states": ["DONE", "CLOSED"]}));

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Ok);
        assert!(result.message.is_none());
    }

    #[test]
    fn rv03_invalid_state_returns_error() {
        let artifacts = vec![
            make_artifact("T-001", "TAREA", "DONE"),
            make_artifact("T-002", "TAREA", "IN_PROGRESS"),
        ];
        let rule = make_rule("RV-03", json!({"allowed_states": ["DONE", "CLOSED"]}));

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
        let msg = result.message.unwrap();
        assert!(msg.contains("T-002"));
    }

    #[test]
    fn rv03_missing_status_field_returns_error() {
        let artifacts = vec![
            make_artifact("T-001", "TAREA", "DONE"),
            make_artifact("T-002", "TAREA", "IN_PROGRESS"),
        ];
        let rule = make_rule("RV-03", json!({
            "artifact_type": "TAREA",
            "allowed_states": ["DONE", "CLOSED"],
            "status_field": "workflow_status"
        }));

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
        let msg = result.message.unwrap();
        assert!(msg.contains("T-001") && msg.contains("T-002"));
    }

    #[test]
    fn rv03_no_artifacts_of_type_returns_ok() {
        let artifacts = vec![
            make_artifact("C-001", "CÓDIGO", "COMMIT"),
        ];
        let rule = make_rule("RV-03", json!({}));

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Ok);
    }

    #[test]
    fn rv03_custom_artifact_type() {
        let artifacts = vec![
            make_artifact("D-001", "DOCUMENTO", "FINALIZADO"),
            make_artifact("D-002", "DOCUMENTO", "BORRADOR"),
        ];
        let rule = make_rule("RV-03", json!({
            "artifact_type": "DOCUMENTO",
            "allowed_states": ["FINALIZADO"],
        }));

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
        assert!(result.message.unwrap().contains("D-002"));
    }
}
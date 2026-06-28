use crate::models::{Artifact, RuleEvaluation, RuleStatus, VerificationRule};

/// RV-07: Confirma la presencia de un artefacto específico que actúe como "marcador"
/// de que la operación ha sido registrada en herramientas externas de gestión.
///
/// # Parámetros
/// * `artifacts` - Slice de artefactos a verificar.
/// * `rule_config` - Configuración de la regla con parámetros:
///   - `artifact_type`: Tipo de artefacto marcador a buscar. OBLIGATORIO — si no se
///     proporciona, la regla devuelve `NoEvaluada` porque no hay tipo concreto que buscar.
///   - `marker_field`: Campo en metadata que indica registro externo (default: "external_registered").
///
/// # Lógica
/// 1. Si `artifact_type` no está configurado, devuelve NoEvaluada (regla no aplicable sin config).
/// 2. Busca un artefacto del tipo especificado.
/// 3. Si no existe, devuelve Error.
/// 4. Si existe, verifica que el campo marker sea `true`; si no, Error.
///
/// # Retorno
/// `RuleEvaluation` con el estado correspondiente indicando si el marcador fue encontrado.
pub fn evaluate(artifacts: &[Artifact], rule_config: &VerificationRule) -> RuleEvaluation {
    let artifact_type = match rule_config.params
        .get("artifact_type")
        .and_then(|v| v.as_str())
    {
        Some(t) => t,
        None => {
            return RuleEvaluation {
                rule_id: rule_config.id.clone(),
                status: RuleStatus::NoEvaluada,
                message: Some(
                    "Parámetro 'artifact_type' no configurado — regla no aplicable".to_string(),
                ),
            };
        }
    };

    let marker_field = rule_config.params
        .get("marker_field")
        .and_then(|v| v.as_str())
        .unwrap_or("external_registered");

    let marker_artifact = artifacts
        .iter()
        .find(|a| a.artifact_type == artifact_type);

    match marker_artifact {
        Some(artifact) => {
            match artifact.metadata.get(marker_field) {
                Some(val) if val.as_bool() == Some(true) => {
                    RuleEvaluation {
                        rule_id: rule_config.id.clone(),
                        status: RuleStatus::Ok,
                        message: Some(format!(
                            "Marcador de registro externo '{}' encontrado en artefacto '{}'",
                            artifact_type,
                            artifact.id
                        )),
                    }
                }
                _ => {
                    RuleEvaluation {
                        rule_id: rule_config.id.clone(),
                        status: RuleStatus::Error,
                        message: Some(format!(
                            "Artefacto '{}' de tipo '{}' encontrado pero '{}' no es true",
                            artifact.id,
                            artifact_type,
                            marker_field
                        )),
                    }
                }
            }
        }
        None => {
            RuleEvaluation {
                rule_id: rule_config.id.clone(),
                status: RuleStatus::Error,
                message: Some(format!(
                    "No se encontró artefacto marcador de tipo '{}' que indique registro externo",
                    artifact_type
                )),
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn make_artifact(id: &str, artifact_type: &str, metadata: serde_json::Value) -> Artifact {
        Artifact {
            id: id.to_string(),
            artifact_type: artifact_type.to_string(),
            metadata,
        }
    }

    fn make_rule_with_type(id: &str, artifact_type: &str) -> VerificationRule {
        VerificationRule {
            id: id.to_string(),
            severity: "OBLIGATORIA".to_string(),
            params: json!({"artifact_type": artifact_type}),
        }
    }

    fn make_rule_no_params(id: &str) -> VerificationRule {
        VerificationRule {
            id: id.to_string(),
            severity: "OBLIGATORIA".to_string(),
            params: json!({}),
        }
    }

    /// TC-UNI-MOT-07: RV-07 caso base — marcador de registro externo encontrado.
    /// Each Choice: cubre el resultado OK para registro externo.
    #[test]
    fn tc_uni_mot_07_rv07_marker_found_returns_ok() {
        let artifacts = vec![
            make_artifact("T-001", "TAREA", json!({"external_registered": true})),
        ];
        let rule = make_rule_with_type("RV-07", "TAREA");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Ok);
        assert!(result.message.is_some());
    }

    #[test]
    fn no_artifact_type_param_returns_no_evaluada() {
        let artifacts = vec![
            make_artifact("T-001", "TAREA", json!({"external_registered": true})),
        ];
        let rule = make_rule_no_params("RV-07");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::NoEvaluada);
    }

    #[test]
    fn marker_artifact_not_found_returns_error() {
        let artifacts = vec![
            make_artifact("C-001", "CODIGO", json!({})),
        ];
        let rule = make_rule_with_type("RV-07", "TAREA");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
        let msg = result.message.unwrap();
        assert!(msg.contains("TAREA"));
    }

    #[test]
    fn marker_field_false_returns_error() {
        let artifacts = vec![
            make_artifact("T-001", "TAREA", json!({"external_registered": false})),
        ];
        let rule = make_rule_with_type("RV-07", "TAREA");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
        let msg = result.message.unwrap();
        assert!(msg.contains("T-001"));
    }

    #[test]
    fn marker_field_missing_returns_error() {
        let artifacts = vec![
            make_artifact("T-001", "TAREA", json!({"other_field": true})),
        ];
        let rule = make_rule_with_type("RV-07", "TAREA");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
    }
}

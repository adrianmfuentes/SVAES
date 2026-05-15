use crate::models::{Artifact, RuleEvaluation, RuleStatus, VerificationRule};

/// RV-10: Busca un artefacto de un tipo concreto que posea un atributo de estado
/// igual a "APROBADO" o "VALIDADO".
///
/// # Parámetros
/// * `artifacts` - Slice de artefactos a verificar.
/// * `rule_config` - Configuración de la regla con parámetros:
///   - `artifact_type`: Tipo de artefacto a buscar (default: "DOCUMENTO").
///   - `status_field`: Campo en metadata que contiene el estado (default: "status").
///   - `approved_states`: Array de estados que se consideran aprobados (default: ["APROBADO", "VALIDADO"]).
///
/// # Lógica
/// 1. Obtiene el tipo de artefacto, campo de estado y valores considerados como aprobados.
/// 2. Filtra los artefactos por tipo.
/// 3. Busca un artefacto cuyo campo de estado sea alguno de los valores aprobados.
/// 4. Si lo encuentra, retorna Ok; si no, retorna Error.
///
/// # Retorno
/// `RuleEvaluation` con el estado correspondiente indicando si se encontró el artefacto aprobado.
pub fn evaluate(artifacts: &[Artifact], rule_config: &VerificationRule) -> RuleEvaluation {
    let artifact_type = rule_config.params
        .get("artifact_type")
        .and_then(|v| v.as_str())
        .unwrap_or("DOCUMENTO");

    let status_field = rule_config.params
        .get("status_field")
        .and_then(|v| v.as_str())
        .unwrap_or("status");

    let approved_states: Vec<&str> = rule_config.params
        .get("approved_states")
        .and_then(|v| v.as_array())
        .map(|arr| arr.iter().filter_map(|v| v.as_str()).collect())
        .unwrap_or_else(|| vec!["APROBADO", "VALIDADO"]);

    let approved_artifact = artifacts
        .iter()
        .filter(|a| a.artifact_type == artifact_type)
        .find(|a| {
            match a.metadata.get(status_field) {
                Some(val) => val.as_str().map(|s| approved_states.contains(&s)).unwrap_or(false),
                None => false,
            }
        });

    match approved_artifact {
        Some(artifact) => {
            RuleEvaluation {
                rule_id: rule_config.id.clone(),
                status: RuleStatus::Ok,
                message: Some(format!(
                    "Artefacto '{}' de tipo '{}' encontrado con estado aprobatorio: '{}'",
                    artifact.id,
                    artifact_type,
                    artifact.metadata.get(status_field).and_then(|v| v.as_str()).unwrap_or("desconocido")
                )),
            }
        }
        None => {
            RuleEvaluation {
                rule_id: rule_config.id.clone(),
                status: RuleStatus::Error,
                message: Some(format!(
                    "No se encontró artefacto de tipo '{}' con estado aprobatorio (estados aceptados: {:?})",
                    artifact_type,
                    approved_states
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

    fn make_rule(id: &str) -> VerificationRule {
        VerificationRule {
            id: id.to_string(),
            severity: "OBLIGATORIA".to_string(),
            params: json!({}),
        }
    }

    #[test]
    fn rv10_approved_document_returns_ok() {
        let artifacts = vec![
            make_artifact("D-001", "DOCUMENTO", json!({"status": "APROBADO"})),
        ];
        let rule = make_rule("RV-10");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Ok);
        let msg = result.message.unwrap();
        assert!(msg.contains("D-001") && msg.contains("APROBADO"));
    }

    #[test]
    fn rv10_validated_document_returns_ok() {
        let artifacts = vec![
            make_artifact("D-001", "DOCUMENTO", json!({"status": "VALIDADO"})),
        ];
        let rule = make_rule("RV-10");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Ok);
    }

    #[test]
    fn rv10_non_approved_status_returns_error() {
        let artifacts = vec![
            make_artifact("D-001", "DOCUMENTO", json!({"status": "BORRADOR"})),
        ];
        let rule = make_rule("RV-10");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
        let msg = result.message.unwrap();
        assert!(msg.contains("No se encontró"));
    }

    #[test]
    fn rv10_no_artifacts_of_type_returns_error() {
        let artifacts = vec![
            make_artifact("T-001", "TAREA", json!({"status": "DONE"})),
        ];
        let rule = make_rule("RV-10");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
    }

    #[test]
    fn rv10_missing_status_field_returns_error() {
        let artifacts = vec![
            make_artifact("D-001", "DOCUMENTO", json!({})),
        ];
        let rule = make_rule("RV-10");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
    }

    #[test]
    fn rv10_custom_artifact_type_and_status() {
        let artifacts = vec![
            make_artifact("R-001", "REPORTE", json!({"approval_state": "APPROVED"})),
        ];
        let rule = VerificationRule {
            id: "RV-10".to_string(),
            severity: "OBLIGATORIA".to_string(),
            params: json!({
                "artifact_type": "REPORTE",
                "status_field": "approval_state",
                "approved_states": ["APPROVED"]
            }),
        };

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Ok);
    }

    #[test]
    fn rv10_first_approved_found_returns_ok() {
        let artifacts = vec![
            make_artifact("D-001", "DOCUMENTO", json!({"status": "BORRADOR"})),
            make_artifact("D-002", "DOCUMENTO", json!({"status": "APROBADO"})),
            make_artifact("D-003", "DOCUMENTO", json!({"status": "VALIDADO"})),
        ];
        let rule = make_rule("RV-10");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Ok);
        let msg = result.message.unwrap();
        assert!(msg.contains("D-002") || msg.contains("D-003"));
    }
}
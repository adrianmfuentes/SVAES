use crate::models::{Artifact, RuleEvaluation, RuleStatus, VerificationRule};
use std::collections::HashSet;

/// RV-08: Compara dos conjuntos de identificadores: los declarados en un artefacto
/// maestro (mapeo) frente a los que realmente se han enviado en el payload.
///
/// # Parámetros
/// * `artifacts` - Slice de artefactos a verificar.
/// * `rule_config` - Configuración de la regla con parámetros:
///   - `master_artifact_id`: ID del artefacto maestro que contiene la lista de IDs declarados.
///   - `master_field`: Campo en metadata del maestro que contiene la lista de IDs (default: "planned_tasks").
///   - `target_type`: Tipo de artefactos a comparar con la lista del maestro (default: "TAREA").
///
/// # Lógica
/// 1. Busca el artefacto maestro por su ID.
/// 2. Extrae la lista de IDs declarados desde el campo especificado de su metadata.
/// 3. Recopila los IDs reales de los artefactos del tipo especificado.
/// 4. Compara ambos conjuntos y calcula la diferencia.
/// 5. Si hay IDs faltantes (en payload pero no declarados) o sobrantes (declarados pero no en payload), retorna Error.
/// 6. Si ambos conjuntos coinciden exactamente, retorna Ok.
///
/// # Retorno
/// `RuleEvaluation` con el estado correspondiente y lista de IDs faltantes/sobrantes.
pub fn evaluate(artifacts: &[Artifact], rule_config: &VerificationRule) -> RuleEvaluation {
    let master_id = match rule_config.params.get("master_artifact_id").and_then(|v| v.as_str()) {
        Some(id) => id,
        None => {
            return RuleEvaluation {
                rule_id: rule_config.id.clone(),
                status: RuleStatus::Error,
                message: Some("Parámetro 'master_artifact_id' no proporcionado".to_string()),
            };
        }
    };

    let master_field = rule_config.params
        .get("master_field")
        .and_then(|v| v.as_str())
        .unwrap_or("planned_tasks");

    let target_type = rule_config.params
        .get("target_type")
        .and_then(|v| v.as_str())
        .unwrap_or("TAREA");

    let master = match artifacts.iter().find(|a| a.id == master_id) {
        Some(a) => a,
        None => {
            return RuleEvaluation {
                rule_id: rule_config.id.clone(),
                status: RuleStatus::Error,
                message: Some(format!("Artefacto maestro '{}' no encontrado", master_id)),
            };
        }
    };

    let declared_ids: HashSet<&str> = match master.metadata.get(master_field) {
        Some(val) => {
            match val.as_array() {
                Some(arr) => arr.iter().filter_map(|v| v.as_str()).collect(),
                None => {
                    return RuleEvaluation {
                        rule_id: rule_config.id.clone(),
                        status: RuleStatus::Error,
                        message: Some(format!(
                            "Campo '{}' en maestro '{}' no es un array válido",
                            master_field, master_id
                        )),
                    };
                }
            }
        }
        None => {
            return RuleEvaluation {
                rule_id: rule_config.id.clone(),
                status: RuleStatus::Error,
                message: Some(format!(
                    "Campo '{}' no encontrado en artefacto maestro '{}'",
                    master_field, master_id
                )),
            };
        }
    };

    let actual_ids: HashSet<&str> = artifacts
        .iter()
        .filter(|a| a.artifact_type == target_type)
        .map(|a| a.id.as_str())
        .collect();

    let missing_in_payload: Vec<&str> = declared_ids
        .difference(&actual_ids)
        .copied()
        .collect();

    if missing_in_payload.is_empty() && declared_ids.len() == actual_ids.len() {
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
                "Discrepancia entre lista declarada y payload. IDs declarados en '{}' del maestro '{}' que no están en artefactos '{}': {:?}",
                master_field,
                master_id,
                target_type,
                missing_in_payload
            )),
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

    fn make_rule(id: &str, master_id: &str) -> VerificationRule {
        VerificationRule {
            id: id.to_string(),
            severity: "OBLIGATORIA".to_string(),
            params: json!({"master_artifact_id": master_id}),
        }
    }

    #[test]
    fn rv08_exact_match_returns_ok() {
        let artifacts = vec![
            make_artifact("PLAN-001", "PLAN", json!({"planned_tasks": ["T-001", "T-002"]})),
            make_artifact("T-001", "TAREA", json!({})),
            make_artifact("T-002", "TAREA", json!({})),
        ];
        let rule = make_rule("RV-08", "PLAN-001");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Ok);
        assert!(result.message.is_none());
    }

    #[test]
    fn rv08_missing_in_payload_returns_error() {
        let artifacts = vec![
            make_artifact("PLAN-001", "PLAN", json!({"planned_tasks": ["T-001", "T-002", "T-003"]})),
            make_artifact("T-001", "TAREA", json!({})),
            make_artifact("T-002", "TAREA", json!({})),
        ];
        let rule = make_rule("RV-08", "PLAN-001");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
        let msg = result.message.unwrap();
        assert!(msg.contains("T-003"));
    }

    #[test]
    fn rv08_master_not_found_returns_error() {
        let artifacts = vec![
            make_artifact("T-001", "TAREA", json!({})),
        ];
        let rule = make_rule("RV-08", "PLAN-999");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
        assert!(result.message.unwrap().contains("no encontrado"));
    }

    #[test]
    fn rv08_master_field_missing_returns_error() {
        let artifacts = vec![
            make_artifact("PLAN-001", "PLAN", json!({})),
            make_artifact("T-001", "TAREA", json!({})),
        ];
        let rule = make_rule("RV-08", "PLAN-001");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
        assert!(result.message.unwrap().contains("no encontrado"));
    }

    #[test]
    fn rv08_no_target_artifacts_returns_error() {
        let artifacts = vec![
            make_artifact("PLAN-001", "PLAN", json!({"planned_tasks": ["T-001"]})),
        ];
        let rule = make_rule("RV-08", "PLAN-001");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
    }

    #[test]
    fn rv08_custom_master_field_and_target_type() {
        let artifacts = vec![
            make_artifact("MAP-001", "MAPA", json!({"mapped_docs": ["D-001", "D-002"]})),
            make_artifact("D-001", "DOCUMENTO", json!({})),
            make_artifact("D-002", "DOCUMENTO", json!({})),
        ];
        let rule = VerificationRule {
            id: "RV-08".to_string(),
            severity: "OBLIGATORIA".to_string(),
            params: json!({
                "master_artifact_id": "MAP-001",
                "master_field": "mapped_docs",
                "target_type": "DOCUMENTO"
            }),
        };

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Ok);
    }
}
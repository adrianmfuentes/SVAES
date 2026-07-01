use serde_json::json;
use crate::models::{Artifact, RuleEvaluation, RuleStatus, VerificationRule};
use std::collections::HashSet;

/// RV-08: Compara dos conjuntos de identificadores: los declarados en un artefacto
/// maestro (mapeo) frente a los que realmente se han enviado en el payload.
///
/// # Parámetros
/// * `artifacts` - Slice de artefactos a verificar.
/// * `rule_config` - Configuración de la regla con parámetros:
///   - `master_artifact_id` (opcional): ID (UUID interno de SVAES) del artefacto
///     maestro que contiene la lista de IDs declarados. Permite fijar explícitamente
///     cuál de los artefactos de esta entrega actúa como "maestro". Si se omite,
///     el maestro se autodetecta (ver `master_type`) para que la regla funcione
///     sin configuración adicional en el perfil por defecto del sistema, ya que el
///     UUID interno cambia en cada entrega/organización y no puede fijarse a nivel
///     de perfil compartido.
///   - `master_type`: Tipo de artefacto que se autodetecta como maestro cuando no
///     se especifica `master_artifact_id` (default: "PLAN"). Debe existir
///     exactamente un artefacto de este tipo en la entrega; si no hay ninguno la
///     regla queda No evaluada, y si hay más de uno se requiere `master_artifact_id`
///     para desambiguar.
///   - `master_field`: Campo en metadata del maestro que contiene la lista de
///     IDs declarados (default: "planned_tasks"). Acepta un array JSON o una
///     cadena separada por comas (para campos de texto simples en el conector,
///     p. ej. un campo personalizado de ClickUp).
///   - `target_type`: Tipo de artefactos a comparar con la lista del maestro (default: "TAREA").
///
/// # Lógica
/// 1. Determina el artefacto maestro: por `master_artifact_id` si se indica, o
///    autodetectando el único artefacto de tipo `master_type` en la entrega.
/// 2. Extrae la lista de IDs declarados desde el campo especificado de su metadata.
/// 3. Recopila la **referencia externa** (`_svaes_external_ref`, la que el usuario
///    introdujo al importar el artefacto, p. ej. "SVAES-1") de los artefactos del
///    tipo especificado - nunca su UUID interno, que ninguna herramienta externa
///    puede conocer ni declarar.
/// 4. Compara ambos conjuntos y calcula la diferencia.
/// 5. Si hay IDs faltantes (en payload pero no declarados) o sobrantes (declarados pero no en payload), retorna Error.
/// 6. Si ambos conjuntos coinciden exactamente, retorna Ok.
///
/// # Retorno
/// `RuleEvaluation` con el estado correspondiente y lista de IDs faltantes/sobrantes.
pub fn evaluate(artifacts: &[Artifact], rule_config: &VerificationRule) -> RuleEvaluation {
    let master_type = rule_config.params
        .get("master_type")
        .and_then(|v| v.as_str())
        .unwrap_or("PLAN");

    let master = match rule_config.params.get("master_artifact_id").and_then(|v| v.as_str()) {
        Some(master_id) => match artifacts.iter().find(|a| a.id == master_id) {
            Some(a) => a,
            None => {
                return RuleEvaluation {
                    rule_id: rule_config.id.clone(),
                    status: RuleStatus::Error,
                    message: Some("rule_evidence.error.RV-08.master_not_found".to_string()),
                    message_params: Some(json!({
                        "master_id": master_id,
                    })),
                };
            }
        },
        None => {
            let candidates: Vec<&Artifact> = artifacts.iter().filter(|a| a.artifact_type == master_type).collect();
            match candidates.as_slice() {
                [] => {
                    return RuleEvaluation {
                        rule_id: rule_config.id.clone(),
                        status: RuleStatus::NoEvaluada,
                        message: Some("rule_evidence.no_evaluada.RV-08".to_string()),
                        message_params: Some(json!({
                            "master_type": master_type,
                        })),
                    };
                }
                [single] => *single,
                multiple => {
                    return RuleEvaluation {
                        rule_id: rule_config.id.clone(),
                        status: RuleStatus::Error,
                        message: Some("rule_evidence.error.RV-08.multiple_masters_found".to_string()),
                        message_params: Some(json!({
                            "master_type": master_type,
                            "count": multiple.len(),
                        })),
                    };
                }
            }
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

    let declared_ids: HashSet<&str> = match master.metadata.get(master_field) {
        Some(val) => {
            if let Some(arr) = val.as_array() {
                arr.iter().filter_map(|v| v.as_str()).collect()
            } else if let Some(s) = val.as_str() {
                // Plain text custom fields (e.g. a ClickUp text field with
                // "SVAES-1, SVAES-2") are a realistic way to declare this list
                // without needing a structured array type in the source tool.
                s.split(',').map(|part| part.trim()).filter(|part| !part.is_empty()).collect()
            } else {
                return RuleEvaluation {
                    rule_id: rule_config.id.clone(),
                    status: RuleStatus::Error,
                    message: Some("rule_evidence.error.RV-08.field_not_array".to_string()),
                    message_params: Some(json!({
                        "master_field": master_field,
                        "master_id": master.id.as_str(),
                    })),
                };
            }
        }
        None => {
            return RuleEvaluation {
                rule_id: rule_config.id.clone(),
                status: RuleStatus::Error,
                message: Some("rule_evidence.error.RV-08.field_not_found".to_string()),
                message_params: Some(json!({
                    "master_field": master_field,
                    "master_id": master.id.as_str(),
                })),
            };
        }
    };

    // Compare against each artifact's *external* reference (the one the user
    // typed when importing it, e.g. "SVAES-1") - not its internal SVAES UUID,
    // which no external tool can ever know or declare in a "planned tasks" field.
    let actual_ids: HashSet<&str> = artifacts
        .iter()
        .filter(|a| a.artifact_type == target_type)
        .filter_map(|a| a.metadata.get("_svaes_external_ref").and_then(|v| v.as_str()))
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
            message_params: None,
        }
    } else {
        RuleEvaluation {
            rule_id: rule_config.id.clone(),
            status: RuleStatus::Error,
            message: Some("rule_evidence.error.RV-08.discrepancy".to_string()),
            message_params: Some(json!({
                "master_field": master_field,
                "master_id": master.id.as_str(),
                "target_type": target_type,
                "missing_ids": format!("{:?}", missing_in_payload),
            })),
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

    /// A TAREA artifact as it actually arrives from the API: internal UUID
    /// (`id`) distinct from the external reference the user typed on import
    /// (e.g. "SVAES-1"), which is what a master artifact must declare.
    fn make_tarea(id: &str, external_ref: &str) -> Artifact {
        Artifact {
            id: id.to_string(),
            artifact_type: "TAREA".to_string(),
            metadata: json!({"_svaes_external_ref": external_ref}),
        }
    }

    fn make_rule(id: &str, master_id: &str) -> VerificationRule {
        VerificationRule {
            id: id.to_string(),
            severity: "OBLIGATORIA".to_string(),
            params: json!({"master_artifact_id": master_id}),
        }
    }

    /// TC-UNI-MOT-08: RV-08 caso base — coincidencia exacta entre lista declarada y payload.
    /// Each Choice: cubre el resultado OK para alineación de listas de planificación.
    #[test]
    fn tc_uni_mot_08_rv08_exact_match_returns_ok() {
        let artifacts = vec![
            make_artifact("uuid-plan", "PLAN", json!({"planned_tasks": ["SVAES-1", "SVAES-2"]})),
            make_tarea("uuid-t1", "SVAES-1"),
            make_tarea("uuid-t2", "SVAES-2"),
        ];
        let rule = make_rule("RV-08", "uuid-plan");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Ok);
        assert!(result.message.is_none());
    }

    #[test]
    fn comma_separated_text_field_is_accepted() {
        // A plain ClickUp text custom field (not a structured array type) with
        // "SVAES-1, SVAES-2" must work just as well as a JSON array.
        let artifacts = vec![
            make_artifact("uuid-plan", "PLAN", json!({"planned_tasks": "SVAES-1, SVAES-2"})),
            make_tarea("uuid-t1", "SVAES-1"),
            make_tarea("uuid-t2", "SVAES-2"),
        ];
        let rule = make_rule("RV-08", "uuid-plan");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Ok);
    }

    #[test]
    fn missing_master_artifact_id_param_returns_no_evaluada() {
        let rule = VerificationRule {
            id: "RV-08".to_string(),
            severity: "OBLIGATORIA".to_string(),
            params: serde_json::json!({}),
        };
        let result = evaluate(&[], &rule);
        assert_eq!(result.status, RuleStatus::NoEvaluada);
        let msg = result.message.unwrap();
        assert_eq!(msg, "rule_evidence.no_evaluada.RV-08");
    }

    #[test]
    fn master_artifact_not_found_returns_error() {
        let artifacts = vec![
            make_tarea("uuid-t1", "SVAES-1"),
        ];
        let rule = make_rule("RV-08", "PLAN-999");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
        let msg = result.message.unwrap();
        assert_eq!(msg, "rule_evidence.error.RV-08.master_not_found");
        let params = result.message_params.unwrap();
        assert!(params["master_id"].as_str().unwrap().contains("PLAN-999"));
    }

    #[test]
    fn declared_task_missing_from_payload_returns_error() {
        let artifacts = vec![
            make_artifact("uuid-plan", "PLAN", json!({"planned_tasks": ["SVAES-1", "SVAES-2", "SVAES-3"]})),
            make_tarea("uuid-t1", "SVAES-1"),
            make_tarea("uuid-t2", "SVAES-2"),
        ];
        let rule = make_rule("RV-08", "uuid-plan");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
        let msg = result.message.unwrap();
        assert_eq!(msg, "rule_evidence.error.RV-08.discrepancy");
        let params = result.message_params.unwrap();
        assert!(params["missing_ids"].as_str().unwrap().contains("SVAES-3"));
    }

    #[test]
    fn extra_task_not_declared_returns_error() {
        let artifacts = vec![
            make_artifact("uuid-plan", "PLAN", json!({"planned_tasks": ["SVAES-1"]})),
            make_tarea("uuid-t1", "SVAES-1"),
            make_tarea("uuid-t2", "SVAES-2"),
        ];
        let rule = make_rule("RV-08", "uuid-plan");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
    }

    fn make_rule_without_master_id(id: &str) -> VerificationRule {
        VerificationRule {
            id: id.to_string(),
            severity: "OBLIGATORIA".to_string(),
            params: json!({}),
        }
    }

    /// The system default profile ships RV-08 with no `master_artifact_id` (that
    /// UUID is release/org-specific and can't be fixed at the shared-profile
    /// level) - the rule must still pass by auto-detecting the single PLAN
    /// artifact as master, e.g. the ClickUp "Release x.y.z" item.
    #[test]
    fn auto_detects_single_plan_artifact_as_master_when_id_not_given() {
        let artifacts = vec![
            make_artifact("uuid-plan", "PLAN", json!({"planned_tasks": "SVAES-1,SVAES-2"})),
            make_tarea("uuid-t1", "SVAES-1"),
            make_tarea("uuid-t2", "SVAES-2"),
        ];
        let rule = make_rule_without_master_id("RV-08");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Ok);
    }

    #[test]
    fn no_plan_artifact_and_no_master_id_returns_no_evaluada_with_master_type() {
        let artifacts = vec![make_tarea("uuid-t1", "SVAES-1")];
        let rule = make_rule_without_master_id("RV-08");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::NoEvaluada);
        let params = result.message_params.unwrap();
        assert_eq!(params["master_type"].as_str().unwrap(), "PLAN");
    }

    #[test]
    fn multiple_plan_artifacts_without_master_id_returns_error() {
        let artifacts = vec![
            make_artifact("uuid-plan-1", "PLAN", json!({"planned_tasks": ["SVAES-1"]})),
            make_artifact("uuid-plan-2", "PLAN", json!({"planned_tasks": ["SVAES-1"]})),
            make_tarea("uuid-t1", "SVAES-1"),
        ];
        let rule = make_rule_without_master_id("RV-08");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
        let msg = result.message.unwrap();
        assert_eq!(msg, "rule_evidence.error.RV-08.multiple_masters_found");
        let params = result.message_params.unwrap();
        assert_eq!(params["count"].as_u64().unwrap(), 2);
    }
}
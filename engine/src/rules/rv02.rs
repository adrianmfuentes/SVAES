use crate::models::{Artifact, RuleEvaluation, RuleStatus, VerificationRule};

/// RV-02: Implementa una búsqueda cruzada para verificar trazabilidad.
///
/// # Parámetros
/// * `artifacts` - Slice de artefactos a verificar.
/// * `rule_config` - Configuración de la regla con parámetros opcionales:
///   - `source_type`: Tipo de artefacto fuente que contiene referencias (default: "CÓDIGO").
///   - `target_type`: Tipo de artefacto destino que debe existir (default: "TAREA").
///   - `reference_field`: Campo de metadata que contiene el ID referenciado (default: "task_id").
///
/// # Lógica
/// 1. Filtra artefactos por tipo fuente (default: "CÓDIGO").
/// 2. Por cada artefacto fuente, extrae el campo de referencia de su metadata.
/// 3. Busca si existe algún artefacto del tipo destino (default: "TAREA") con ese ID.
/// 4. Si no existe, retorna Error con los IDs huérfanos.
/// 5. Si todos existen, retorna Ok.
///
/// # Retorno
/// `RuleEvaluation` con el estado correspondiente y mensaje detallado si hay referencias faltantes.
pub fn evaluate(artifacts: &[Artifact], rule_config: &VerificationRule) -> RuleEvaluation {
    let source_type = rule_config.params
        .get("source_type")
        .and_then(|v| v.as_str())
        .unwrap_or("CÓDIGO");

    let target_type = rule_config.params
        .get("target_type")
        .and_then(|v| v.as_str())
        .unwrap_or("TAREA");

    let reference_field = rule_config.params
        .get("reference_field")
        .and_then(|v| v.as_str())
        .unwrap_or("task_id");

    let source_ids: std::collections::HashSet<&str> = artifacts
        .iter()
        .filter(|a| a.artifact_type == target_type)
        .map(|a| a.id.as_str())
        .collect();

    let mut missing_references: Vec<&str> = Vec::new();

    for artifact in artifacts.iter().filter(|a| a.artifact_type == source_type) {
        if let Some(reference) = artifact.metadata.get(reference_field) {
            if let Some(reference_str) = reference.as_str() {
                if !source_ids.contains(reference_str) {
                    missing_references.push(reference_str);
                }
            }
        }
    }

    if missing_references.is_empty() {
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
                "Referencias huérfanas detectadas: '{}'. Los siguientes IDs referenciados en artefactos '{}' no existen como '{}': {:?}",
                missing_references.len(),
                source_type,
                target_type,
                missing_references
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

    fn make_rule(id: &str) -> VerificationRule {
        VerificationRule {
            id: id.to_string(),
            severity: "OBLIGATORIA".to_string(),
            params: json!({}),
        }
    }

    /// TC-UNI-MOT-02: RV-02 caso base — todas las referencias existen.
    /// Each Choice: cubre el resultado OK para trazabilidad entre artefactos.
    #[test]
    fn tc_uni_mot_02_rv02_all_references_exist_returns_ok() {
        let artifacts = vec![
            make_artifact("T-001", "TAREA", json!({})),
            make_artifact("T-002", "TAREA", json!({})),
            make_artifact("C-001", "CÓDIGO", json!({"task_id": "T-001"})),
            make_artifact("C-002", "CÓDIGO", json!({"task_id": "T-002"})),
        ];
        let rule = make_rule("RV-02");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Ok);
        assert!(result.message.is_none());
    }

    /// TC-UNI-MOT-12: RV-02 — referencia huérfana produce ERROR.
    /// Each Choice: cubre el resultado ERROR para el catálogo de trazabilidad.
    #[test]
    fn tc_uni_mot_12_rv02_orphan_reference_returns_error() {
        let artifacts = vec![
            make_artifact("T-001", "TAREA", json!({})),
            make_artifact("C-001", "CÓDIGO", json!({"task_id": "T-001"})),
            make_artifact("C-002", "CÓDIGO", json!({"task_id": "T-999"})),
        ];
        let rule = make_rule("RV-02");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
        let msg = result.message.unwrap();
        assert!(msg.contains("T-999"));
    }
}
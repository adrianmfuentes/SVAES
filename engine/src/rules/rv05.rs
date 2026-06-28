use crate::models::{Artifact, RuleEvaluation, RuleStatus, VerificationRule};

/// RV-05: Verifica que existan artefactos de tipo "DOCUMENTO" y que tengan
/// un flag de accesibilidad en true dentro de su metadata.
///
/// # Parámetros
/// * `artifacts` - Slice de artefactos a verificar.
/// * `rule_config` - Configuración de la regla con parámetros:
///   - `artifact_type`: Tipo de artefacto a verificar (default: "DOCUMENTO").
///   - `accessible_field`: Nombre del campo boolean en metadata (default: "accessible").
///
/// # Lógica
/// 1. Filtra artefactos por tipo (default: "DOCUMENTO").
/// 2. Verifica que al menos uno exista.
/// 3. Por cada documento, comprueba que el campo `accessible` exista y sea `true`.
/// 4. Si no hay documentos o alguno no es accesible, retorna Error.
///
/// # Retorno
/// `RuleEvaluation` con el estado correspondiente y IDs de documentos inaccesibles.
pub fn evaluate(artifacts: &[Artifact], rule_config: &VerificationRule) -> RuleEvaluation {
    let artifact_type = rule_config.params
        .get("artifact_type")
        .and_then(|v| v.as_str())
        .unwrap_or("DOCUMENTO");

    let accessible_field = rule_config.params
        .get("accessible_field")
        .and_then(|v| v.as_str())
        .unwrap_or("accessible");

    let documents: Vec<&Artifact> = artifacts
        .iter()
        .filter(|a| a.artifact_type == artifact_type)
        .collect();

    if documents.is_empty() {
        return RuleEvaluation {
            rule_id: rule_config.id.clone(),
            status: RuleStatus::Error,
            message: Some(format!(
                "No se encontraron artefactos de tipo '{}'",
                artifact_type
            )),
        };
    }

    let inaccessible_docs: Vec<&str> = documents
        .iter()
        .filter(|doc| {
            match doc.metadata.get(accessible_field) {
                Some(val) => val.as_bool() != Some(true),
                None => true,
            }
        })
        .map(|doc| doc.id.as_str())
        .collect();

    if inaccessible_docs.is_empty() {
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
                "Documentos inaccesibles (flag '{}' no es true): {:?}",
                accessible_field,
                inaccessible_docs
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

    /// TC-UNI-MOT-05: RV-05 caso base — todos los documentos accesibles.
    /// Each Choice: cubre el resultado OK para disponibilidad de documentos.
    #[test]
    fn tc_uni_mot_05_rv05_all_accessible_returns_ok() {
        let artifacts = vec![
            make_artifact("D-001", "DOCUMENTO", json!({"accessible": true})),
            make_artifact("D-002", "DOCUMENTO", json!({"accessible": true})),
        ];
        let rule = make_rule("RV-05");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Ok);
        assert!(result.message.is_none());
    }

    #[test]
    fn no_documents_returns_error() {
        let artifacts = vec![make_artifact("T-001", "TAREA", json!({"accessible": true}))];
        let rule = make_rule("RV-05");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
        let msg = result.message.unwrap();
        assert!(msg.contains("DOCUMENTO"));
    }

    #[test]
    fn inaccessible_document_returns_error() {
        let artifacts = vec![
            make_artifact("D-001", "DOCUMENTO", json!({"accessible": true})),
            make_artifact("D-002", "DOCUMENTO", json!({"accessible": false})),
        ];
        let rule = make_rule("RV-05");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
        let msg = result.message.unwrap();
        assert!(msg.contains("D-002"));
    }

    #[test]
    fn document_missing_accessible_field_returns_error() {
        let artifacts = vec![make_artifact("D-001", "DOCUMENTO", json!({}))];
        let rule = make_rule("RV-05");

        let result = evaluate(&artifacts, &rule);

        assert_eq!(result.status, RuleStatus::Error);
    }
}